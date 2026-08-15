from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
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

@router.get("/dashboard", response_model=DashboardStats)
async def admin_dashboard(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_documents = db.query(TeacherDocument).count()
    recent_uploads = db.query(TeacherDocument).order_by(TeacherDocument.uploaded_at.desc()).limit(10).count()
    
    log = ActivityLog(user_id=admin.id, action="admin_dashboard_access", details="Accessed admin dashboard", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    return DashboardStats(total_teachers=total_teachers, total_documents=total_documents, recent_uploads=recent_uploads)

@router.get("/teachers", response_model=list[UserResponse])
async def list_teachers(
    search: Optional[str] = None,
    district: Optional[str] = None,
    request: Request = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == "teacher")
    if search:
        query = query.filter(User.full_name.ilike(f"%{search}%"))
    if district:
        query = query.filter(User.district.ilike(f"%{district}%"))
    teachers = query.all()
    
    log = ActivityLog(user_id=admin.id, action="admin_list_teachers", details=f"Searched teachers: {search or 'all'}", ip_address=request.client.host if request else None, user_agent=request.headers.get("user-agent") if request else None)
    db.add(log)
    db.commit()
    
    return [UserResponse.from_orm(t) for t in teachers]

@router.get("/teachers/{teacher_id}/documents", response_model=list[DocumentResponse])
async def get_teacher_documents(teacher_id: str, request: Request = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    docs = db.query(TeacherDocument).filter(TeacherDocument.user_id == teacher_id).order_by(TeacherDocument.uploaded_at.desc()).all()
    
    log = ActivityLog(user_id=admin.id, action="admin_view_documents", details=f"Viewed documents for teacher {teacher_id}", ip_address=request.client.host if request else None, user_agent=request.headers.get("user-agent") if request else None)
    db.add(log)
    db.commit()
    
    return [DocumentResponse.from_orm(d) for d in docs]

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
    
    log = ActivityLog(user_id=admin.id, action="admin_update_teacher", details=f"Updated teacher {teacher_id}", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    return {"message": "Teacher updated successfully"}

@router.get("/activity-logs", response_model=list[ActivityLogResponse])
async def get_activity_logs(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50).all()
    
    log = ActivityLog(user_id=admin.id, action="admin_view_logs", details="Viewed activity logs", ip_address=request.client.host, user_agent=request.headers.get("user-agent"))
    db.add(log)
    db.commit()
    
    return [ActivityLogResponse.from_orm(log) for log in logs]
