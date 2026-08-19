from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import get_settings
from app.db.session import engine
from app.models.models import Base
from app.routers import auth, teachers, admin
import os

settings = get_settings()

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# Request Size Limit Middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return Response("Request too large", status_code=413)
        return await call_next(request)

port = int(os.getenv("PORT", 8000))

try:
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal
    from app.models.models import User
    from app.core.security import get_password_hash
    from app.core.encryption import encrypt_value
    from sqlalchemy import text
    db_seed = SessionLocal()
    try:
        db_seed.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;"))
        db_seed.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;"))
        db_seed.commit()
    except Exception as col_err:
        print(f"Column migration note: {col_err}")

    try:
        admin_user = db_seed.query(User).filter(User.role == "admin").first()
        if not admin_user:
            admin_user = User(
                id="00000000-0000-0000-0000-000000000000",
                full_name="System Administrator",
                cnic="0000000000000",
                email="admin@deo.gov.pk",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db_seed.add(admin_user)
        else:
            admin_user.password_hash = get_password_hash("admin123")
            admin_user.failed_login_attempts = 0
            admin_user.locked_until = None
            admin_user.cnic = "0000000000000"
            admin_user.is_active = True
        db_seed.commit()
        print("Default admin user auto-seeded/reset successfully.")
    except Exception as seed_err:
        print(f"Admin seed note: {seed_err}")
    finally:
        db_seed.close()
except Exception as exc:
    print(f"Warning: database tables not auto-created on startup: {exc}")

app = FastAPI(title="DEO Office Teacher Management API", version="1.0.0")

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# CORS
frontend_url = settings.FRONTEND_URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

@app.get("/health")
def health():
    return {"status": "ok"}

if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(teachers.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
