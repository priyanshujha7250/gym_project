import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym_platform.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admin_sessions (
        token TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration_months INTEGER NOT NULL,
        base_price INTEGER NOT NULL,
        cardio_price INTEGER NOT NULL DEFAULT 300,
        includes_cardio INTEGER NOT NULL DEFAULT 0,
        features TEXT NOT NULL,
        savings_text TEXT DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        plan_id INTEGER NOT NULL,
        cardio_addon INTEGER NOT NULL DEFAULT 0,
        membership_start DATE,
        membership_end DATE,
        status TEXT NOT NULL DEFAULT 'Enquiry',
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    );

    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        interested_plan TEXT,
        message TEXT,
        preferred_time TEXT,
        status TEXT NOT NULL DEFAULT 'New',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        payment_method TEXT NOT NULL, -- 'Razorpay' or 'Cash'
        gateway_order_id TEXT,
        gateway_payment_id TEXT,
        payment_status TEXT NOT NULL, -- 'Created', 'Captured', 'Verified', 'Cash Received', 'Failed'
        paid_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        recorded_by TEXT,
        receipt_no TEXT UNIQUE,
        notes TEXT,
        FOREIGN KEY (member_id) REFERENCES members(id)
    );

    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- 'Strength Machines', 'Free Weights', 'Cardio', 'Functional'
        description TEXT NOT NULL,
        beginner_notes TEXT NOT NULL,
        setup_steps TEXT NOT NULL,
        common_mistakes TEXT NOT NULL,
        image_url TEXT NOT NULL,
        tutorial_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS trainers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role_title TEXT NOT NULL,
        bio TEXT NOT NULL,
        qualifications TEXT NOT NULL,
        guidance_areas TEXT NOT NULL,
        how_to_reach TEXT NOT NULL,
        image_url TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS nutrition_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL, -- 'General Guidelines', 'Meal Timing', 'Vegetarian Sources', 'Hydration'
        description TEXT NOT NULL,
        key_points TEXT NOT NULL,
        reviewed_by TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS diet_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        dietary_preference TEXT NOT NULL, -- 'Vegetarian', 'Non-Vegetarian', 'Eggetarian', 'Vegan'
        allergies TEXT,
        primary_goal TEXT NOT NULL, -- 'Fat Loss', 'Muscle Gain', 'Endurance', 'General Health'
        budget_range TEXT,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'Pending Review',
        reviewed_by TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        admin_name TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def log_audit(action: str, details: str, admin_name: str = "System"):
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO audit_logs (action, details, admin_name) VALUES (?, ?, ?)",
            (action, details, admin_name)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to write audit log: {e}")

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully at:", DB_PATH)
