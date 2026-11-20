import os
import sys
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_connection
from seed_data import seed_all
from auth import authenticate_admin
from app import GymAPIHandler

class MockHandler:
    def __init__(self, auth_token=None):
        self.auth_token = auth_token
        self.status_code = None
        self.response_data = None
        self.headers = {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def _send_json(self, status_code: int, data: dict):
        self.status_code = status_code
        self.response_data = data
        return data

    def _send_error(self, status_code: int, message: str):
        self.status_code = status_code
        self.response_data = {"error": message}
        return self.response_data

    def _get_auth_admin(self):
        return GymAPIHandler._get_auth_admin(self)

    def handle_get(self, path, query=None):
        query = query or {}
        GymAPIHandler._handle_api_get(self, path, query)
        return self.status_code, self.response_data

    def handle_post(self, path, body):
        GymAPIHandler._handle_api_post(self, path, body)
        return self.status_code, self.response_data

    def handle_put(self, path, body):
        GymAPIHandler._handle_api_put(self, path, body)
        return self.status_code, self.response_data

class TestAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_all()

    def test_01_public_get_apis(self):
        handler = MockHandler()

        # 1. Plans
        status, data = handler.handle_get("/api/plans")
        self.assertEqual(status, 200)
        self.assertTrue(len(data["plans"]) >= 6)
        # Check basic vs cardio plan structure
        basic = next(p for p in data["plans"] if p["name"] == "Basic Monthly")
        self.assertEqual(basic["base_price"], 1000)
        self.assertEqual(basic["includes_cardio"], 0)

        # 2. Equipment
        status, data = handler.handle_get("/api/equipment")
        self.assertEqual(status, 200)
        self.assertTrue(len(data["equipment"]) >= 5)

        # Filter category
        status, data_cardio = handler.handle_get("/api/equipment", {"category": ["Cardio"]})
        self.assertEqual(status, 200)
        for eq in data_cardio["equipment"]:
            self.assertEqual(eq["category"], "Cardio")

        # 3. Trainers
        status, data = handler.handle_get("/api/trainers")
        self.assertEqual(status, 200)
        self.assertTrue(len(data["trainers"]) >= 3)

        # 4. Nutrition
        status, data = handler.handle_get("/api/nutrition")
        self.assertEqual(status, 200)
        self.assertTrue(len(data["nutrition"]) >= 3)

    def test_02_enquiries_post_and_admin_workflow(self):
        # Public visitor submits enquiry
        pub_handler = MockHandler()
        status, data = pub_handler.handle_post("/api/enquiries", {
            "name": "Harsh Vardhan",
            "phone": "9811223344",
            "email": "harsh@example.com",
            "interested_plan": "Basic Monthly",
            "message": "Do you offer locker facilities?",
            "preferred_time": "Morning"
        })
        self.assertEqual(status, 201)
        enquiry_id = data["enquiry_id"]

        # Admin logs in
        login_res = authenticate_admin("admin@gym.com", "admin123")
        admin_handler = MockHandler(auth_token=login_res["token"])

        # Admin retrieves enquiries
        status, enq_list = admin_handler.handle_get("/api/enquiries")
        self.assertEqual(status, 200)
        found = any(e["id"] == enquiry_id for e in enq_list["enquiries"])
        self.assertTrue(found)

        # Admin updates enquiry status
        status, upd = admin_handler.handle_put(f"/api/enquiries/{enquiry_id}/status", {"status": "Contacted"})
        self.assertEqual(status, 200)

        # Verify updated status
        conn = get_connection()
        enq = conn.execute("SELECT status FROM enquiries WHERE id = ?", (enquiry_id,)).fetchone()
        conn.close()
        self.assertEqual(enq["status"], "Contacted")

    def test_03_diet_requests_post_and_review(self):
        pub_handler = MockHandler()
        status, data = pub_handler.handle_post("/api/diet-requests", {
            "name": "Simran Kaur",
            "phone": "9877665544",
            "dietary_preference": "Vegetarian",
            "allergies": "Gluten sensitivity",
            "primary_goal": "Fat Loss",
            "budget_range": "₹3,000/mo",
            "notes": "Looking for meal plan without wheat"
        })
        self.assertEqual(status, 201)
        req_id = data["request_id"]

        # Admin views diet requests
        login_res = authenticate_admin("admin@gym.com", "admin123")
        admin_handler = MockHandler(auth_token=login_res["token"])

        status, d_list = admin_handler.handle_get("/api/diet-requests")
        self.assertEqual(status, 200)
        self.assertTrue(any(d["id"] == req_id for d in d_list["diet_requests"]))

        # Admin updates diet request status
        status, upd = admin_handler.handle_put(f"/api/diet-requests/{req_id}/status", {"status": "Reviewed"})
        self.assertEqual(status, 200)

    def test_04_member_registration_and_razorpay_flow(self):
        pub_handler = MockHandler()
        # Fetch actual plan ID
        status, plans_data = pub_handler.handle_get("/api/plans")
        basic_plan = next(p for p in plans_data["plans"] if p["name"] == "Basic Monthly")

        # Register for Basic Monthly with Cardio Add-on
        status, data = pub_handler.handle_post("/api/members/register", {
            "name": "Gaurav Malhotra",
            "phone": "9812349900",
            "email": "gaurav@example.com",
            "plan_id": basic_plan["id"],
            "cardio_addon": True,
            "payment_choice": "razorpay"
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["payment_type"], "online")
        order = data["order"]
        # Basic 1000 + Cardio 300 = 1300
        self.assertEqual(order["amount_inr"], 1300)

        # Verify payment signature
        status, ver = pub_handler.handle_post("/api/payments/verify", {
            "order_id": order["order_id"],
            "payment_id": "pay_test_online_verified",
            "signature": "demo_verified_signature"
        })
        self.assertEqual(status, 200)
        self.assertEqual(ver["status"], "success")

        # Verify member is now active in database
        conn = get_connection()
        mem = conn.execute("SELECT status, membership_start, membership_end FROM members WHERE id = ?", (data["member_id"],)).fetchone()
        conn.close()
        self.assertEqual(mem["status"], "Active")
        self.assertIsNotNone(mem["membership_start"])

    def test_05_cash_desk_workflow(self):
        # 1. Member chooses Pay Cash at Gym
        pub_handler = MockHandler()
        status, plans_data = pub_handler.handle_get("/api/plans")
        basic_plan = next(p for p in plans_data["plans"] if p["name"] == "Basic Monthly")

        status, data = pub_handler.handle_post("/api/members/register", {
            "name": "Manish Tyagi",
            "phone": "9812349911",
            "email": "manish@example.com",
            "plan_id": basic_plan["id"],
            "cardio_addon": False,
            "payment_choice": "cash"
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["payment_type"], "cash")
        member_id = data["member_id"]

        # Check initial status is 'Awaiting payment'
        conn = get_connection()
        mem = conn.execute("SELECT status FROM members WHERE id = ?", (member_id,)).fetchone()
        conn.close()
        self.assertEqual(mem["status"], "Awaiting payment")

        # 2. Staff records physical cash at front desk
        login_res = authenticate_admin("staff@gym.com", "staff123")
        staff_handler = MockHandler(auth_token=login_res["token"])

        status, cash_res = staff_handler.handle_post("/api/payments/cash", {
            "member_id": member_id,
            "amount": 1000,
            "notes": "Cash collected at desk"
        })
        self.assertEqual(status, 200)
        self.assertEqual(cash_res["status"], "success")
        self.assertTrue(cash_res["receipt_no"].startswith("CASH-"))

        # Verify member is now Active
        conn = get_connection()
        updated_mem = conn.execute("SELECT status, membership_start, membership_end FROM members WHERE id = ?", (member_id,)).fetchone()
        conn.close()
        self.assertEqual(updated_mem["status"], "Active")

    def test_06_admin_stats_and_audit(self):
        login_res = authenticate_admin("admin@gym.com", "admin123")
        admin_handler = MockHandler(auth_token=login_res["token"])

        status, stats = admin_handler.handle_get("/api/admin/stats")
        self.assertEqual(status, 200)
        self.assertGreater(stats["stats"]["total_revenue"], 0)
        self.assertGreater(stats["stats"]["active_members"], 0)

        # Audit logs
        status, audit = admin_handler.handle_get("/api/admin/audit-logs")
        self.assertEqual(status, 200)
        self.assertTrue(len(audit["audit_logs"]) >= 5)

if __name__ == "__main__":
    unittest.main()
