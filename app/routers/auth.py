import re
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import get_settings
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, validate_password_strength, get_current_active_user
from app.core.encryption import encrypt_value, decrypt_value
from app.db.session import get_db
from app.models.models import User, TeacherDocument, ActivityLog, RefreshToken
from app.schemas.schemas import UserCreate, UserLogin, Token, UserResponse, DocumentResponse, CompletionResponse
from app.services.supabase_service import upload_file_to_supabase, delete_file_from_supabase, DOCUMENT_TYPES, REQUIRED_PROFILE_FIELDS, REQUIRED_DOCUMENT_TYPES
from app.services.pdf_compressor import compress_pdf
from datetime import datetime
import os
import secrets
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)

@router.post("/register")
@limiter.limit("10/hour")
async def register(
    request: Request,
    full_name: str = Form(...),
    father_name: str = Form(None),
    husband_name: str = Form(None),
    gender: str = Form(...),
    cnic: str = Form(...),
    personal_number: str = Form(None),
    school_name: str = Form(None),
    semis_code: str = Form(None),
    taluka: str = Form(None),
    district: str = Form(None),
    union_council: str = Form(None),
    domicile_taluka: str = Form(None),
    date_of_birth: str = Form(None),
    date_of_joining_school: str = Form(None),
    current_address: str = Form(None),
    permanent_address: str = Form(None),
    contact_number: str = Form(None),
    father_number: str = Form(None),
    husband_number: str = Form(None),
    iba_seat_number: str = Form(None),
    drc_number: str = Form(None),
    iba_first_merit_number: str = Form(None),
    iba_obtained_marks: str = Form(None),
    designation: str = Form(None),
    bps: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    password: str = Form(...),
    confirm_password: str = Form(...),
    cnic_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    cnic_clean = re.sub(r'[^0-9]', '', cnic)
    if len(cnic_clean) != 13:
        raise HTTPException(status_code=400, detail="Invalid CNIC. Please enter exactly 13 digits.")
    
    existing = db.query(User).filter(User.cnic == encrypt_value(cnic_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail="CNIC already registered")
    
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    is_strong, message = validate_password_strength(password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=message)
    
    hashed = get_password_hash(password)
    user = User(
        full_name=full_name,
        father_name=father_name,
        husband_name=husband_name,
        gender=gender,
        cnic=encrypt_value(cnic_clean),
        personal_number=encrypt_value(personal_number) if personal_number else None,
        school_name=school_name,
        semis_code=semis_code,
        taluka=taluka,
        district=district,
        union_council=union_council,
        domicile_taluka=domicile_taluka,
        date_of_birth=date_of_birth,
        date_of_joining_school=date_of_joining_school,
        current_address=current_address,
        permanent_address=permanent_address,
        contact_number=encrypt_value(contact_number) if contact_number else None,
        father_number=encrypt_value(father_number) if father_number else None,
        husband_number=encrypt_value(husband_number) if husband_number else None,
        iba_seat_number=iba_seat_number,
        drc_number=drc_number,
        iba_first_merit_number=iba_first_merit_number,
        iba_obtained_marks=iba_obtained_marks,
        designation=designation,
        bps=bps,
        email=email,
        phone=encrypt_value(phone) if phone else None,
        password_hash=hashed
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if cnic_file and cnic_file.filename:
        file_bytes = cnic_file.file.read()
        original_size = len(file_bytes)
        if original_size > settings.UPLOAD_MAX_SIZE:
            raise HTTPException(status_code=400, detail="Please compress your PDF to under 5 MB before uploading.")
        compressed_bytes, compression_status = compress_pdf(file_bytes, max_size_mb=5)
        compressed_size = len(compressed_bytes)
        path = f"cnic/{user.id}_{cnic_clean}_{cnic_file.filename}"
        public_url = upload_file_to_supabase(compressed_bytes, path)
        if public_url:
            doc = TeacherDocument(
                user_id=user.id,
                document_type="cnic",
                filename=path,
                original_filename=cnic_file.filename,
                file_type="PDF",
                file_size=compressed_size,
                description=f"CNIC uploaded during registration (compressed from {original_size/1024/1024:.1f}MB to {compressed_size/1024/1024:.1f}MB)"
            )
            db.add(doc)
            db.commit()
    
    log = ActivityLog(user_id=user.id, action="register", details="Teacher registered", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    access_token = create_access_token({"sub": user.cnic}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token({"sub": user.cnic})
    
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(refresh_token_obj)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: UserLogin, db: Session = Depends(get_db)):
    cnic_clean = re.sub(r'[^0-9]', '', form_data.cnic)
    user = db.query(User).filter((User.cnic == encrypt_value(cnic_clean)) | (User.cnic == cnic_clean)).first()
    
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(status_code=403, detail="Account locked. Try again later.")
    
    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + LOCKOUT_DURATION
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid CNIC or password")
    
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    
    access_token = create_access_token({"sub": user.cnic}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token({"sub": user.cnic})
    
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(refresh_token_obj)
    db.commit()
    
    log = ActivityLog(user_id=user.id, action="login", details="User logged in", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": UserResponse.from_orm(user)}

@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request, refresh_token: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        cnic: str = payload.get("sub")
        token_type: str = payload.get("type")
        if cnic is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    token_obj = db.query(RefreshToken).filter(RefreshToken.token == refresh_token, RefreshToken.revoked == False).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")
    
    user = db.query(User).filter(User.cnic == cnic).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    token_obj.revoked = True
    db.commit()
    
    access_token = create_access_token({"sub": user.cnic}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    new_refresh_token = create_refresh_token({"sub": user.cnic})
    
    new_token_obj = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(new_token_obj)
    db.commit()
    
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer", "user": UserResponse.from_orm(user)}

@router.post("/logout")
async def logout(request: Request, refresh_token: str = Form(...), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    token_obj = db.query(RefreshToken).filter(RefreshToken.token == refresh_token, RefreshToken.user_id == current_user.id).first()
    if token_obj:
        token_obj.revoked = True
        db.commit()
    
    log = ActivityLog(user_id=current_user.id, action="logout", details="User logged out", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    return {"message": "Logged out successfully"}


