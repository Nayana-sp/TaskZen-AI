from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict
# BUG FIX: `datetime | None` is Python 3.10+ syntax. Using Optional[datetime]
# from typing is compatible with Python 3.8+, which is the minimum FastAPI supports.
from typing import Optional
from datetime import datetime
from db import Base


# ─── SQLAlchemy Models ────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    tasks    = relationship("Task", back_populates="owner")


class Task(Base):
    __tablename__ = "tasks"
    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"))
    task_name     = Column(String, index=True)
    description = Column(String, nullable=True)
    date          = Column(String)           # YYYY-MM-DD
    time          = Column(String)           # HH:MM or None
    reminder_time = Column(DateTime, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    priority      = Column(String)           # High | Medium | Low
    status        = Column(String, default="Pending")
    created_at    = Column(DateTime, default=datetime.utcnow)
    completed_at  = Column(DateTime, nullable=True)
    owner         = relationship("User", back_populates="tasks")
    


class VoiceLog(Base):
    __tablename__ = "voice_logs"
    id                 = Column(Integer, primary_key=True, index=True)
    # BUG FIX: VoiceLog had no user_id, so voice commands were stored anonymously
    # with no way to know which user issued them. Added foreign key for audit trail.
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=True)
    command_text       = Column(String)
    extracted_intent   = Column(String)
    extracted_entities = Column(String)   # JSON string


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name:     str
    email:    str
    password: str


class UserResponse(BaseModel):
    id:    int
    name:  str
    email: str
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    task_name: str
    description: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    reminder_time: Optional[datetime] = None   
    priority: str = "Medium"


class TaskResponse(BaseModel):
    id: int
    task_name: str
    description: Optional[str] = None
    date: Optional[str]
    time: Optional[str]
    reminder_time: Optional[datetime]
    priority: str
    status: str
    user_id: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type:   str
