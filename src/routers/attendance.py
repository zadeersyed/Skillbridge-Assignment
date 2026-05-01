"""
Attendance endpoints.

POST /attendance/mark – Student: marks own attendance for an active session
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.dependencies import require_roles
from src.db.database import get_db
from src.models.user import User
from src.models.attendance import Attendance, SessionModel, BatchStudent

router = APIRouter(prefix="/attendance", tags=["Attendance"])

VALID_STATUSES = {"present", "absent", "late"}


class MarkAttendanceRequest(BaseModel):
    session_id: int
    status: str


@router.post("/mark", status_code=201)
def mark_attendance(
    payload: MarkAttendanceRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """
    Student marks their own attendance for a session.
    Checks:
      - Session exists (404 if not)
      - Student is enrolled in the batch (403 if not)
      - Status is valid (422 if not)
      - Not already marked (422 if duplicate)
    """
    if payload.status not in VALID_STATUSES:
        raise HTTPException(422, f"status must be one of {sorted(VALID_STATUSES)}")

    session = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    if not session:
        raise HTTPException(404, f"Session id={payload.session_id} not found")

    # Verify student is enrolled in the batch the session belongs to
    enrolled = db.query(BatchStudent).filter(
        BatchStudent.batch_id == session.batch_id,
        BatchStudent.student_id == current_user.id,
    ).first()
    if not enrolled:
        raise HTTPException(
            403,
            "You are not enrolled in the batch for this session",
        )

    # Prevent duplicate marking
    existing = db.query(Attendance).filter(
        Attendance.session_id == payload.session_id,
        Attendance.student_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(422, "Attendance already marked for this session")

    record = Attendance(
        session_id=payload.session_id,
        student_id=current_user.id,
        status=payload.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "session_id": record.session_id,
        "student_id": record.student_id,
        "status": record.status,
        "marked_at": record.marked_at.isoformat(),
    }
