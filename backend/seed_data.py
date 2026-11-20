import json
from database import get_connection, init_db, log_audit
from auth import hash_password

def seed_all():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM members")
    cursor.execute("DELETE FROM plans")
    cursor.execute("DELETE FROM admin_sessions")
    cursor.execute("DELETE FROM admins")
    admins = [
        ("Gym Owner & Manager", "admin@gym.com", hash_password("admin123"), "admin"),
        ("Front Desk Staff", "staff@gym.com", hash_password("staff123"), "staff"),
        ("Senior Head Trainer", "trainer@gym.com", hash_password("trainer123"), "trainer")
    ]
    cursor.executemany(
        "INSERT INTO admins (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        admins
    )

    # 2. Plans
    plans = [
        (
            "Basic Monthly",
            1,
            1000,
            300,
            0,
            json.dumps([
                "Full strength-training machines access",
                "Dumbbells & free weights zone",
                "Locker & changing room facilities",
                "Complimentary machine tutorial video access",
                "Basic in-person trainer guidance & setup assistance",
                "Cardio equipment: NOT INCLUDED (Optional +₹300/mo)"
            ]),
            "Standard monthly rate"
        ),
        (
            "Basic + Cardio Monthly",
            1,
            1300,
            0,
            1,
            json.dumps([
                "Full strength-training machines access",
                "Dumbbells & free weights zone",
                "Full cardio zone access (Treadmills, Cycles, Cross-Trainers)",
                "Locker & changing room facilities",
                "Complimentary machine tutorial video access",
                "Basic in-person trainer guidance & setup assistance",
                "Cardio equipment: INCLUDED"
            ]),
            "Most popular for beginners"
        ),
        (
            "Basic Quarterly (3 Months)",
            3,
            2850,
            300,
            0,
            json.dumps([
                "Full strength-training machines access",
                "Dumbbells & free weights zone",
                "Locker & shower facilities",
                "Machine tutorial video library",
                "Dedicated trainer posture checks",
                "Cardio equipment: NOT INCLUDED (Optional +₹300/mo)"
            ]),
            "Save ₹150 (Effective ₹950/mo)"
        ),
        (
            "Basic + Cardio Quarterly (3 Months)",
            3,
            3700,
            0,
            1,
            json.dumps([
                "Full strength-training machines access",
                "Dumbbells & free weights zone",
                "Full cardio equipment access included",
                "Locker & shower facilities",
                "Machine tutorial video library",
                "Dedicated trainer posture checks",
                "Cardio equipment: INCLUDED"
            ]),
            "Save ₹200 vs monthly"
        ),
        (
            "Basic Half-Yearly (6 Months)",
            6,
            5400,
            300,
            0,
            json.dumps([
                "Full strength machines & weight training",
                "Free weights & power racks",
                "Locker & shower facilities",
                "Progress tracking & form reviews",
                "Cardio equipment: NOT INCLUDED (Optional +₹300/mo)"
            ]),
            "Save ₹600 (Effective ₹900/mo)"
        ),
        (
            "Basic + Cardio Half-Yearly (6 Months)",
            6,
            7000,
            0,
            1,
            json.dumps([
                "Full strength & cardio access included",
                "Free weights & power racks",
                "Unlimited cardio sessions",
                "Locker & shower facilities",
                "Progress tracking & form reviews",
                "Cardio equipment: INCLUDED"
            ]),
            "Save ₹800 vs monthly"
        ),
        (
            "Basic Annual (12 Months)",
            12,
            9600,
            300,
            0,
            json.dumps([
                "Full 12 months strength facility access",
                "Free weights, racks, & cables",
                "Locker & shower facilities",
                "1 Free dietary consultation roadmap",
                "Cardio equipment: NOT INCLUDED (Optional +₹300/mo)"
            ]),
            "Save ₹2,400 (Effective ₹800/mo - 2 months free!)"
        ),
        (
            "Basic + Cardio Annual (12 Months)",
            12,
            12480,
            0,
            1,
            json.dumps([
                "Full 12 months strength + cardio access",
                "All machines, treadmills & cross-trainers",
                "Locker & shower facilities",
                "1 Free dietary consultation roadmap",
                "Cardio equipment: INCLUDED"
            ]),
            "Save ₹3,120 vs paying monthly"
        )
    ]
    cursor.executemany(
        """INSERT INTO plans (
            name, duration_months, base_price, cardio_price, includes_cardio, features, savings_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        plans
    )

    # 3. Equipment & Tutorials
    cursor.execute("DELETE FROM equipment")
    equipment = [
        (
            "Seated Chest Press Machine",
            "Strength Machines",
            "Targeted compound exercise for pectorals, anterior deltoids, and triceps with safe guided trajectory.",
            "Great for beginners because the fixed path eliminates stabilization risk while building chest strength.",
            "1. Adjust seat height so handles align with mid-chest level.\n2. Keep feet flat on floor and shoulder blades pinned against the back pad.\n3. Grip handles comfortably without bending wrists backwards.\n4. Exhale as you push forward smoothly, stopping just short of locking your elbows.",
            "Flaring elbows excessively high (keep at 45-60 degree angle); arching lower back off the pad.",
            "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/sqOw2Y68ecY"
        ),
        (
            "Lat Pulldown & Cable Row",
            "Strength Machines",
            "Builds upper body pulling strength, broad back muscles (latissimus dorsi), and posture muscles.",
            "Essential foundation for back health and core stability before attempting bodyweight pull-ups.",
            "1. Adjust the thigh pad snugly over your quads to prevent lifting off the seat.\n2. Grasp the wide bar slightly wider than shoulder width.\n3. Lean back very slightly (10-15 degrees) with chest lifted.\n4. Pull elbows down towards your ribs, drawing the bar down to collarbone level.",
            "Swinging your whole torso backward with momentum; pulling the bar behind your neck (dangerous for cervical spine).",
            "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/CAwf7n6Luuc"
        ),
        (
            "45-Degree Incline Leg Press",
            "Strength Machines",
            "High-capacity lower body compound machine focusing on quadriceps, hamstrings, and glutes without spine loading.",
            "Ideal for beginners to develop leg power safely without balancing a heavy barbell on their shoulders.",
            "1. Sit fully in the seat with hips firmly pressed against the backrest.\n2. Place feet shoulder-width apart in the center of the sled.\n3. Release safety catches while holding the side handles.\n4. Lower the weight smoothly until knees are bent to approximately 90 degrees, then push through heels.",
            "Letting knees cave inwards; letting lower back peel off the seat at the bottom; locking knees forcefully at top.",
            "https://images.unsplash.com/photo-1434682881908-b43d0467b798?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/yZmx_Ac3880"
        ),
        (
            "Commercial Grade Treadmill",
            "Cardio",
            "Shock-absorbing motorized running treadmill with variable speed, incline, and heart rate monitoring.",
            "Cardio equipment requires Cardio Add-on (+₹300/mo) or Basic + Cardio Plan. Superb for aerobic stamina and calorie burn.",
            "1. Always clip the red safety lanyard to your clothing before starting.\n2. Straddle the side rails while pressing Quick Start.\n3. Begin at a brisk walking pace (3.5 - 4.5 km/h) before jogging.\n4. Maintain upright posture looking forward, not down at feet.",
            "Holding tightly onto side rails while leaning back; looking down at phone causing neck strain; sudden stops without cooling down.",
            "https://images.unsplash.com/photo-1576678927484-cc907957088c?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/8_bE9b9G2dI"
        ),
        (
            "Stationary Air & Spin Bike",
            "Cardio",
            "Low-impact cardiovascular conditioning machine with flywheel resistance, easy on knees and joints.",
            "Requires Cardio Add-on. Excellent for high-intensity intervals (HIIT) or steady-state endurance training.",
            "1. Adjust seat height so that your knee has a slight 5-10 degree bend at the lowest pedal point.\n2. Adjust handlebar height to avoid rounding lower back.\n3. Secure shoe straps firmly over forefoot.\n4. Pedal at a steady rhythm (70-90 RPM).",
            "Saddle set too low causing knee cap discomfort; slumping shoulders forward; bouncing excessively in the saddle.",
            "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/7V8n6g7-j7g"
        ),
        (
            "Heavy-Duty Squat Power Rack",
            "Free Weights",
            "Professional barbell safety cage with adjustable J-hooks and steel safety spotter arms.",
            "The king of lower body strength exercises. Always ask a trainer for initial bar path setup and depth check.",
            "1. Set safety spotter bars just below your lowest squat depth.\n2. Position barbell at mid-chest height.\n3. Step under bar resting it across upper traps (high bar).\n4. Step back 2 paces, squat keeping knees tracked over toes, hips descending between heels.",
            "Lifting heels off the ground; rounding lower back; squatting without setting safety spotter bars.",
            "https://images.unsplash.com/photo-1541534741688-6078c6bfb5c5?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/bEv6CCg2BC8"
        ),
        (
            "Dumbbell & Adjustable Bench Station",
            "Free Weights",
            "Complete free-weight dumbbell pairs from 2.5 kg up to 35 kg with heavy-duty multi-angle benches.",
            "Allows natural joint articulation for flat, incline, shoulder presses, curls, and lateral raises.",
            "1. Select a conservative weight you can control for 10-12 strict repetitions.\n2. Sit on bench with dumbbells resting vertically on knees.\n3. Kick dumbbells up to starting position as you lie back.\n4. Keep core braced and feet firmly planted.",
            "Dropping heavy dumbbells carelessly on rubber floor; arching spine to heave weight up; ego lifting with bad form.",
            "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/VmB1G1K7v94"
        ),
        (
            "Dual Adjustable Pulley (Cable Crossover)",
            "Functional",
            "Versatile dual-stack cable station providing continuous tension through full muscle range of motion.",
            "Great for rotator cuff warmups, chest flyes, tricep pushdowns, bicep curls, and core woodchoppers.",
            "1. Adjust pulley carriages to desired height pin.\n2. Choose appropriate attachment (rope, D-handles, straight bar).\n3. Take one step forward into a staggered stance for stability.\n4. Move weight using controlled tempo (2 seconds concentric, 3 seconds eccentric).",
            "Jerking weight with momentum; using whole body rocking rather than isolated joint movement.",
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=800&q=80",
            "https://www.youtube-nocookie.com/embed/taI4XduLp4M"
        )
    ]
    cursor.executemany(
        """INSERT INTO equipment (
            name, category, description, beginner_notes, setup_steps, common_mistakes, image_url, tutorial_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        equipment
    )

    # 4. Trainers
    cursor.execute("DELETE FROM trainers")
    trainers = [
        (
            "Rohit Verma",
            "Head Strength & Conditioning Coach",
            "Over 9 years of coaching experience helping beginners build strength safely without injury. Specializes in progressive overload and barbell mechanics.",
            "Certified Strength Coach (CSCS) | K11 Sports Science Diploma",
            "Beginner machine orientation, compound lift technique, mobility & injury prevention",
            "Available on gym floor every morning 6:00 AM - 11:00 AM. Ask him directly or book a free orientation slot at the desk.",
            "https://images.unsplash.com/photo-1567013127542-490d757e51fc?auto=format&fit=crop&w=600&q=80"
        ),
        (
            "Ananya Sharma",
            "Functional Movement & Transformation Specialist",
            "Passionate about making the gym feel welcoming, comfortable, and empowering for first-time visitors and women.",
            "ACE Certified Personal Trainer | Level 2 Kettlebell & Functional Movement",
            "Posture correction, fat loss conditioning, beginner workout confidence, core stability",
            "On floor 4:30 PM - 9:30 PM. Spot her in the functional training area or ask the front desk to introduce you.",
            "https://images.unsplash.com/photo-1594381898411-846e7d193883?auto=format&fit=crop&w=600&q=80"
        ),
        (
            "Vikram Singh",
            "Certified Fitness & Sports Nutritionist",
            "Guides members with evidence-based nutrition frameworks and sensible, non-restrictive diet planning tailored to Indian food habits.",
            "ISSA Certified Nutrition Specialist | Precision Nutrition Level 1",
            "Calorie balance, vegetarian protein optimization, pre/post workout nutrition, sustainable habits",
            "Holds weekly member nutrition Q&A sessions on Saturdays 5 PM. Individual review requests via website portal.",
            "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=600&q=80"
        )
    ]
    cursor.executemany(
        """INSERT INTO trainers (
            name, role_title, bio, qualifications, guidance_areas, how_to_reach, image_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        trainers
    )

    # 5. Nutrition Resources
    cursor.execute("DELETE FROM nutrition_resources")
    nutrition = [
        (
            "Beginner's Nutrition Blueprint: Protein & Energy",
            "General Guidelines",
            "A sensible, grounded guide to fueling workouts without extreme diets or expensive supplements.",
            json.dumps([
                "Target approximately 1.2 to 1.6 grams of protein per kg of bodyweight for muscle recovery.",
                "Prioritize whole grains, lentils, fresh vegetables, and adequate healthy fats.",
                "Drink 3 to 4 liters of water daily, especially around your workout window.",
                "Avoid crash starvation diets that deplete energy and cause muscle loss."
            ]),
            "Vikram Singh (ISSA Nutrition Specialist)"
        ),
        (
            "Vegetarian & Indian Protein Optimization",
            "Vegetarian Sources",
            "How to hit protein targets consistently using familiar, affordable Indian foods.",
            json.dumps([
                "Combine dal or legumes with rice or roti for complete amino acid profiles.",
                "Incorporate Paneer (cottage cheese), Tofu, Greek yogurt/Dahi, and Soya chunks (52g protein per 100g).",
                "Sprouted moong and chickpeas make excellent mid-morning or post-workout snacks.",
                "Whey or plant protein powder can be an optional, convenient supplement if food targets fall short."
            ]),
            "Vikram Singh (ISSA Nutrition Specialist)"
        ),
        (
            "Pre & Post Workout Meal Timing",
            "Meal Timing",
            "Maximize energy on the gym floor and optimize muscle repair after your session.",
            json.dumps([
                "Pre-workout (60-90 mins before): Complex carbohydrates with light protein (e.g. oats with banana, peanut butter toast).",
                "Hydration: Sip 200-300 ml water 20 minutes before training.",
                "Post-workout (within 2 hours): Balanced meal containing protein + carbohydrates for glycogen replenishment.",
                "Listen to your digestion: never train on a heavy stomach or completely empty stomach."
            ]),
            "Vikram Singh (ISSA Nutrition Specialist)"
        ),
        (
            "Safe Supplementation & Clear Boundaries",
            "Hydration",
            "Understanding what works versus marketing hype. Safety-first approach.",
            json.dumps([
                "Supplements are never a substitute for whole food, regular sleep, and consistent training.",
                "Consult a certified health professional before taking new ergogenic supplements.",
                "Never consume unregulated fat burners, steroids, or unverified powders.",
                "Creatine monohydrate (3-5g/day) is well-researched for strength, but ensure plenty of water."
            ]),
            "Vikram Singh (ISSA Nutrition Specialist)"
        )
    ]
    cursor.executemany(
        """INSERT INTO nutrition_resources (
            title, category, description, key_points, reviewed_by
        ) VALUES (?, ?, ?, ?, ?)""",
        nutrition
    )

    # 6. Sample Enquiries
    cursor.execute("DELETE FROM enquiries")
    enquiries = [
        ("Aarav Mehta", "9876543210", "aarav@example.com", "Basic Monthly", "Hi, I have never been to a gym before. Do trainers help with machine setup on day 1?", "Evening (6-8 PM)", "New"),
        ("Pooja Nair", "9812345678", "pooja.n@example.com", "Basic + Cardio Monthly", "Wanted to enquire about treadmill availability during peak morning hours.", "Morning (7-9 AM)", "Contacted"),
        ("Rahul Sharma", "9823456789", "rahul.sharma@example.com", "Basic Quarterly (3 Months)", "Interested in joining with a friend. Is there any partner discount?", "Weekend", "Converted")
    ]
    cursor.executemany(
        """INSERT INTO enquiries (
            name, phone, email, interested_plan, message, preferred_time, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        enquiries
    )

    # 7. Sample Members
    p1 = cursor.execute("SELECT id FROM plans WHERE name = 'Basic Monthly'").fetchone()[0]
    p2 = cursor.execute("SELECT id FROM plans WHERE name = 'Basic + Cardio Monthly'").fetchone()[0]
    p3 = cursor.execute("SELECT id FROM plans WHERE name = 'Basic Quarterly (3 Months)'").fetchone()[0]
    p4 = cursor.execute("SELECT id FROM plans WHERE name = 'Basic + Cardio Quarterly (3 Months)'").fetchone()[0]

    members = [
        ("Kunal Deshmukh", "9898989801", "kunal@example.com", p1, 0, "2026-11-01", "2026-12-01", "Active", "Prefers morning workouts"),
        ("Sneha Patil", "9898989802", "sneha@example.com", p2, 1, "2026-11-10", "2026-12-10", "Active", "Cardio enthusiast"),
        ("Amitabh Sen", "9898989803", "amitabh@example.com", p4, 1, "2026-10-15", "2027-01-15", "Active", "Paid quarterly Basic + Cardio"),
        ("Priyanka Rao", "9898989804", "priyanka@example.com", p1, 1, None, None, "Awaiting payment", "Enquired at front desk, cash pending"),
        ("Rohan Joshi", "9898989805", "rohan@example.com", p3, 0, "2026-08-01", "2026-11-01", "Expired", "Quarterly plan expired recently")
    ]
    cursor.executemany(
        """INSERT INTO members (
            name, phone, email, plan_id, cardio_addon, membership_start, membership_end, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        members
    )

    # 8. Sample Payments
    m1 = cursor.execute("SELECT id FROM members WHERE name = 'Kunal Deshmukh'").fetchone()[0]
    m2 = cursor.execute("SELECT id FROM members WHERE name = 'Sneha Patil'").fetchone()[0]
    m3 = cursor.execute("SELECT id FROM members WHERE name = 'Amitabh Sen'").fetchone()[0]

    payments = [
        (m1, 1000, "Cash", None, None, "Cash Received", "Front Desk Staff", "CASH-20261101-A1B", "Basic monthly cash collected"),
        (m2, 1300, "Razorpay", "order_8a12bc9837", "pay_8a12bc9837xyz", "Verified", None, "RCP-20261110-B2C", "Online plan Basic+Cardio"),
        (m3, 3700, "Cash", None, None, "Cash Received", "Gym Owner & Manager", "CASH-20261015-C3D", "Quarterly Basic+Cardio cash collected")
    ]
    cursor.executemany(
        """INSERT INTO payments (
            member_id, amount, payment_method, gateway_order_id, gateway_payment_id,
            payment_status, recorded_by, receipt_no, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        payments
    )

    # 9. Sample Diet Request
    cursor.execute("DELETE FROM diet_requests")
    diet_requests = [
        ("Kunal Deshmukh", "9898989801", "kunal@example.com", "Vegetarian", "Peanuts", "Muscle Gain", "₹3000-₹5000/mo", "Looking to gain 4kg lean muscle without dairy overload.", "Pending Review", None)
    ]
    cursor.executemany(
        """INSERT INTO diet_requests (
            name, phone, email, dietary_preference, allergies, primary_goal, budget_range, notes, status, reviewed_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        diet_requests
    )

    conn.commit()
    conn.close()

    log_audit("DATABASE_SEEDED", "Initialized database with plans, equipment, trainers, nutrition guides, and sample members")
    print("Database successfully seeded with realistic sample data!")

if __name__ == "__main__":
    seed_all()
