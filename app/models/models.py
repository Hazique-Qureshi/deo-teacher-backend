# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    father_name = Column(String(100), nullable=True)
    husband_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    cnic = Column(String(100), unique=True, nullable=False, index=True)
    personal_number = Column(String(100), nullable=True)
    school_name = Column(String(150), nullable=True)
    semis_code = Column(String(50), nullable=True)
    taluka = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    union_council = Column(String(100), nullable=True)
    domicile_taluka = Column(String(100), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    date_of_joining_school = Column(String(20), nullable=True)
    current_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)
    contact_number = Column(String(100), nullable=True)
    father_number = Column(String(100), nullable=True)
    husband_number = Column(String(100), nullable=True)
    iba_seat_number = Column(String(50), nullable=True)
    drc_number = Column(String(50), nullable=True)
    iba_first_merit_number = Column(String(50), nullable=True)
    iba_obtained_marks = Column(String(20), nullable=True)
    designation = Column(String(100), nullable=True)
    bps = Column(String(20), nullable=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    phone = Column(String(100), nullable=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="teacher")
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    documents = relationship("TeacherDocument", backref="user", lazy=True, cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", backref="user", lazy=True, cascade="all, delete-orphan")

class TeacherDocument(Base):
    __tablename__ = "teacher_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    document_type = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
