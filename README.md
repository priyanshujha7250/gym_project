# FIT NATION & Digital Management Platform

A modern, mobile-friendly gym website and comprehensive management portal designed to help gym owners attract new members, explain facilities and transparent membership options, build trust through certified trainer guidance, and simplify member registrations, renewals, and payment tracking.

---

## 🎯 Key Value & Business Rules

1. **Beginner-Friendly Onboarding**: Real video tutorials and machine setup instructions explaining pin adjustment, biomechanics, safe technique, and common mistakes to prevent intimidation for first-time gym goers.
2. **Transparent Membership & Pricing Logic**:
   - **Basic Membership**: Starting at **₹1,000/month**. Includes full strength machines, free weights, dumbbells, lockers, and floor trainer guidance.
   - **Crucial Rule**: Basic Membership **does NOT include cardio equipment**.
   - **Cardio Add-On**: Optional add-on at **+₹300/month** (e.g. Basic + Cardio is **₹1,300/month**).
   - **Multi-Month Durations**: Genuine savings are supported for 1-month, 3-month (Quarterly), 6-month (Half-yearly), and 12-month (Annual) plans.
3. **Dual Payment Workflows**:
   - **Online Razorpay Flow**: Server-side HMAC-SHA256 signature verification, instant activation, and digital receipts.
   - **Cash-at-Gym Flow**: Allows prospects to reserve online with status *Awaiting payment*, pay cash at the gym reception desk, where staff record payment to activate access and print/generate a cash receipt.
4. **Certified Nutrition Framework**:
   - Evidence-based general nutrition guidelines (protein intake, Indian vegetarian sources, pre/post workout fuel).
   - Clear professional boundary notice with a personalized dietary consultation inquiry workflow.
5. **Developer Service Pricing Agreement**:
   - **First 30 days (Introductory Pilot)**: ₹500.
   - **Ongoing Monthly Service & Maintenance**: ₹1,000/month.

---

## 🏗️ Architecture & Tech Stack

- **Frontend**: Responsive Single-Page Architecture using HTML5, modern CSS3 (Custom Properties, Glassmorphism, CSS Grid, Athletic Dark Theme), and Vanilla JavaScript.
  - Razorpay Checkout SDK integration with fallback testing mode.
  - Filterable equipment catalog & machine tutorial video modal.
  - Dynamic duration switcher & interactive real-time price calculator.
  - Interactive member registration and enquiry booking forms.
- **Backend**: Python 3 multi-threaded HTTP server (`http.server.ThreadingHTTPServer`) with zero third-party dependencies required for instant, reliable operation.
  - RESTful JSON API endpoints for public & staff operations.
  - Secure PBKDF2-HMAC-SHA256 password hashing.
  - 24-hour cryptographic session tokens with role-based access control.
  - Razorpay HMAC-SHA256 signature verification engine.
  - Comprehensive operational audit logging.
- **Database**: SQLite3 (`gym_platform.db`) with Write-Ahead Logging (WAL) and foreign keys enabled:
  - `admins`, `admin_sessions`, `plans`, `members`, `enquiries`, `payments`, `equipment`, `trainers`, `nutrition_resources`, `diet_requests`, `audit_logs`.

---

## 🚀 Quick Start Guide

### 1. Launch the Platform
From the project root directory, run:
```bash
./start.sh
```
Or directly:
```bash
PYTHONPATH=backend python3 backend/app.py
```

The application will start on **http://localhost:8000/**.

### 2. Access the Portals
- **Public Website**: [http://localhost:8000/](http://localhost:8000/)
- **Admin Management Portal**: [http://localhost:8000/admin](http://localhost:8000/admin)

### 3. Default Staff Login Credentials
| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Gym Manager / Owner** | `admin@gym.com` | `admin123` | Full administrative control, plans, stats, audit |
| **Front Desk Staff** | `staff@gym.com` | `staff123` | Member registrations, enquiries, cash recording |
| **Senior Trainer** | `trainer@gym.com` | `trainer123` | Equipment tutorials, diet consultation reviews |

---

## 🧪 Testing & Verification

The project includes unit and integration test suites:

### Run Core Logic Tests:
```bash
PYTHONPATH=backend python3 backend/test_backend.py
```
*Verifies PBKDF2 authentication, ₹300/mo cardio add-on business rules, Razorpay order/signature verification, and staff cash payment workflows.*

### Run API Integration Tests:
```bash
PYTHONPATH=backend python3 backend/test_api_integration.py
```
*Verifies all REST API endpoints, enquiry workflows, online payment completions, cash collections, and admin statistics.*

---

## 📂 Project Directory Structure

```
gym_project/
├── backend/
│   ├── app.py                   # Multi-threaded HTTP server & REST routing engine
│   ├── database.py              # SQLite schema definition, connection manager & audit log
│   ├── auth.py                  # PBKDF2 password hashing & token session manager
│   ├── payments.py              # Razorpay order generation, HMAC verification & cash logic
│   ├── seed_data.py             # Seed data (plans, equipment, trainers, nutrition, members)
│   ├── test_backend.py          # Unit test suite for payment & auth rules
│   ├── test_api_integration.py  # Comprehensive API integration test suite
│   └── gym_platform.db          # SQLite database (auto-created on startup)
├── public/
│   ├── index.html               # Main customer-facing website
│   ├── admin.html               # Gym staff & owner management dashboard
│   ├── css/
│   │   ├── styles.css           # Customer website styling (dark/neon athletic theme)
│   │   └── admin.css            # Admin portal styling (metrics cards, data tables, modals)
│   └── js/
│       ├── main.js              # Interactive filters, plan selector, tutorial modals & forms
│       ├── payment.js           # Razorpay checkout & test simulator integration
│       └── admin.js             # Admin dashboard state, cash recording & renewals
├── start.sh                     # Automated startup script
└── README.md                    # Project documentation & agreement reference
```

---

## 📋 REST API Reference

### Public APIs
- `GET /api/plans` — Fetch active membership plans with duration, pricing, and cardio details.
- `GET /api/equipment?category=<cat>` — Fetch equipment list with setup guides and video tutorials.
- `GET /api/trainers` — List certified floor coaches and floor availability hours.
- `GET /api/nutrition` — List educational nutrition blueprints and guidelines.
- `POST /api/enquiries` — Submit prospect contact or gym tour inquiry.
- `POST /api/diet-requests` — Submit dietary preference consultation questionnaire.
- `POST /api/members/register` — Register member with choice of Razorpay online or Cash at Gym.
- `POST /api/payments/verify` — Server-side verification of Razorpay signature.

### Staff / Admin Protected APIs (`Authorization: Bearer <token>`)
- `POST /api/admin/login` — Authenticate staff and obtain session token.
- `GET /api/admin/me` — Validate session and fetch current admin profile.
- `GET /api/admin/stats` — Fetch revenue (Total, Online, Cash), active members, and expiry alerts.
- `GET /api/members` — Member directory with status, plan, and payment records.
- `POST /api/payments/cash` — Staff records physical cash received at gym front desk.
- `PUT /api/members/<id>/renew` — Extends member expiry date by plan duration.
- `PUT /api/members/<id>` — Update member status, start/end dates, or notes.
- `GET /api/enquiries` — View prospect leads and update statuses (*New*, *Contacted*, *Converted*).
- `POST /api/plans` — Create new membership plan.
- `POST /api/equipment` — Add equipment and video tutorial links.
- `GET /api/admin/audit-logs` — Tamper-evident operational audit trail.

---

## 🔒 Security & Best Practices

1. **Server-Side Verification**: Online payments are only marked successful after backend cryptographic verification (`hmac.compare_digest`) against the Razorpay secret key.
2. **Environment Variable Configuration**:
   ```bash
   export RAZORPAY_KEY_ID="rzp_live_yourActualKey"
   export RAZORPAY_KEY_SECRET="yourActualSecret"
   ```
3. **Audit Trail**: Every cash collection, membership renewal, plan change, or admin login is immutably logged with timestamp, initiator name, and operational details.
4. **Data Privacy**: Only necessary contact details are gathered. Clear consent and disclaimer checkboxes are presented before submission.
