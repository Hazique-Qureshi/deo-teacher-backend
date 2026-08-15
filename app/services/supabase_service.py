import re
import os
import shutil
import io
import uuid
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()

supabase = None
LOCAL_UPLOAD_DIR = Path("uploads")
LOCAL_UPLOAD_DIR.mkdir(exist_ok=True)


def _get_supabase_client():
    global supabase
    if settings.USE_LOCAL_STORAGE:
        return None
    if supabase is not None:
        return supabase
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return supabase
    except Exception as exc:
        print(f"Supabase client initialization skipped: {exc}")
        return None

DOCUMENT_TYPES = {
    "cnic": "CNIC",
    "pay_slip": "Pay Slip",
    "picture": "Picture (Passport Size)",
    "offer_order": "Offer Order",
    "appointment_order": "Appointment Order",
    "medical_fitness": "Medical Fitness Certificate",
    "police_verification": "Police Verification",
    "school_joining": "School Joining",
    "iba_first_merit_list": "IBA First Merit List",
    "iba_admit_card": "IBA Admit Card",
    "iba_fees_challan": "IBA Fees Challan",
    "acceptance_stamp_paper": "Acceptance With Stamp Paper",
    "academic_matric": "Matric Certificate + Marksheet",
    "academic_inter": "Inter Certificate + Marksheet",
    "academic_graduation": "Graduation Degree + Final Transcript",
    "academic_bed": "B.Ed Degree + Final Transcript",
    "academic_med": "M.Ed Degree + Final Transcript",
    "academic_ade": "ADE Degree + Final Transcript",
    "domicile_prc": "Domicile and PRC (Form D)",
    "uc_certificate": "UC Certificate"
}

REQUIRED_PROFILE_FIELDS = [
    "gender", "father_name", "personal_number", "contact_number",
    "school_name", "semis_code", "designation", "bps",
    "district", "taluka", "union_council", "domicile_taluka",
    "date_of_birth", "date_of_joining_school",
    "iba_seat_number", "drc_number", "iba_first_merit_number", "iba_obtained_marks"
]

REQUIRED_DOCUMENT_TYPES = list(DOCUMENT_TYPES.keys())

def validate_pdf_content(file_bytes: bytes) -> bool:
    try:
        header = file_bytes[:8]
        is_pdf_header = header.startswith(b'%PDF-') or header.startswith(b'%EOF')
        if not is_pdf_header:
            return False
        from pypdf import PdfReader
        PdfReader(io.BytesIO(file_bytes))
        return True
    except Exception:
        return False

def generate_safe_filename(user_id: str, document_type: str, original_filename: str) -> str:
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "pdf"
    if ext != "pdf":
        raise ValueError("Only PDF allowed")
    return f"documents/{user_id}/{document_type}_{uuid.uuid4()}.pdf"

def scan_file_for_malware(file_bytes: bytes) -> bool:
    try:
        import clamd
        cd = clamd.ClamNetworkSocket('localhost', 3310)
        result = cd.instream(io.BytesIO(file_bytes))
        return result['stream'][0] == 'OK'
    except Exception as e:
        print(f"Malware scan skipped: {e}")
        return True

def upload_file_to_supabase(file_bytes: bytes, destination_path: str, content_type: str = "application/pdf"):
    if not validate_pdf_content(file_bytes):
        raise ValueError("Invalid file type. Only PDF allowed.")
    
    if not scan_file_for_malware(file_bytes):
        raise ValueError("File rejected: malware detected")
    
    client = _get_supabase_client()
    if client:
        try:
            result = client.storage.from_("teacher-documents").upload(destination_path, file_bytes, {"contentType": content_type})
            if result:
                signed = client.storage.from_("teacher-documents").create_signed_url(destination_path, 3600)
                return signed.get("signedURL")
        except Exception as e:
            print(f"Supabase upload failed, falling back to local storage: {e}")
    
    local_path = LOCAL_UPLOAD_DIR / destination_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(file_bytes)
    return f"/uploads/{destination_path}"


def get_signed_url(path: str, expires_in: int = 3600):
    client = _get_supabase_client()
    if client:
        try:
            signed = client.storage.from_("teacher-documents").create_signed_url(path, expires_in)
            return signed.get("signedURL")
        except Exception:
            return None
    else:
        return f"/uploads/{path}"


def delete_file_from_supabase(path: str):
    client = _get_supabase_client()
    if client:
        try:
            client.storage.from_("teacher-documents").remove([path])
        except Exception:
            pass
    else:
        local_path = LOCAL_UPLOAD_DIR / path
        if local_path.exists():
            local_path.unlink()
    return True
