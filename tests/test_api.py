"""
Required tests (per assignment):
  1. Successful student signup and login, asserting a valid JWT is returned
  2. A trainer creating a session with all required fields
  3. A student successfully marking their own attendance
  4. A POST to /monitoring/attendance returning 405
  5. A request to a protected endpoint with no token returning 401

Tests 1 and 3 also run against the real database (marked real_db).
"""

import pytest
from jose import jwt

from src.core.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _signup(client, email, password, role, name="Test User"):
    return client.post("/auth/signup", json={
        "name": name, "email": email, "password": password, "role": role
    })


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _setup_trainer_with_batch(client):
    """Create institution → trainer → batch → return trainer token + batch_id."""
    inst_r = _signup(client, "inst@test.com", "Pass123!", "institution", "Test Inst")
    assert inst_r.status_code == 201
    inst_id = jwt.decode(
        inst_r.json()["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )["sub"]

    # Need institution's numeric id from DB — easiest: login and check id via a batch call
    # We'll just store inst signup token and use institution_id workaround:
    # Re-fetch institution id from token
    inst_token = inst_r.json()["access_token"]

    # Create trainer (no institution_id needed for this test)
    trainer_r = _signup(client, "trainer@test.com", "Pass123!", "trainer")
    assert trainer_r.status_code == 201
    trainer_token = trainer_r.json()["access_token"]

    # Trainer creates a batch — needs an institution_id
    # Use the institution user's numeric id from their JWT sub
    inst_numeric_id = int(inst_id)
    batch_r = client.post(
        "/batches",
        json={"name": "Batch Alpha", "institution_id": inst_numeric_id},
        headers=_auth_header(trainer_token),
    )
    assert batch_r.status_code == 201, batch_r.text
    batch_id = batch_r.json()["id"]

    return trainer_token, batch_id


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 – Student signup and login return a valid JWT
# ═══════════════════════════════════════════════════════════════════════════════

def test_student_signup_and_login_returns_jwt(client):
    """Signup then login as a student — both should return valid, decodable JWTs."""
    signup_r = _signup(client, "student@test.com", "Pass123!", "student", "Alice")
    assert signup_r.status_code == 201
    signup_data = signup_r.json()
    assert "access_token" in signup_data

    # Decode and validate token structure
    payload = jwt.decode(
        signup_data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload["role"] == "student"
    assert "sub" in payload
    assert "exp" in payload

    # Login with same credentials
    login_r = _login(client, "student@test.com", "Pass123!")
    assert login_r.status_code == 200
    login_data = login_r.json()
    assert "access_token" in login_data

    payload2 = jwt.decode(
        login_data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload2["role"] == "student"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 – Trainer creates a session with all required fields
# ═══════════════════════════════════════════════════════════════════════════════

def test_trainer_creates_session(client):
    """Trainer can create a session after being assigned to a batch."""
    trainer_token, batch_id = _setup_trainer_with_batch(client)

    session_r = client.post(
        "/sessions",
        json={
            "title": "Intro Session",
            "date": "2025-06-01",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "batch_id": batch_id,
        },
        headers=_auth_header(trainer_token),
    )
    assert session_r.status_code == 201, session_r.text
    data = session_r.json()
    assert data["title"] == "Intro Session"
    assert data["batch_id"] == batch_id


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 – Student successfully marks own attendance
# ═══════════════════════════════════════════════════════════════════════════════

def test_student_marks_attendance(client):
    """Student joins a batch via invite, then marks attendance for a session."""
    trainer_token, batch_id = _setup_trainer_with_batch(client)

    # Create a session
    session_r = client.post(
        "/sessions",
        json={
            "title": "Test Session",
            "date": "2025-06-10",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "batch_id": batch_id,
        },
        headers=_auth_header(trainer_token),
    )
    assert session_r.status_code == 201
    session_id = session_r.json()["id"]

    # Trainer generates an invite
    invite_r = client.post(
        f"/batches/{batch_id}/invite",
        headers=_auth_header(trainer_token),
    )
    assert invite_r.status_code == 200, invite_r.text
    invite_token = invite_r.json()["token"]

    # Student signs up and joins batch
    student_r = _signup(client, "student2@test.com", "Pass123!", "student", "Bob")
    assert student_r.status_code == 201
    student_token = student_r.json()["access_token"]

    join_r = client.post(
        "/batches/join",
        json={"token": invite_token},
        headers=_auth_header(student_token),
    )
    assert join_r.status_code == 200, join_r.text

    # Student marks attendance
    mark_r = client.post(
        "/attendance/mark",
        json={"session_id": session_id, "status": "present"},
        headers=_auth_header(student_token),
    )
    assert mark_r.status_code == 201, mark_r.text
    assert mark_r.json()["status"] == "present"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 – POST /monitoring/attendance returns 405
# ═══════════════════════════════════════════════════════════════════════════════

def test_post_monitoring_attendance_returns_405(client):
    """Per spec: any non-GET method on /monitoring/attendance must return 405."""
    response = client.post("/monitoring/attendance", json={})
    assert response.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5 – Protected endpoint with no token returns 401
# ═══════════════════════════════════════════════════════════════════════════════

def test_protected_endpoint_without_token_returns_401(client):
    """Hitting a protected endpoint with no Authorization header returns 401."""
    response = client.post("/sessions", json={
        "title": "No Auth",
        "date": "2025-06-01",
        "start_time": "09:00:00",
        "end_time": "11:00:00",
        "batch_id": 1,
    })
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# BONUS – Real DB Tests (tests 1 and 3 variant against live Neon PostgreSQL)
# ═══════════════════════════════════════════════════════════════════════════════

def test_student_signup_login_real_db(real_client):
    """Test 1 against the real database."""
    import time as t
    unique = str(int(t.time()))
    signup_r = _signup(real_client, f"realstudent{unique}@test.com", "Pass123!", "student")
    assert signup_r.status_code == 201
    token = signup_r.json()["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["role"] == "student"

    login_r = _login(real_client, f"realstudent{unique}@test.com", "Pass123!")
    assert login_r.status_code == 200


def test_student_marks_attendance_real_db(real_client):
    """Test 3 against the real database — full join-and-mark flow."""
    import time as t
    unique = str(int(t.time()))

    # Institution
    inst_r = _signup(real_client, f"realinst{unique}@test.com", "Pass123!", "institution", "RealInst")
    assert inst_r.status_code == 201
    inst_id = int(jwt.decode(inst_r.json()["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"])

    # Trainer
    trainer_r = _signup(real_client, f"realtrainer{unique}@test.com", "Pass123!", "trainer")
    assert trainer_r.status_code == 201
    trainer_token = trainer_r.json()["access_token"]

    # Batch
    batch_r = real_client.post("/batches", json={"name": "Real Batch", "institution_id": inst_id},
                               headers=_auth_header(trainer_token))
    assert batch_r.status_code == 201
    batch_id = batch_r.json()["id"]

    # Session
    sess_r = real_client.post("/sessions", json={
        "title": "Real Session", "date": "2025-07-01",
        "start_time": "09:00:00", "end_time": "11:00:00", "batch_id": batch_id
    }, headers=_auth_header(trainer_token))
    assert sess_r.status_code == 201
    session_id = sess_r.json()["id"]

    # Invite → student joins → marks
    inv_r = real_client.post(f"/batches/{batch_id}/invite", headers=_auth_header(trainer_token))
    assert inv_r.status_code == 200
    inv_token = inv_r.json()["token"]

    stu_r = _signup(real_client, f"realstudent2{unique}@test.com", "Pass123!", "student")
    assert stu_r.status_code == 201
    stu_token = stu_r.json()["access_token"]

    join_r = real_client.post("/batches/join", json={"token": inv_token}, headers=_auth_header(stu_token))
    assert join_r.status_code == 200

    mark_r = real_client.post("/attendance/mark",
                              json={"session_id": session_id, "status": "present"},
                              headers=_auth_header(stu_token))
    assert mark_r.status_code == 201
    assert mark_r.json()["status"] == "present"
