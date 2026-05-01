"""
Institution endpoints.

GET /institutions/{id}/summary – Programme Manager: summary across all batches in an institution
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.dependencies import require_roles
from src.db.database import get_db
from src.models.user import User
from src.models.attendance import Batch, SessionModel, Attendance

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("/{institution_id}/summary")
def institution_summary(
    institution_id: int,
    current_user: User = Depends(require_roles("programme_manager")),
    db: Session = Depends(get_db),
):
    """Aggregate attendance across all batches under an institution."""
    institution = db.query(User).filter(
        User.id == institution_id, User.role == "institution"
    ).first()
    if not institution:
        raise HTTPException(404, f"Institution id={institution_id} not found")

    batches = db.query(Batch).filter(Batch.institution_id == institution_id).all()
    batch_summaries = []
    grand_total = grand_present = grand_absent = grand_late = 0

    for batch in batches:
        sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch.id).all()
        b_total = b_present = b_absent = b_late = 0
        for sess in sessions:
            records = db.query(Attendance).filter(Attendance.session_id == sess.id).all()
            b_total += len(records)
            b_present += sum(1 for r in records if r.status == "present")
            b_absent += sum(1 for r in records if r.status == "absent")
            b_late += sum(1 for r in records if r.status == "late")
        grand_total += b_total
        grand_present += b_present
        grand_absent += b_absent
        grand_late += b_late
        batch_summaries.append({
            "batch_id": batch.id,
            "batch_name": batch.name,
            "session_count": len(sessions),
            "total_records": b_total,
            "present": b_present,
            "absent": b_absent,
            "late": b_late,
        })

    return {
        "institution_id": institution_id,
        "institution_name": institution.name,
        "batches": batch_summaries,
        "overall": {
            "total_records": grand_total,
            "present": grand_present,
            "absent": grand_absent,
            "late": grand_late,
        },
    }
