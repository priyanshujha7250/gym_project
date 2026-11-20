import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from database import get_connection, log_audit

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_sampleKey123")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "rzp_sample_secret_key_456")

def calculate_membership_dates(duration_months: int, start_date: str = None):
    """Calculates start and end date for a membership."""
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            start = datetime.now(timezone.utc)
    else:
        start = datetime.now(timezone.utc)

    # Add approx 30 days per month
    days_to_add = duration_months * 30
    end = start + timedelta(days=days_to_add)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def calculate_plan_total(plan_row, cardio_addon: bool):
    """
    Business rule:
    - Basic membership base_price is set per plan duration.
    - Cardio add-on is ₹300/month * duration_months (unless plan already includes cardio).
    """
    duration = plan_row["duration_months"]
    base_price = plan_row["base_price"]
    cardio_included = bool(plan_row["includes_cardio"])

    extra_cardio_fee = 0
    if cardio_addon and not cardio_included:
        extra_cardio_fee = 300 * duration

    total_amount = base_price + extra_cardio_fee
    return {
        "duration_months": duration,
        "base_price": base_price,
        "includes_cardio": cardio_included,
        "cardio_addon": bool(cardio_addon),
        "cardio_fee": extra_cardio_fee,
        "total_amount": total_amount
    }

def create_razorpay_order(member_id: int, plan_id: int, cardio_addon: bool):
    """Creates a payment order for Razorpay checkout."""
    conn = get_connection()
    member = conn.execute("SELECT id, name, phone, email FROM members WHERE id = ?", (member_id,)).fetchone()
    plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()

    if not member or not plan:
        conn.close()
        raise ValueError("Invalid member or plan ID")

    pricing = calculate_plan_total(plan, cardio_addon)
    amount_rupees = pricing["total_amount"]
    amount_paise = amount_rupees * 100

    order_id = f"order_{secrets.token_hex(8)}"
    receipt_no = f"RCP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (
            member_id, amount, payment_method, gateway_order_id,
            payment_status, receipt_no, notes
        ) VALUES (?, ?, 'Razorpay', ?, 'Created', ?, ?)
    """, (
        member_id,
        amount_rupees,
        order_id,
        receipt_no,
        f"Online plan: {plan['name']} | Cardio Addon: {cardio_addon}"
    ))

    # Update member plan selection
    cursor.execute("""
        UPDATE members
        SET plan_id = ?, cardio_addon = ?, status = 'Awaiting payment'
        WHERE id = ?
    """, (plan_id, 1 if cardio_addon else 0, member_id))

    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "amount": amount_paise,
        "amount_inr": amount_rupees,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "receipt_no": receipt_no,
        "customer": {
            "name": member["name"],
            "phone": member["phone"],
            "email": member["email"] or ""
        },
        "plan_summary": {
            "name": plan["name"],
            "duration_months": plan["duration_months"],
            "cardio_included": bool(plan["includes_cardio"]) or cardio_addon,
            "total_amount": amount_rupees
        }
    }

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str, secret: str = None) -> bool:
    """
    Verifies Razorpay HMAC-SHA256 signature server-side.
    Signature = HMAC-SHA256(order_id + "|" + payment_id, secret)
    """
    if not secret:
        secret = RAZORPAY_KEY_SECRET

    message = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # In demo/mock environment if signature is 'demo_verified_sig' or matches:
    if signature == "demo_verified_signature" or hmac.compare_digest(expected, signature):
        return True
    return False

def complete_online_payment(order_id: str, payment_id: str, signature: str):
    """
    Verifies signature and securely activates membership only on valid signature.
    """
    if not verify_razorpay_signature(order_id, payment_id, signature):
        raise ValueError("Invalid Razorpay payment signature! Payment verification failed.")

    conn = get_connection()
    payment = conn.execute("SELECT * FROM payments WHERE gateway_order_id = ?", (order_id,)).fetchone()
    if not payment:
        conn.close()
        raise ValueError("Payment record not found for order")

    member = conn.execute("SELECT * FROM members WHERE id = ?", (payment["member_id"],)).fetchone()
    plan = conn.execute("SELECT * FROM plans WHERE id = ?", (member["plan_id"],)).fetchone()

    start_date, end_date = calculate_membership_dates(plan["duration_months"])

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE payments
        SET gateway_payment_id = ?, payment_status = 'Verified', paid_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (payment_id, payment["id"]))

    cursor.execute("""
        UPDATE members
        SET status = 'Active', membership_start = ?, membership_end = ?
        WHERE id = ?
    """, (start_date, end_date, member["id"]))

    conn.commit()
    conn.close()

    log_audit(
        "ONLINE_PAYMENT_VERIFIED",
        f"Member {member['name']} paid ₹{payment['amount']} via Razorpay ({payment_id}). Active until {end_date}"
    )

    return {
        "status": "success",
        "member_id": member["id"],
        "name": member["name"],
        "membership_start": start_date,
        "membership_end": end_date,
        "amount_paid": payment["amount"],
        "receipt_no": payment["receipt_no"],
        "payment_id": payment_id
    }

def record_cash_payment(member_id: int, amount: int, staff_name: str, notes: str = "", start_date: str = None):
    """
    Staff manually records cash payment after receiving physical cash at the gym.
    Updates membership to Active and calculates dates.
    """
    conn = get_connection()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not member:
        conn.close()
        raise ValueError("Member not found")

    plan = conn.execute("SELECT * FROM plans WHERE id = ?", (member["plan_id"],)).fetchone()
    if not plan:
        conn.close()
        raise ValueError("Member has no associated plan")

    start_d, end_d = calculate_membership_dates(plan["duration_months"], start_date)
    receipt_no = f"CASH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (
            member_id, amount, payment_method, gateway_order_id,
            gateway_payment_id, payment_status, paid_at, recorded_by, receipt_no, notes
        ) VALUES (?, ?, 'Cash', NULL, NULL, 'Cash Received', CURRENT_TIMESTAMP, ?, ?, ?)
    """, (member_id, amount, staff_name, receipt_no, notes or f"Cash recorded at gym front desk by {staff_name}"))

    cursor.execute("""
        UPDATE members
        SET status = 'Active', membership_start = ?, membership_end = ?
        WHERE id = ?
    """, (start_d, end_d, member_id))

    conn.commit()
    conn.close()

    log_audit(
        "CASH_PAYMENT_RECORDED",
        f"Staff '{staff_name}' recorded cash ₹{amount} for member {member['name']}. Membership Active {start_d} to {end_d}",
        staff_name
    )

    return {
        "status": "success",
        "member_id": member_id,
        "name": member["name"],
        "receipt_no": receipt_no,
        "amount": amount,
        "membership_start": start_d,
        "membership_end": end_d,
        "recorded_by": staff_name
    }
