import os
import sys
import json
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

from database import get_connection, init_db, log_audit
from auth import authenticate_admin, get_admin_by_token, invalidate_token, hash_password
from payments import (
    calculate_plan_total,
    create_razorpay_order,
    complete_online_payment,
    record_cash_payment,
    calculate_membership_dates
)

PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")

class GymAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _send_error(self, status_code: int, message: str):
        self._send_json(status_code, {"error": message})

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _get_auth_admin(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:].strip()
        return get_admin_by_token(token)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Static routing rewrites
        if path == "/" or path == "":
            self.path = "/index.html"
            return super().do_GET()
        elif path == "/admin":
            self.path = "/admin.html"
            return super().do_GET()

        # Check if API route
        if not path.startswith("/api/"):
            return super().do_GET()

        try:
            self._handle_api_get(path, query)
        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")

    def _handle_api_get(self, path: str, query: dict):
        conn = get_connection()

        # 1. Plans (Public)
        if path == "/api/plans":
            plans = conn.execute("SELECT * FROM plans WHERE is_active = 1 ORDER BY duration_months ASC, base_price ASC").fetchall()
            result = []
            for p in plans:
                row = dict(p)
                try:
                    row["features"] = json.loads(row["features"])
                except Exception:
                    row["features"] = []
                result.append(row)
            conn.close()
            return self._send_json(200, {"plans": result})

        # 2. Equipment (Public)
        elif path == "/api/equipment":
            category = query.get("category", [None])[0]
            if category and category != "All":
                items = conn.execute(
                    "SELECT * FROM equipment WHERE is_active = 1 AND category = ? ORDER BY id ASC",
                    (category,)
                ).fetchall()
            else:
                items = conn.execute("SELECT * FROM equipment WHERE is_active = 1 ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json(200, {"equipment": [dict(i) for i in items]})

        # 3. Trainers (Public)
        elif path == "/api/trainers":
            trainers = conn.execute("SELECT * FROM trainers WHERE is_active = 1 ORDER BY id ASC").fetchall()
            conn.close()
            return self._send_json(200, {"trainers": [dict(t) for t in trainers]})

        # 4. Nutrition Resources (Public)
        elif path == "/api/nutrition":
            resources = conn.execute("SELECT * FROM nutrition_resources WHERE is_active = 1 ORDER BY id ASC").fetchall()
            result = []
            for r in resources:
                row = dict(r)
                try:
                    row["key_points"] = json.loads(row["key_points"])
                except Exception:
                    row["key_points"] = []
                result.append(row)
            conn.close()
            return self._send_json(200, {"nutrition": result})

        # 5. Admin Me (Protected)
        elif path == "/api/admin/me":
            admin = self._get_auth_admin()
            conn.close()
            if not admin:
                return self._send_error(401, "Unauthorized or session expired")
            return self._send_json(200, {"admin": admin})

        # 6. Admin Overview Stats (Protected)
        elif path == "/api/admin/stats":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")

            total_revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_status IN ('Verified', 'Cash Received')").fetchone()[0]
            online_revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_method = 'Razorpay' AND payment_status = 'Verified'").fetchone()[0]
            cash_revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_method = 'Cash' AND payment_status = 'Cash Received'").fetchone()[0]

            active_members = conn.execute("SELECT COUNT(*) FROM members WHERE status = 'Active'").fetchone()[0]
            awaiting_payment = conn.execute("SELECT COUNT(*) FROM members WHERE status = 'Awaiting payment'").fetchone()[0]
            total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]

            new_enquiries = conn.execute("SELECT COUNT(*) FROM enquiries WHERE status = 'New'").fetchone()[0]
            total_enquiries = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]

            # Expiring soon (within next 7 days)
            expiring_soon = conn.execute("""
                SELECT COUNT(*) FROM members
                WHERE status = 'Active'
                AND membership_end BETWEEN date('now') AND date('now', '+7 days')
            """).fetchone()[0]

            recent_payments = conn.execute("""
                SELECT p.*, m.name as member_name
                FROM payments p
                JOIN members m ON p.member_id = m.id
                ORDER BY p.id DESC LIMIT 5
            """).fetchall()

            conn.close()
            return self._send_json(200, {
                "stats": {
                    "total_revenue": total_revenue,
                    "online_revenue": online_revenue,
                    "cash_revenue": cash_revenue,
                    "active_members": active_members,
                    "awaiting_payment": awaiting_payment,
                    "total_members": total_members,
                    "new_enquiries": new_enquiries,
                    "total_enquiries": total_enquiries,
                    "expiring_soon": expiring_soon
                },
                "recent_payments": [dict(rp) for rp in recent_payments]
            })

        # 7. Admin Enquiries (Protected)
        elif path == "/api/enquiries":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")
            enquiries = conn.execute("SELECT * FROM enquiries ORDER BY id DESC").fetchall()
            conn.close()
            return self._send_json(200, {"enquiries": [dict(e) for e in enquiries]})

        # 8. Admin Members List (Protected)
        elif path == "/api/members":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")
            members = conn.execute("""
                SELECT m.*, p.name as plan_name, p.duration_months, p.base_price, p.includes_cardio
                FROM members m
                LEFT JOIN plans p ON m.plan_id = p.id
                ORDER BY m.id DESC
            """).fetchall()
            conn.close()
            return self._send_json(200, {"members": [dict(m) for m in members]})

        # 9. Admin Payments History (Protected)
        elif path == "/api/payments":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")
            payments = conn.execute("""
                SELECT p.*, m.name as member_name, m.phone as member_phone, pl.name as plan_name
                FROM payments p
                JOIN members m ON p.member_id = m.id
                LEFT JOIN plans pl ON m.plan_id = pl.id
                ORDER BY p.id DESC
            """).fetchall()
            conn.close()
            return self._send_json(200, {"payments": [dict(p) for p in payments]})

        # 10. Admin Diet Requests (Protected)
        elif path == "/api/diet-requests":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")
            requests = conn.execute("SELECT * FROM diet_requests ORDER BY id DESC").fetchall()
            conn.close()
            return self._send_json(200, {"diet_requests": [dict(d) for d in requests]})

        # 11. Admin Audit Logs (Protected)
        elif path == "/api/admin/audit-logs":
            admin = self._get_auth_admin()
            if not admin:
                conn.close()
                return self._send_error(401, "Unauthorized")
            logs = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50").fetchall()
            conn.close()
            return self._send_json(200, {"audit_logs": [dict(l) for l in logs]})

        else:
            conn.close()
            return self._send_error(404, f"API route not found: {path}")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        try:
            self._handle_api_post(path, body)
        except Exception as e:
            self._send_error(500, f"Error processing request: {str(e)}")

    def _handle_api_post(self, path: str, body: dict):
        # 1. Admin Login
        if path == "/api/admin/login":
            email = body.get("email", "")
            password = body.get("password", "")
            if not email or not password:
                return self._send_error(400, "Email and password are required")
            auth_res = authenticate_admin(email, password)
            if not auth_res:
                return self._send_error(401, "Invalid email or password")
            return self._send_json(200, auth_res)

        # 2. Admin Logout
        elif path == "/api/admin/logout":
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                invalidate_token(token)
            return self._send_json(200, {"message": "Logged out successfully"})

        # 3. Public Enquiry Submission
        elif path == "/api/enquiries":
            name = body.get("name", "").strip()
            phone = body.get("phone", "").strip()
            email = body.get("email", "").strip()
            interested_plan = body.get("interested_plan", "")
            message = body.get("message", "").strip()
            preferred_time = body.get("preferred_time", "Anytime")

            if not name or not phone:
                return self._send_error(400, "Full Name and Phone Number are required")

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO enquiries (name, phone, email, interested_plan, message, preferred_time, status)
                VALUES (?, ?, ?, ?, ?, ?, 'New')
            """, (name, phone, email, interested_plan, message, preferred_time))
            enquiry_id = cursor.lastrowid
            conn.commit()
            conn.close()

            log_audit("NEW_ENQUIRY", f"Enquiry #{enquiry_id} received from {name} ({phone}) for {interested_plan}")

            return self._send_json(201, {
                "message": "Enquiry received! Our trainers or desk team will reach out shortly.",
                "enquiry_id": enquiry_id
            })

        # 4. Public Member Registration / Join Checkout Initiation
        elif path == "/api/members/register":
            name = body.get("name", "").strip()
            phone = body.get("phone", "").strip()
            email = body.get("email", "").strip()
            plan_id = body.get("plan_id")
            cardio_addon = bool(body.get("cardio_addon", False))
            payment_choice = body.get("payment_choice", "razorpay") # 'razorpay' or 'cash'

            if not name or not phone or not plan_id:
                return self._send_error(400, "Name, phone, and plan selection are required")

            conn = get_connection()
            plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if not plan:
                conn.close()
                return self._send_error(404, "Selected plan not found")

            # Check if member with this phone already exists
            existing = conn.execute("SELECT id, status FROM members WHERE phone = ?", (phone,)).fetchone()
            cursor = conn.cursor()

            initial_status = "Awaiting payment"
            if existing:
                member_id = existing["id"]
                cursor.execute("""
                    UPDATE members
                    SET name = ?, email = ?, plan_id = ?, cardio_addon = ?, status = ?
                    WHERE id = ?
                """, (name, email, plan_id, 1 if cardio_addon else 0, initial_status, member_id))
            else:
                cursor.execute("""
                    INSERT INTO members (name, phone, email, plan_id, cardio_addon, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, phone, email, plan_id, 1 if cardio_addon else 0, initial_status))
                member_id = cursor.lastrowid

            conn.commit()
            conn.close()

            pricing = calculate_plan_total(plan, cardio_addon)

            if payment_choice == "razorpay":
                order_data = create_razorpay_order(member_id, plan_id, cardio_addon)
                return self._send_json(200, {
                    "member_id": member_id,
                    "payment_type": "online",
                    "order": order_data
                })
            else:
                # Cash registration intent
                log_audit("CASH_INTENT_SUBMITTED", f"Member {name} (#{member_id}) registered with Cash at Gym choice for {plan['name']}")
                return self._send_json(200, {
                    "member_id": member_id,
                    "payment_type": "cash",
                    "pricing": pricing,
                    "message": "Registration received! Please visit the gym front desk to pay cash and activate your access card."
                })

        # 5. Razorpay Online Payment Verification
        elif path == "/api/payments/verify":
            order_id = body.get("order_id")
            payment_id = body.get("payment_id")
            signature = body.get("signature")

            if not order_id or not payment_id or not signature:
                return self._send_error(400, "order_id, payment_id, and signature are required for server verification")

            try:
                res = complete_online_payment(order_id, payment_id, signature)
                return self._send_json(200, res)
            except Exception as e:
                return self._send_error(400, str(e))

        # 6. Admin Cash Payment Recording (Protected)
        elif path == "/api/payments/cash":
            admin = self._get_auth_admin()
            if not admin:
                return self._send_error(401, "Unauthorized. Only logged-in staff can record cash payments.")

            member_id = body.get("member_id")
            amount = body.get("amount")
            start_date = body.get("start_date")
            notes = body.get("notes", "")

            if not member_id or not amount:
                return self._send_error(400, "member_id and cash amount are required")

            try:
                res = record_cash_payment(
                    member_id=int(member_id),
                    amount=int(amount),
                    staff_name=admin["name"],
                    notes=notes,
                    start_date=start_date
                )
                return self._send_json(200, res)
            except Exception as e:
                return self._send_error(400, str(e))

        # 7. Member Diet Preference / Nutrition Request (Public)
        elif path == "/api/diet-requests":
            name = body.get("name", "").strip()
            phone = body.get("phone", "").strip()
            email = body.get("email", "").strip()
            dietary_preference = body.get("dietary_preference", "Vegetarian")
            allergies = body.get("allergies", "").strip()
            primary_goal = body.get("primary_goal", "General Health")
            budget_range = body.get("budget_range", "")
            notes = body.get("notes", "")

            if not name or not phone:
                return self._send_error(400, "Name and Phone number are required")

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO diet_requests (
                    name, phone, email, dietary_preference, allergies,
                    primary_goal, budget_range, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending Review')
            """, (name, phone, email, dietary_preference, allergies, primary_goal, budget_range, notes))
            request_id = cursor.lastrowid
            conn.commit()
            conn.close()

            log_audit("DIET_REQUEST_SUBMITTED", f"Diet consultation requested by {name} ({primary_goal})")

            return self._send_json(201, {
                "message": "Diet consultation request submitted! A certified coach will review it with you.",
                "request_id": request_id
            })

        # 8. Admin Add Equipment (Protected)
        elif path == "/api/equipment":
            admin = self._get_auth_admin()
            if not admin:
                return self._send_error(401, "Unauthorized")

            name = body.get("name")
            category = body.get("category", "Strength Machines")
            description = body.get("description", "")
            beginner_notes = body.get("beginner_notes", "")
            setup_steps = body.get("setup_steps", "")
            common_mistakes = body.get("common_mistakes", "")
            image_url = body.get("image_url", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80")
            tutorial_url = body.get("tutorial_url", "")

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO equipment (
                    name, category, description, beginner_notes,
                    setup_steps, common_mistakes, image_url, tutorial_url, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (name, category, description, beginner_notes, setup_steps, common_mistakes, image_url, tutorial_url))
            eq_id = cursor.lastrowid
            conn.commit()
            conn.close()

            log_audit("EQUIPMENT_ADDED", f"Staff {admin['name']} added equipment: {name}", admin["name"])
            return self._send_json(201, {"message": "Equipment created", "equipment_id": eq_id})

        # 9. Admin Add Plan (Protected)
        elif path == "/api/plans":
            admin = self._get_auth_admin()
            if not admin:
                return self._send_error(401, "Unauthorized")

            name = body.get("name")
            duration_months = int(body.get("duration_months", 1))
            base_price = int(body.get("base_price", 1000))
            cardio_price = int(body.get("cardio_price", 300))
            includes_cardio = 1 if body.get("includes_cardio") else 0
            features = body.get("features", [])
            savings_text = body.get("savings_text", "")

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO plans (name, duration_months, base_price, cardio_price, includes_cardio, features, savings_text, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (name, duration_months, base_price, cardio_price, includes_cardio, json.dumps(features), savings_text))
            plan_id = cursor.lastrowid
            conn.commit()
            conn.close()

            log_audit("PLAN_CREATED", f"Plan {name} (₹{base_price}) created by {admin['name']}", admin["name"])
            return self._send_json(201, {"message": "Plan created successfully", "plan_id": plan_id})

        else:
            return self._send_error(404, f"POST route not found: {path}")

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        try:
            self._handle_api_put(path, body)
        except Exception as e:
            self._send_error(500, f"Error processing update: {str(e)}")

    def _handle_api_put(self, path: str, body: dict):
        admin = self._get_auth_admin()
        if not admin:
            return self._send_error(401, "Unauthorized")

        conn = get_connection()
        cursor = conn.cursor()

        # Update Enquiry Status: /api/enquiries/<id>/status
        if path.startswith("/api/enquiries/") and path.endswith("/status"):
            parts = path.split("/")
            enquiry_id = int(parts[3])
            status = body.get("status", "Contacted")
            cursor.execute("UPDATE enquiries SET status = ? WHERE id = ?", (status, enquiry_id))
            conn.commit()
            conn.close()
            log_audit("ENQUIRY_STATUS_UPDATED", f"Enquiry #{enquiry_id} marked as {status} by {admin['name']}", admin["name"])
            return self._send_json(200, {"message": "Enquiry status updated"})

        # Update Member Details / Dates: /api/members/<id>
        elif path.startswith("/api/members/") and not path.endswith("/renew"):
            parts = path.split("/")
            member_id = int(parts[3])
            status = body.get("status")
            start_date = body.get("membership_start")
            end_date = body.get("membership_end")
            notes = body.get("notes")

            cursor.execute("""
                UPDATE members
                SET status = COALESCE(?, status),
                    membership_start = COALESCE(?, membership_start),
                    membership_end = COALESCE(?, membership_end),
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (status, start_date, end_date, notes, member_id))
            conn.commit()
            conn.close()

            log_audit("MEMBER_UPDATED", f"Member #{member_id} updated by {admin['name']}", admin["name"])
            return self._send_json(200, {"message": "Member updated successfully"})

        # Renew Membership: /api/members/<id>/renew
        elif path.startswith("/api/members/") and path.endswith("/renew"):
            parts = path.split("/")
            member_id = int(parts[3])
            member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
            if not member:
                conn.close()
                return self._send_error(404, "Member not found")

            plan = conn.execute("SELECT * FROM plans WHERE id = ?", (member["plan_id"],)).fetchone()
            conn.close()

            start_d, end_d = calculate_membership_dates(plan["duration_months"] if plan else 1)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE members
                SET status = 'Active', membership_start = ?, membership_end = ?
                WHERE id = ?
            """, (start_d, end_d, member_id))
            conn.commit()
            conn.close()

            log_audit("MEMBER_RENEWED", f"Member #{member_id} renewed by {admin['name']} until {end_d}", admin["name"])
            return self._send_json(200, {
                "message": "Membership renewed successfully",
                "membership_start": start_d,
                "membership_end": end_d
            })

        # Update Diet Request Status: /api/diet-requests/<id>/status
        elif path.startswith("/api/diet-requests/") and path.endswith("/status"):
            parts = path.split("/")
            req_id = int(parts[3])
            status = body.get("status", "Reviewed")
            cursor.execute("""
                UPDATE diet_requests
                SET status = ?, reviewed_by = ?
                WHERE id = ?
            """, (status, admin["name"], req_id))
            conn.commit()
            conn.close()
            log_audit("DIET_REQUEST_UPDATED", f"Diet request #{req_id} marked as {status} by {admin['name']}", admin["name"])
            return self._send_json(200, {"message": "Diet request status updated"})

        # Update Equipment: /api/equipment/<id>
        elif path.startswith("/api/equipment/"):
            parts = path.split("/")
            eq_id = int(parts[3])
            name = body.get("name")
            category = body.get("category")
            description = body.get("description")
            beginner_notes = body.get("beginner_notes")
            setup_steps = body.get("setup_steps")
            common_mistakes = body.get("common_mistakes")
            image_url = body.get("image_url")
            tutorial_url = body.get("tutorial_url")

            cursor.execute("""
                UPDATE equipment
                SET name = COALESCE(?, name),
                    category = COALESCE(?, category),
                    description = COALESCE(?, description),
                    beginner_notes = COALESCE(?, beginner_notes),
                    setup_steps = COALESCE(?, setup_steps),
                    common_mistakes = COALESCE(?, common_mistakes),
                    image_url = COALESCE(?, image_url),
                    tutorial_url = COALESCE(?, tutorial_url)
                WHERE id = ?
            """, (name, category, description, beginner_notes, setup_steps, common_mistakes, image_url, tutorial_url, eq_id))
            conn.commit()
            conn.close()

            log_audit("EQUIPMENT_UPDATED", f"Equipment #{eq_id} updated by {admin['name']}", admin["name"])
            return self._send_json(200, {"message": "Equipment updated"})

        else:
            conn.close()
            return self._send_error(404, f"PUT route not found: {path}")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        admin = self._get_auth_admin()
        if not admin:
            return self._send_error(401, "Unauthorized")

        if path.startswith("/api/equipment/"):
            parts = path.split("/")
            eq_id = int(parts[3])
            conn = get_connection()
            conn.execute("UPDATE equipment SET is_active = 0 WHERE id = ?", (eq_id,))
            conn.commit()
            conn.close()
            log_audit("EQUIPMENT_DELETED", f"Equipment #{eq_id} set inactive by {admin['name']}", admin["name"])
            return self._send_json(200, {"message": "Equipment deleted/deactivated"})
        else:
            return self._send_error(404, "DELETE route not found")

def run(server_class=ThreadingHTTPServer, handler_class=GymAPIHandler, port=PORT):
    server_address = ("0.0.0.0", port)
    httpd = server_class(server_address, handler_class)
    print(f"Gym Website & Platform running at: http://localhost:{port}/")
    print(f"Admin Dashboard available at: http://localhost:{port}/admin")
    httpd.serve_forever()

if __name__ == "__main__":
    init_db()
    run()
