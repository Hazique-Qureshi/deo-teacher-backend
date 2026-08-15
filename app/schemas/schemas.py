from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    full_name: str
    father_name: Optional[str] = None
    husband_name: Optional[str] = None
    gender: Optional[str] = None
    cnic: str
    personal_number: Optional[str] = None
    school_name: Optional[str] = None
    semis_code: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    union_council: Optional[str] = None
    domicile_taluka: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_joining_school: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    contact_number: Optional[str] = None
    father_number: Optional[str] = None
    husband_number: Optional[str] = None
    iba_seat_number: Optional[str] = None
    drc_number: Optional[str] = None
    iba_first_merit_number: Optional[str] = None
    iba_obtained_marks: Optional[str] = None
    designation: Optional[str] = None
    bps: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    cnic: str
    password: str

class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class DocumentBase(BaseModel):
    document_type: str
    description: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    user_id: str
    filename: str
    original_filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ActivityLogResponse(BaseModel):
    id: int
    action: str
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_teachers: int
    total_documents: int
    recent_uploads: int

class AdminTeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    father_name: Optional[str] = None
    husband_name: Optional[str] = None
    gender: Optional[str] = None
    personal_number: Optional[str] = None
    school_name: Optional[str] = None
    semis_code: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    union_council: Optional[str] = None
    domicile_taluka: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_joining_school: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    contact_number: Optional[str] = None
    father_number: Optional[str] = None
    husband_number: Optional[str] = None
    iba_seat_number: Optional[str] = None
    drc_number: Optional[str] = None
    iba_first_merit_number: Optional[str] = None
    iba_obtained_marks: Optional[str] = None
    designation: Optional[str] = None
    bps: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class CompletionResponse(BaseModel):
    missing_profile_fields: list[str]
    missing_documents: list[str]
    completion_percentage: int
