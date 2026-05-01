"""
Programme-level and Monitoring Officer endpoints.

GET /programme/summary        – Programme Manager: programme-wide summary
GET /monitoring/attendance    – Monitoring Officer: read-only, requires scoped token
POST /monitoring/attendance   – Returns 405 Method Not Allowed (per spec)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src.core.dependencies import require_roles, get_monitoring_user
from src.db.database import get_db
from src.models.user import User
from src.models.attendance import Batch, SessionModel, Attendance

programme_router = APIRouter(prefix="/programme", tags=["Programme"])
monitoring_router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# ── Programme Manager ──────────────────────────────────────────────────────────

@programme_router.get("/summary")
def programme_summary(
    current_user: User = Depends(require_roles("programme_manager")),
    db: Session = Depends(get_db),
):
    """Programme-wide attendance rollup across all institutions and batches."""
    batches = db.query(Batch).all()
    institution_map: dict[int, dict] = {}

    for batch in batches:
        inst_id = batch.institution_id
        if inst_id not in institution_map:
            inst_user = db.query(User).filter(User.id == inst_id).first()
            institution_map[inst_id] = {
                "institution_id": inst_id,
                "institution_name": inst_user.name if inst_user else "Unknown",
                "batch_count": 0,
                "total_records": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
            }
        institution_map[inst_id]["batch_count"] += 1

        sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch.id).all()
        for sess in sessions:
            records = db.query(Attendance).filter(Attendance.session_id == sess.id).all()
            institution_map[inst_id]["total_records"] += len(records)
            institution_map[inst_id]["present"] += sum(1 for r in records if r.status == "present")
            institution_map[inst_id]["absent"] += sum(1 for r in records if r.status == "absent")
            institution_map[inst_id]["late"] += sum(1 for r in records if r.status == "late")

    totals = {
        "total_records": sum(v["total_records"] for v in institution_map.values()),
        "present": sum(v["present"] for v in institution_map.values()),
        "absent": sum(v["absent"] for v in institution_map.values()),
        "late": sum(v["late"] for v in institution_map.values()),
    }

    return {
        "institutions": list(institution_map.values()),
        "programme_totals": totals,
    }


# ── Monitoring Officer ─────────────────────────────────────────────────────────

@monitoring_router.get("/attendance")
def monitoring_attendance(
    current_user: User = Depends(get_monitoring_user),
    db: Session = Depends(get_db),
):
    """
    Read-only view of all attendance records across the entire programme.
    Requires the scoped monitoring token (not the standard login token).
    """
    records = db.query(Attendance).all()
    return {
        "total_records": len(records),
        "records": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "student_id": r.student_id,
                "status": r.status,
                "marked_at": r.marked_at.isoformat() if r.marked_at else None,
            }
            for r in records
        ],
    }


@monitoring_router.post("/attendance")
@monitoring_router.put("/attendance")
@monitoring_router.patch("/attendance")
@monitoring_router.delete("/attendance")
def monitoring_attendance_write_blocked():
    """Per spec: any non-GET method on /monitoring/attendance returns 405."""
    raise HTTPException(status_code=405, detail="Method Not Allowed")
