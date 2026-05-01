"""
Batch endpoints.

POST /batches                  – Trainer / Institution: create batch
POST /batches/{id}/invite      – Trainer: generate invite token
POST /batches/join             – Student: join via invite token
GET  /batches/{id}/summary     – Institution: attendance summary for a batch
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.dependencies import get_current_user, require_roles
from src.db.database import get_db
from src.models.user import User
from src.models.attendance import (
    Batch, BatchTrainer, BatchStudent, BatchInvite, Attendance, SessionModel,
)

router = APIRouter(prefix="/batches", tags=["Batches"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    name: str
    institution_id: int


class InviteResponse(BaseModel):
    token: str
    expires_at: datetime
    batch_id: int


class JoinRequest(BaseModel):
    token: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_batch(
    payload: BatchCreate,
    current_user: User = Depends(require_roles("trainer", "institution")),
    db: Session = Depends(get_db),
):
    """Create a new batch and, if created by a trainer, auto-assign them to it."""
    # Validate institution exists
    inst = db.query(User).filter(
        User.id == payload.institution_id, User.role == "institution"
    ).first()
    if not inst:
        raise HTTPException(404, f"Institution id={payload.institution_id} not found")

    batch = Batch(name=payload.name, institution_id=payload.institution_id)
    db.add(batch)
    db.flush()  # get batch.id before commit

    # Auto-assign trainer who created the batch
    if current_user.role == "trainer":
        db.add(BatchTrainer(batch_id=batch.id, trainer_id=current_user.id))

    db.commit()
    db.refresh(batch)
    return {"id": batch.id, "name": batch.name, "institution_id": batch.institution_id}


@router.post("/{batch_id}/invite", response_model=InviteResponse)
def create_invite(
    batch_id: int,
    current_user: User = Depends(require_roles("trainer")),
    db: Session = Depends(get_db),
):
    """Generate a single-use invite token for a batch (trainer only)."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch id={batch_id} not found")

    # Ensure this trainer belongs to the batch
    assignment = db.query(BatchTrainer).filter(
        BatchTrainer.batch_id == batch_id,
        BatchTrainer.trainer_id == current_user.id,
    ).first()
    if not assignment:
        raise HTTPException(403, "You are not assigned to this batch")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invite = BatchInvite(
        batch_id=batch_id,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
        used=False,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return InviteResponse(token=invite.token, expires_at=invite.expires_at, batch_id=batch_id)


@router.post("/join", status_code=200)
def join_batch(
    payload: JoinRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """Student uses an invite token to enrol in a batch."""
    invite = db.query(BatchInvite).filter(BatchInvite.token == payload.token).first()
    if not invite:
        raise HTTPException(404, "Invite token not found")
    if invite.used:
        raise HTTPException(422, "This invite token has already been used")
    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(422, "This invite token has expired")

    # Check not already enrolled
    existing = db.query(BatchStudent).filter(
        BatchStudent.batch_id == invite.batch_id,
        BatchStudent.student_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(422, "You are already enrolled in this batch")

    db.add(BatchStudent(batch_id=invite.batch_id, student_id=current_user.id))
    invite.used = True
    db.commit()
    return {"message": "Successfully joined batch", "batch_id": invite.batch_id}


@router.get("/{batch_id}/summary")
def batch_summary(
    batch_id: int,
    current_user: User = Depends(require_roles("institution", "programme_manager")),
    db: Session = Depends(get_db),
):
    """
    Institution: attendance summary for all sessions in a batch.
    Returns per-session breakdown and overall stats.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, f"Batch id={batch_id} not found")

    # Institution can only view their own batches
    if current_user.role == "institution" and batch.institution_id != current_user.id:
        raise HTTPException(403, "This batch does not belong to your institution")

    sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch_id).all()
    result = []
    total_records = present = absent = late = 0

    for sess in sessions:
        records = db.query(Attendance).filter(Attendance.session_id == sess.id).all()
        s_present = sum(1 for r in records if r.status == "present")
        s_absent = sum(1 for r in records if r.status == "absent")
        s_late = sum(1 for r in records if r.status == "late")
        total_records += len(records)
        present += s_present
        absent += s_absent
        late += s_late
        result.append({
            "session_id": sess.id,
            "title": sess.title,
            "date": str(sess.date),
            "total": len(records),
            "present": s_present,
            "absent": s_absent,
            "late": s_late,
        })

    return {
        "batch_id": batch_id,
        "batch_name": batch.name,
        "sessions": result,
        "overall": {
            "total_records": total_records,
            "present": present,
            "absent": absent,
            "late": late,
        },
    }
