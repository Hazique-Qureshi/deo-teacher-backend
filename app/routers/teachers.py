from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import io
import os
import uuid
from app.core.security import get_current_active_user, get_password_hash
from app.core.config import get_settings
from app.core.encryption import encrypt_value, decrypt_value
from app.db.session import get_db
from app.models.models import User, TeacherDocument, ActivityLog
from app.schemas.schemas import DocumentResponse, CompletionResponse
from app.services.supabase_service import upload_file_to_supabase, delete_file_from_supabase, DOCUMENT_TYPES, REQUIRED_PROFILE_FIELDS, REQUIRED_DOCUMENT_TYPES, get_signed_url, validate_pdf_content, generate_safe_filename, scan_file_for_malware
from app.services.pdf_compressor import compress_pdf

settings = get_settings()
router = APIRouter(prefix="/api/teachers", tags=["Teachers"])


@router.get("/me", response_model=dict)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    missing_fields = [f for f in REQUIRED_PROFILE_FIELDS if not getattr(current_user, f)]
    return {
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "father_name": current_user.father_name,
            "husband_name": current_user.husband_name,
            "gender": current_user.gender,
            "cnic": decrypt_value(current_user.cnic),
            "personal_number": decrypt_value(current_user.personal_number) if current_user.personal_number else None,
            "school_name": current_user.school_name,
            "semis_code": current_user.semis_code,
            "taluka": current_user.taluka,
            "district": current_user.district,
            "union_council": current_user.union_council,
            "domicile_taluka": current_user.domicile_taluka,
            "date_of_birth": current_user.date_of_birth,
            "date_of_joining_school": current_user.date_of_joining_school,
            "current_address": current_user.current_address,
            "permanent_address": current_user.permanent_address,
            "contact_number": decrypt_value(current_user.contact_number) if current_user.contact_number else None,
            "father_number": decrypt_value(current_user.father_number) if current_user.father_number else None,
            "husband_number": decrypt_value(current_user.husband_number) if current_user.husband_number else None,
            "iba_seat_number": current_user.iba_seat_number,
            "drc_number": current_user.drc_number,
            "iba_first_merit_number": current_user.iba_first_merit_number,
            "iba_obtained_marks": current_user.iba_obtained_marks,
            "designation": current_user.designation,
            "bps": current_user.bps,
            "email": current_user.email,
            "phone": decrypt_value(current_user.phone) if current_user.phone else None,
            "role": current_user.role,
        },
        "missing_profile_fields": missing_fields
    }

@router.put("/me", response_model=dict)
async def update_profile(
    full_name: Optional[str] = Form(None),
    father_name: Optional[str] = Form(None),
    husband_name: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    personal_number: Optional[str] = Form(None),
    school_name: Optional[str] = Form(None),
    semis_code: Optional[str] = Form(None),
    taluka: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    union_council: Optional[str] = Form(None),
    domicile_taluka: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    date_of_joining_school: Optional[str] = Form(None),
    current_address: Optional[str] = Form(None),
    permanent_address: Optional[str] = Form(None),
    contact_number: Optional[str] = Form(None),
    father_number: Optional[str] = Form(None),
    husband_number: Optional[str] = Form(None),
    iba_seat_number: Optional[str] = Form(None),
    drc_number: Optional[str] = Form(None),
    iba_first_merit_number: Optional[str] = Form(None),
    iba_obtained_marks: Optional[str] = Form(None),
    designation: Optional[str] = Form(None),
    bps: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    update_data = {
        "full_name": full_name or current_user.full_name,
        "father_name": father_name if father_name is not None else current_user.father_name,
        "husband_name": husband_name if husband_name is not None else current_user.husband_name,
        "gender": gender if gender is not None else current_user.gender,
        "personal_number": encrypt_value(personal_number) if personal_number is not None else current_user.personal_number,
        "school_name": school_name if school_name is not None else current_user.school_name,
        "semis_code": semis_code if semis_code is not None else current_user.semis_code,
        "taluka": taluka if taluka is not None else current_user.taluka,
        "district": district if district is not None else current_user.district,
        "union_council": union_council if union_council is not None else current_user.union_council,
        "domicile_taluka": domicile_taluka if domicile_taluka is not None else current_user.domicile_taluka,
        "date_of_birth": date_of_birth if date_of_birth is not None else current_user.date_of_birth,
        "date_of_joining_school": date_of_joining_school if date_of_joining_school is not None else current_user.date_of_joining_school,
        "current_address": current_address if current_address is not None else current_user.current_address,
        "permanent_address": permanent_address if permanent_address is not None else current_user.permanent_address,
        "contact_number": encrypt_value(contact_number) if contact_number is not None else current_user.contact_number,
        "father_number": encrypt_value(father_number) if father_number is not None else current_user.father_number,
        "husband_number": encrypt_value(husband_number) if husband_number is not None else current_user.husband_name,
        "iba_seat_number": iba_seat_number if iba_seat_number is not None else current_user.iba_seat_number,
        "drc_number": drc_number if drc_number is not None else current_user.drc_number,
        "iba_first_merit_number": iba_first_merit_number if iba_first_merit_number is not None else current_user.iba_first_merit_number,
        "iba_obtained_marks": iba_obtained_marks if iba_obtained_marks is not None else current_user.iba_obtained_marks,
        "designation": designation if designation is not None else current_user.designation,
        "bps": bps if bps is not None else current_user.bps,
        "email": email if email is not None else current_user.email,
        "phone": encrypt_value(phone) if phone is not None else current_user.phone,
    }
    
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    log = ActivityLog(user_id=current_user.id, action="profile_update", details="Profile updated")
    db.add(log)
    db.commit()
    
    return {"message": "Profile updated successfully", "user": {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "gender": current_user.gender,
        "cnic": decrypt_value(current_user.cnic),
    }}

@router.post("/upload-document", response_model=DocumentResponse)
async def upload_document(
    document_type: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    file_bytes = file.file.read()
    original_size = len(file_bytes)
    if original_size > settings.UPLOAD_MAX_SIZE:
        raise HTTPException(status_code=400, detail="Please compress your PDF to under 5 MB before uploading.")
    
    if not validate_pdf_content(file_bytes):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF allowed.")
    
    compressed_bytes, compression_status = compress_pdf(file_bytes, max_size_mb=5)
    compressed_size = len(compressed_bytes)
    
    safe_filename = generate_safe_filename(current_user.id, document_type, file.filename)
    path = safe_filename
    public_url = upload_file_to_supabase(compressed_bytes, path)
    if not public_url:
        raise HTTPException(status_code=500, detail="Upload failed")
    
    doc = TeacherDocument(
        user_id=current_user.id,
        document_type=document_type,
        filename=path,
        original_filename=file.filename,
        file_type="PDF",
        file_size=compressed_size,
        description=f"{description or ''} (compressed from {original_size/1024/1024:.1f}MB to {compressed_size/1024/1024:.1f}MB)"
    )
    db.add(doc)
    
    log = ActivityLog(user_id=current_user.id, action="upload", details=f"Uploaded {document_type}")
    db.add(log)
    db.commit()
    db.refresh(doc)
    
    return DocumentResponse.from_orm(doc)

@router.get("/documents", response_model=list[DocumentResponse])
async def get_documents(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    docs = db.query(TeacherDocument).filter(TeacherDocument.user_id == current_user.id).order_by(TeacherDocument.uploaded_at.desc()).all()
    return [DocumentResponse.from_orm(d) for d in docs]

@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    doc = db.query(TeacherDocument).filter(
        TeacherDocument.id == doc_id,
        TeacherDocument.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    signed_url = get_signed_url(doc.filename, expires_in=300)
    if signed_url:
        return {"url": signed_url}
    
    return {"url": f"/uploads/{doc.filename}"}

@router.get("/completion", response_model=CompletionResponse)
async def get_completion(current_user: User = Depends(get_current_active_user)):
    missing_fields = [f for f in REQUIRED_PROFILE_FIELDS if not getattr(current_user, f)]
    uploaded_types = {d.document_type for d in current_user.documents}
    missing_docs = [DOCUMENT_TYPES[t] for t in REQUIRED_DOCUMENT_TYPES if t not in uploaded_types]
    total = len(REQUIRED_PROFILE_FIELDS) + len(REQUIRED_DOCUMENT_TYPES)
    completed = total - len(missing_fields) - len(missing_docs)
    percentage = round((completed / total) * 100) if total else 0
    return CompletionResponse(missing_profile_fields=missing_fields, missing_documents=missing_docs, completion_percentage=percentage)

@router.get("/global-stats")
async def get_global_stats(db: Session = Depends(get_db)):
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    return {"total_teachers": total_teachers}

