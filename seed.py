"""
Seed script: populates the database with realistic test data.

Creates:
  - 2 institutions
  - 4 trainers (2 per institution)
  - 15 students
  - 1 programme manager
  - 1 monitoring officer
  - 3 batches (across institutions)
  - 8 sessions with attendance records

Run:
    python seed.py
"""

import sys
import os
from datetime import date, time, datetime, timedelta, timezone

# Allow running from repo root
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from src.db.database import SessionLocal, Base, engine
import src.models  # noqa – register all ORM models
from src.models.user import User
from src.models.attendance import (
    Batch, BatchTrainer, BatchStudent, BatchInvite,
    SessionModel, Attendance,
)
from src.core.security import hash_password

PASSWORD = "Password123!"

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Clear existing data (order matters for FKs) ────────────────────
        db.query(Attendance).delete()
        db.query(SessionModel).delete()
        db.query(BatchInvite).delete()
        db.query(BatchStudent).delete()
        db.query(BatchTrainer).delete()
        db.query(Batch).delete()
        db.query(User).delete()
        db.commit()

        print("Cleared existing data.")

        # ── Institutions ───────────────────────────────────────────────────
        inst1 = User(name="Sunrise Skills Institute", email="sunrise@inst.com",
                     hashed_password=hash_password(PASSWORD), role="institution")
        inst2 = User(name="Horizon Vocational Centre", email="horizon@inst.com",
                     hashed_password=hash_password(PASSWORD), role="institution")
        db.add_all([inst1, inst2])
        db.flush()

        # ── Trainers ───────────────────────────────────────────────────────
        trainer1 = User(name="Amit Sharma", email="amit@trainer.com",
                        hashed_password=hash_password(PASSWORD), role="trainer",
                        institution_id=inst1.id)
        trainer2 = User(name="Priya Nair", email="priya@trainer.com",
                        hashed_password=hash_password(PASSWORD), role="trainer",
                        institution_id=inst1.id)
        trainer3 = User(name="Ravi Kumar", email="ravi@trainer.com",
                        hashed_password=hash_password(PASSWORD), role="trainer",
                        institution_id=inst2.id)
        trainer4 = User(name="Sunita Rao", email="sunita@trainer.com",
                        hashed_password=hash_password(PASSWORD), role="trainer",
                        institution_id=inst2.id)
        db.add_all([trainer1, trainer2, trainer3, trainer4])
        db.flush()

        # ── Programme Manager & Monitoring Officer ─────────────────────────
        pm = User(name="Deepa Menon", email="deepa@programme.com",
                  hashed_password=hash_password(PASSWORD), role="programme_manager")
        mo = User(name="Vikram Iyer", email="vikram@monitoring.com",
                  hashed_password=hash_password(PASSWORD), role="monitoring_officer")
        db.add_all([pm, mo])
        db.flush()

        # ── Students ───────────────────────────────────────────────────────
        student_data = [
            ("Aarav Singh", "aarav@student.com"),
            ("Bhavna Patel", "bhavna@student.com"),
            ("Chetan Verma", "chetan@student.com"),
            ("Divya Reddy", "divya@student.com"),
            ("Esha Joshi", "esha@student.com"),
            ("Farhan Shaikh", "farhan@student.com"),
            ("Gita Pillai", "gita@student.com"),
            ("Harsh Gupta", "harsh@student.com"),
            ("Ishaan Mehta", "ishaan@student.com"),
            ("Jaya Shetty", "jaya@student.com"),
            ("Kiran Das", "kiran@student.com"),
            ("Lata Bhatt", "lata@student.com"),
            ("Manish Tiwari", "manish@student.com"),
            ("Nisha Patil", "nisha@student.com"),
            ("Omkar Kulkarni", "omkar@student.com"),
        ]
        students = [
            User(name=n, email=e, hashed_password=hash_password(PASSWORD), role="student")
            for n, e in student_data
        ]
        db.add_all(students)
        db.flush()

        # ── Batches ────────────────────────────────────────────────────────
        batch1 = Batch(name="Python Fundamentals – Batch A", institution_id=inst1.id)
        batch2 = Batch(name="Data Analytics – Batch B", institution_id=inst1.id)
        batch3 = Batch(name="Web Development – Batch C", institution_id=inst2.id)
        db.add_all([batch1, batch2, batch3])
        db.flush()

        # ── BatchTrainers ──────────────────────────────────────────────────
        db.add_all([
            BatchTrainer(batch_id=batch1.id, trainer_id=trainer1.id),
            BatchTrainer(batch_id=batch2.id, trainer_id=trainer2.id),
            BatchTrainer(batch_id=batch3.id, trainer_id=trainer3.id),
            BatchTrainer(batch_id=batch3.id, trainer_id=trainer4.id),  # shared batch
        ])

        # ── Enrol students in batches ──────────────────────────────────────
        # batch1: students 0-6
        for s in students[:7]:
            db.add(BatchStudent(batch_id=batch1.id, student_id=s.id))
        # batch2: students 5-11
        for s in students[5:12]:
            db.add(BatchStudent(batch_id=batch2.id, student_id=s.id))
        # batch3: students 10-14
        for s in students[10:]:
            db.add(BatchStudent(batch_id=batch3.id, student_id=s.id))

        db.flush()

        # ── Sessions (8 total) ─────────────────────────────────────────────
        today = date.today()
        sessions_raw = [
            # batch1 – 3 sessions
            SessionModel(batch_id=batch1.id, trainer_id=trainer1.id,
                         title="Intro to Python", date=today - timedelta(days=14),
                         start_time=time(9, 0), end_time=time(11, 0)),
            SessionModel(batch_id=batch1.id, trainer_id=trainer1.id,
                         title="Control Flow & Functions", date=today - timedelta(days=7),
                         start_time=time(9, 0), end_time=time(11, 0)),
            SessionModel(batch_id=batch1.id, trainer_id=trainer1.id,
                         title="OOP in Python", date=today - timedelta(days=1),
                         start_time=time(9, 0), end_time=time(11, 0)),
            # batch2 – 3 sessions
            SessionModel(batch_id=batch2.id, trainer_id=trainer2.id,
                         title="Data Wrangling with Pandas", date=today - timedelta(days=12),
                         start_time=time(14, 0), end_time=time(16, 0)),
            SessionModel(batch_id=batch2.id, trainer_id=trainer2.id,
                         title="Data Visualisation", date=today - timedelta(days=5),
                         start_time=time(14, 0), end_time=time(16, 0)),
            SessionModel(batch_id=batch2.id, trainer_id=trainer2.id,
                         title="SQL Fundamentals", date=today - timedelta(days=2),
                         start_time=time(14, 0), end_time=time(16, 0)),
            # batch3 – 2 sessions
            SessionModel(batch_id=batch3.id, trainer_id=trainer3.id,
                         title="HTML & CSS Basics", date=today - timedelta(days=10),
                         start_time=time(10, 0), end_time=time(12, 0)),
            SessionModel(batch_id=batch3.id, trainer_id=trainer4.id,
                         title="JavaScript Fundamentals", date=today - timedelta(days=3),
                         start_time=time(10, 0), end_time=time(12, 0)),
        ]
        db.add_all(sessions_raw)
        db.flush()

        # ── Attendance records ─────────────────────────────────────────────
        STATUSES = ["present", "present", "present", "late", "absent"]  # biased toward present

        def mark(session, student_list):
            for i, student in enumerate(student_list):
                db.add(Attendance(
                    session_id=session.id,
                    student_id=student.id,
                    status=STATUSES[i % len(STATUSES)],
                    marked_at=datetime.now(timezone.utc),
                ))

        mark(sessions_raw[0], students[:7])   # batch1 session 1 – all 7
        mark(sessions_raw[1], students[:6])   # batch1 session 2 – 6
        mark(sessions_raw[2], students[:5])   # batch1 session 3 – 5
        mark(sessions_raw[3], students[5:12]) # batch2 session 1 – all 7
        mark(sessions_raw[4], students[5:11]) # batch2 session 2 – 6
        mark(sessions_raw[5], students[5:10]) # batch2 session 3 – 5
        mark(sessions_raw[6], students[10:])  # batch3 session 1 – all 5
        mark(sessions_raw[7], students[10:14])# batch3 session 2 – 4

        db.commit()
        print("\n✅ Seed complete! Test accounts (password for all: Password123!):\n")
        print("  Role                | Email")
        print("  ------------------- | ---------------------------")
        print(f"  institution         | {inst1.email}")
        print(f"  institution         | {inst2.email}")
        print(f"  trainer             | {trainer1.email}")
        print(f"  trainer             | {trainer2.email}")
        print(f"  trainer             | {trainer3.email}")
        print(f"  trainer             | {trainer4.email}")
        print(f"  programme_manager   | {pm.email}")
        print(f"  monitoring_officer  | {mo.email}")
        print(f"  student (sample)    | {students[0].email}")
        print(f"\n  IDs → inst1={inst1.id}, inst2={inst2.id}")
        print(f"        batch1={batch1.id}, batch2={batch2.id}, batch3={batch3.id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
