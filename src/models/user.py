"""ORM model for the users table."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Roles: student | trainer | institution | programme_manager | monitoring_officer
    role = Column(String, nullable=False)
    institution_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    sessions_created = relationship(
        "SessionModel", back_populates="trainer", foreign_keys="SessionModel.trainer_id"
    )
    attendance_records = relationship("Attendance", back_populates="student")
    invites_created = relationship("BatchInvite", back_populates="creator")
