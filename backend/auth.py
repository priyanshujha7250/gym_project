import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from database import get_connection, log_audit

SESSION_DURATION_HOURS = 24

def hash_password(password: str, salt: str = None) -> str:
    """Hashes a password with salt using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a password against the stored salt$hash string."""
    try:
        salt, key_hex = stored_hash.split('$')
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False

def authenticate_admin(email: str, password: str):
    """Checks credentials and creates a session token if valid."""
    conn = get_connection()
    admin = conn.execute(
        "SELECT id, name, email, password_hash, role FROM admins WHERE email = ?",
        (email.strip().lower(),)
    ).fetchone()

    if not admin:
        conn.close()
        return None

    if not verify_password(admin["password_hash"], password):
        conn.close()
        return None

    # Generate session token
    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)

    conn.execute(
        "INSERT INTO admin_sessions (token, admin_id, expires_at) VALUES (?, ?, ?)",
        (token, admin["id"], expires_at.isoformat())
    )
    conn.commit()
    conn.close()

    log_audit("ADMIN_LOGIN", f"Admin {admin['name']} ({admin['email']}) logged in", admin["name"])

    return {
        "token": token,
        "admin": {
            "id": admin["id"],
            "name": admin["name"],
            "email": admin["email"],
            "role": admin["role"]
        },
        "expires_at": expires_at.isoformat()
    }

def get_admin_by_token(token: str):
    """Validates session token and returns admin profile."""
    if not token:
        return None

    conn = get_connection()
    session = conn.execute("""
        SELECT s.token, s.expires_at, a.id, a.name, a.email, a.role
        FROM admin_sessions s
        JOIN admins a ON s.admin_id = a.id
        WHERE s.token = ?
    """, (token,)).fetchone()
    conn.close()

    if not session:
        return None

    # Check expiry
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Token expired
            invalidate_token(token)
            return None
    except Exception:
        return None

    return {
        "id": session["id"],
        "name": session["name"],
        "email": session["email"],
        "role": session["role"]
    }

def invalidate_token(token: str):
    """Logs out by deleting session token."""
    conn = get_connection()
    conn.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
