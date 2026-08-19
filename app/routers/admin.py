from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io
from app.core.security import get_current_active_user
from app.core.encryption import decrypt_value
from app.db.session import get_db
from app.models.models import User, TeacherDocument, ActivityLog
from app.schemas.schemas import UserResponse, DocumentResponse, DashboardStats, ActivityLogResponse, AdminTeacherUpdate
from app.services.supabase_service import DOCUMENT_TYPES

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def _serialize_teacher(t: User) -> dict:
    return {
        "full_name": t.full_name or "",
        "father_name": t.father_name or "",
        "husband_name": t.husband_name or "",
        "gender": t.gender or "",
        "cnic": t.cnic or "",
        "personal_number": decrypt_value(t.personal_number) if t.personal_number else "",
        "school_name": t.school_name or "",
        "semis_code": t.semis_code or "",
        "taluka": t.taluka or "",
        "district": t.district or "",
        "union_council": t.union_council or "",
        "domicile_taluka": t.domicile_taluka or "",
        "date_of_birth": str(t.date_of_birth) if t.date_of_birth else "",
        "date_of_joining_school": str(t.date_of_joining_school) if t.date_of_joining_school else "",
        "current_address": t.current_address or "",
        "permanent_address": t.permanent_address or "",
        "contact_number": decrypt_value(t.contact_number) if t.contact_number else "",
        "father_number": decrypt_value(t.father_number) if t.father_number else "",
        "husband_number": decrypt_value(t.husband_number) if t.husband_number else "",
        "iba_seat_number": t.iba_seat_number or "",
        "drc_number": t.drc_number or "",
        "iba_first_merit_number": t.iba_first_merit_number or "",
        "iba_obtained_marks": t.iba_obtained_marks or "",
        "designation": t.designation or "",
        "bps": t.bps or "",
        "email": t.email or "",
        "phone": decrypt_value(t.phone) if t.phone else "",
        "id": str(t.id),
        "role": t.role,
        "is_active": t.is_active,
    }

@router.get("/dashboard", response_model=DashboardStats)
async def admin_dashboard(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_documents = db.query(TeacherDocument).count()
    recent_uploads = db.query(TeacherDocument).order_by(TeacherDocument.uploaded_at.desc()).limit(10).count()

    try:
        log = ActivityLog(user_id=admin.id, action="admin_dashboard_access", details="Accessed admin dashboard", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.add(log); db.commit()
    except Exception: pass

    return DashboardStats(total_teachers=total_teachers, total_documents=total_documents, recent_uploads=recent_uploads)

@router.get("/teachers", response_model=list[UserResponse])
async def list_teachers(
    search: Optional[str] = None,
    cnic: Optional[str] = None,
    district: Optional[str] = None,
    request: Request = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == "teacher")
    if cnic:
        cnic_clean = cnic.replace("-", "").replace(" ", "")
        all_teachers = query.all()
        teachers = [t for t in all_teachers if (t.cnic or "").replace("-", "") == cnic_clean or cnic_clean in (t.cnic or "")]
    else:
        if search:
            query = query.filter(User.full_name.ilike(f"%{search}%"))
        if district:
            query = query.filter(User.district.ilike(f"%{district}%"))
        teachers = query.order_by(User.full_name).all()

    try:
        log = ActivityLog(user_id=admin.id, action="admin_list_teachers", details=f"Searched: name={search}, cnic={cnic}", ip_address=request.client.host if request and request.client else None, user_agent=request.headers.get("user-agent") if request else None)
        db.add(log); db.commit()
    except Exception: pass

    result = []
    for t in teachers:
        try:
            result.append(UserResponse.model_validate(t) if hasattr(UserResponse, "model_validate") else UserResponse.from_orm(t))
        except Exception:
            pass
    return result

@router.get("/teachers/export/csv")
async def export_all_teachers_csv(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    teachers = db.query(User).filter(User.role == "teacher").order_by(User.full_name).all()
    output = io.StringIO()
    fieldnames = ["full_name","father_name","husband_name","gender","cnic","personal_number","school_name","semis_code","taluka","district","union_council","domicile_taluka","date_of_birth","date_of_joining_school","current_address","permanent_address","contact_number","father_number","husband_number","iba_seat_number","drc_number","iba_first_merit_number","iba_obtained_marks","designation","bps","email","phone"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for t in teachers:
        writer.writerow(_serialize_teacher(t))
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=all_teachers.csv"})

@router.get("/teachers/{teacher_id}/export/csv")
async def export_single_teacher_csv(teacher_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")
    output = io.StringIO()
    fieldnames = ["full_name","father_name","husband_name","gender","cnic","personal_number","school_name","semis_code","taluka","district","union_council","domicile_taluka","date_of_birth","date_of_joining_school","current_address","permanent_address","contact_number","father_number","husband_number","iba_seat_number","drc_number","iba_first_merit_number","iba_obtained_marks","designation","bps","email","phone"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerow(_serialize_teacher(t))
    output.seek(0)
    filename = f"teacher_{(t.full_name or 'unknown').replace(' ', '_')}.csv"
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/teachers/{teacher_id}", response_model=UserResponse)
async def get_teacher_detail(teacher_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return UserResponse.model_validate(t) if hasattr(UserResponse, "model_validate") else UserResponse.from_orm(t)

@router.get("/teachers/{teacher_id}/documents", response_model=list[DocumentResponse])
async def get_teacher_documents(teacher_id: str, request: Request = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    docs = db.query(TeacherDocument).filter(TeacherDocument.user_id == teacher_id).order_by(TeacherDocument.uploaded_at.desc()).all()
    try:
        log = ActivityLog(user_id=admin.id, action="admin_view_documents", details=f"Viewed documents for teacher {teacher_id}", ip_address=request.client.host if request and request.client else None, user_agent=request.headers.get("user-agent") if request else None)
        db.add(log); db.commit()
    except Exception: pass
    return [DocumentResponse.model_validate(d) if hasattr(DocumentResponse, "model_validate") else DocumentResponse.from_orm(d) for d in docs]

@router.put("/teachers/{teacher_id}", response_model=dict)
async def update_teacher(request: Request, teacher_id: str, update_data: AdminTeacherUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    data = update_data.model_dump(exclude_none=True)
    sensitive_fields = {"personal_number", "contact_number", "father_number", "husband_number", "phone"}
    for key, value in data.items():
        if key in sensitive_fields and value:
            setattr(teacher, key, encrypt_value(value))
        else:
            setattr(teacher, key, value)

    db.commit()
    db.refresh(teacher)

    try:
        log = ActivityLog(user_id=admin.id, action="admin_update_teacher", details=f"Updated teacher {teacher_id}", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.add(log); db.commit()
    except Exception: pass

    return {"message": "Teacher updated successfully"}

@router.get("/activity-logs", response_model=list[ActivityLogResponse])
async def get_activity_logs(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50).all()
    try:
        log = ActivityLog(user_id=admin.id, action="admin_view_logs", details="Viewed activity logs", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.add(log); db.commit()
    except Exception: pass
    return [ActivityLogResponse.model_validate(l) if hasattr(ActivityLogResponse, "model_validate") else ActivityLogResponse.from_orm(l) for l in logs]
