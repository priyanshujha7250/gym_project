import os
import sys
import unittest
import json
from datetime import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_connection, log_audit
from seed_data import seed_all
from auth import hash_password, verify_password, authenticate_admin, get_admin_by_token
from payments import (
    calculate_plan_total,
    create_razorpay_order,
    verify_razorpay_signature,
    complete_online_payment,
    record_cash_payment
)

class TestGymPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Seed test database
        seed_all()

    def test_01_pricing_and_cardio_rules(self):
        """Verify the ₹300/mo cardio add-on business rule for different plans."""
        conn = get_connection()
        basic_monthly = conn.execute("SELECT * FROM plans WHERE name = 'Basic Monthly'").fetchone()
        basic_cardio_monthly = conn.execute("SELECT * FROM plans WHERE name = 'Basic + Cardio Monthly'").fetchone()
        basic_quarterly = conn.execute("SELECT * FROM plans WHERE name = 'Basic Quarterly (3 Months)'").fetchone()
        conn.close()

        # Basic 1-month without cardio: 1000
        calc1 = calculate_plan_total(basic_monthly, cardio_addon=False)
        self.assertEqual(calc1["total_amount"], 1000)
        self.assertFalse(calc1["cardio_addon"])

        # Basic 1-month WITH cardio add-on: 1000 + 300 = 1300
        calc2 = calculate_plan_total(basic_monthly, cardio_addon=True)
        self.assertEqual(calc2["total_amount"], 1300)
        self.assertEqual(calc2["cardio_fee"], 300)

        # Plan that already includes cardio: 1300 (no extra fee added even if toggle on)
        calc3 = calculate_plan_total(basic_cardio_monthly, cardio_addon=True)
        self.assertEqual(calc3["total_amount"], 1300)
        self.assertEqual(calc3["cardio_fee"], 0)

        # Basic 3-months WITH cardio add-on: 2850 + (300 * 3) = 3750
        calc4 = calculate_plan_total(basic_quarterly, cardio_addon=True)
        self.assertEqual(calc4["total_amount"], 2850 + 900)
        self.assertEqual(calc4["cardio_fee"], 900)

    def test_02_admin_authentication(self):
        """Verify secure PBKDF2 authentication and token generation."""
        # Valid login
        login_res = authenticate_admin("admin@gym.com", "admin123")
        self.assertIsNotNone(login_res)
        self.assertIn("token", login_res)
        token = login_res["token"]

        # Validate token
        admin = get_admin_by_token(token)
        self.assertIsNotNone(admin)
        self.assertEqual(admin["email"], "admin@gym.com")
        self.assertEqual(admin["role"], "admin")

        # Invalid password
        bad_res = authenticate_admin("admin@gym.com", "wrongpassword")
        self.assertIsNone(bad_res)

        # Invalid email
        nonexistent = authenticate_admin("unknown@gym.com", "admin123")
        self.assertIsNone(nonexistent)

    def test_03_cash_payment_workflow(self):
        """Verify staff recording cash payment sets membership to Active and calculates dates."""
        conn = get_connection()
        # Find Priyanka Rao (awaiting payment)
        member = conn.execute("SELECT id, status FROM members WHERE name = 'Priyanka Rao'").fetchone()
        self.assertIsNotNone(member)
        conn.close()

        res = record_cash_payment(
            member_id=member["id"],
            amount=1300,
            staff_name="Front Desk Staff",
            notes="Cash received at desk for Basic + Cardio monthly"
        )

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["receipt_no"].startswith("CASH-"))

        # Check member status updated
        conn = get_connection()
        updated_member = conn.execute("SELECT status, membership_start, membership_end FROM members WHERE id = ?", (member["id"],)).fetchone()
        conn.close()

        self.assertEqual(updated_member["status"], "Active")
        self.assertIsNotNone(updated_member["membership_start"])
        self.assertIsNotNone(updated_member["membership_end"])

    def test_04_online_payment_workflow(self):
        """Verify Razorpay order creation and server-side HMAC signature verification."""
        conn = get_connection()
        member = conn.execute("SELECT id FROM members LIMIT 1").fetchone()
        plan = conn.execute("SELECT id FROM plans WHERE name = 'Basic Monthly'").fetchone()
        conn.close()

        order = create_razorpay_order(member["id"], plan["id"], cardio_addon=True)
        self.assertTrue(order["order_id"].startswith("order_"))
        self.assertEqual(order["amount_inr"], 1300)
        self.assertEqual(order["amount"], 130000) # in paise

        # Test signature verification
        # 1. Invalid signature should fail
        with self.assertRaises(ValueError):
            complete_online_payment(order["order_id"], "pay_fake123", "invalid_signature")

        # 2. Valid signature in test/demo mode
        res = complete_online_payment(order["order_id"], "pay_test_succ123", "demo_verified_signature")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["amount_paid"], 1300)

if __name__ == "__main__":
    unittest.main()
