"""
Session endpoints.

POST /sessions              – Trainer: create a session
GET  /sessions/{id}/attendance – Trainer: full attendance list for a session
"""

from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.dependencies import require_roles
from src.db.database import get_db
from src.models.user import User
from src.models.attendance import SessionModel, Attendance, BatchTrainer, BatchStudent

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str
    date: date
    start_time: time
    end_time: time
    batch_id: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_session(
    payload: SessionCreate,
    current_user: User = Depends(require_roles("trainer")),
    db: Session = Depends(get_db),
):
    """Trainer creates a session for a batch they are assigned to."""
    # Verify trainer is assigned to the batch
    assignment = db.query(BatchTrainer).filter(
        BatchTrainer.batch_id == payload.batch_id,
        BatchTrainer.trainer_id == current_user.id,
    ).first()
    if not assignment:
        raise HTTPException(403, "You are not assigned to this batch")

    if payload.end_time <= payload.start_time:
        raise HTTPException(422, "end_time must be after start_time")

    session = SessionModel(
        batch_id=payload.batch_id,
        trainer_id=current_user.id,
        title=payload.title,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "date": str(session.date),
        "start_time": str(session.start_time),
        "end_time": str(session.end_time),
        "batch_id": session.batch_id,
    }


@router.get("/{session_id}/attendance")
def get_session_attendance(
    session_id: int,
    current_user: User = Depends(require_roles("trainer")),
    db: Session = Depends(get_db),
):
    """Trainer retrieves the full attendance list for one of their sessions."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(404, f"Session id={session_id} not found")

    # Trainer must own this session or be assigned to the batch
    if session.trainer_id != current_user.id:
        assignment = db.query(BatchTrainer).filter(
            BatchTrainer.batch_id == session.batch_id,
            BatchTrainer.trainer_id == current_user.id,
        ).first()
        if not assignment:
            raise HTTPException(403, "You are not authorised to view this session's attendance")

    records = (
        db.query(Attendance)
        .filter(Attendance.session_id == session_id)
        .all()
    )

    # Include ALL enrolled students, marking non-responders as absent
    enrolled = db.query(BatchStudent).filter(BatchStudent.batch_id == session.batch_id).all()
    marked_ids = {r.student_id: r for r in records}

    attendance_list = []
    for enr in enrolled:
        rec = marked_ids.get(enr.student_id)
        attendance_list.append({
            "student_id": enr.student_id,
            "status": rec.status if rec else "not_marked",
            "marked_at": rec.marked_at.isoformat() if rec else None,
        })

    return {
        "session_id": session_id,
        "title": session.title,
        "date": str(session.date),
        "attendance": attendance_list,
        "total_enrolled": len(enrolled),
        "marked_count": len(records),
    }
