"""
main.py — THRESHOLD AI Governance Platform — FastAPI application entry point.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn

from app.config import settings
from app.core.logger import app_logger, log_request, log_response
from app.core.exceptions import THRESHOLDBaseException, to_http_exception


# ── Lifespan: startup + shutdown ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("THRESHOLD AI starting up…")
    # ── Init DB tables ────────────────────────────────────────
    try:
        from app.database.init_db import init_db
        await init_db(seed=False)   # set seed=True on first run
        app_logger.info("Database initialised.")
    except Exception as exc:
        app_logger.error("Database init failed", extra={"error": str(exc)})
        raise

    yield

    app_logger.info("THRESHOLD AI shutting down.")


# ── Application factory ───────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI Governance Platform — PS-9.1 Graduated Autonomy Engine",
    docs_url="/api/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/api/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# ── Production Middlewares ─────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging & Security Headers middleware ──────────────
@app.middleware("http")
async def logging_and_security_middleware(request: Request, call_next):
    start    = time.monotonic()
    log_request(request.method, str(request.url.path))
    response = await call_next(request)
    duration = (time.monotonic() - start) * 1000
    log_response(request.method, str(request.url.path), response.status_code, duration)

    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Static asset caching
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400"

    return response

# ── Domain exception handler ──────────────────────────────────
@app.exception_handler(THRESHOLDBaseException)
async def THRESHOLD_exception_handler(request: Request, exc: THRESHOLDBaseException):
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"detail": http_exc.detail},
    )

# ── Global unhandled exception handler ────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "INTERNAL_SERVER_ERROR", "message": "An internal error occurred."}},
    )

# ── Static files ──────────────────────────────────────────────
app.mount(
    "/static",
    StaticFiles(directory=str(settings.STATIC_DIR)),
    name="static",
)

# ── Jinja2 templates ──────────────────────────────────────────
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# ── HTML page routes ──────────────────────────────────────────
@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/api/docs")

@app.get("/",          response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/landing",   response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login",     response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup",    response_class=HTMLResponse, include_in_schema=False)
async def signup_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "mode": "signup"})

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/assistant", response_class=HTMLResponse, include_in_schema=False)
async def assistant_page(request: Request):
    return templates.TemplateResponse("assistant.html", {"request": request})

@app.get("/governance",response_class=HTMLResponse, include_in_schema=False)
async def governance_page(request: Request):
    return templates.TemplateResponse("governance.html", {"request": request})

@app.get("/review",    response_class=HTMLResponse, include_in_schema=False)
async def review_page(request: Request):
    return templates.TemplateResponse("review.html", {"request": request})

@app.get("/audit",     response_class=HTMLResponse, include_in_schema=False)
async def audit_page(request: Request):
    return templates.TemplateResponse("audit_logs.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
async def analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/settings",  response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/profile",   response_class=HTMLResponse, include_in_schema=False)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/logout", include_in_schema=False)
async def logout():
    response = HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Logging Out — THRESHOLD AI</title>
  <script>
    try {
      localStorage.removeItem('THRESHOLD_token');
      sessionStorage.removeItem('THRESHOLD_token');
    } catch (e) {}
    window.location.replace('/');
  </script>
</head>
<body style="background:#0F172A;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
  <p>Logging out…</p>
</body>
</html>""")
    response.delete_cookie("THRESHOLD_token")
    return response

# ── Auth routes ───────────────────────────────────────────────
from typing import Optional
import random
from fastapi import Depends, Header
from app.repositories.employee_repository import EmployeeRepository
from app.core.security import verify_password, hash_password, create_access_token
from app.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    full_name: str
    username: str
    email: str
    password: str
    department: Optional[str] = "Engineering"
    role: Optional[str] = "reviewer"

@app.post("/api/v1/auth/login", tags=["Auth"], summary="Login with username + password")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = EmployeeRepository(db)
    employee = await repo.get_by_username(payload.username)
    if employee is None or not verify_password(payload.password, employee.hashed_password):
        return JSONResponse(status_code=401, content={"detail": {"code": "AUTH_ERROR", "message": "Invalid credentials"}})
    if not employee.is_active:
        return JSONResponse(status_code=403, content={"detail": {"code": "AUTHZ_ERROR", "message": "Account is disabled"}})
    await repo.update_last_login(employee.employee_id)
    token = create_access_token(
        subject=employee.username,
        extra={"role": employee.role, "dept": employee.department, "name": employee.full_name},
    )
    return {"access_token": token, "token_type": "bearer", "user": {"name": employee.full_name, "role": employee.role}}

@app.post("/api/v1/auth/signup", tags=["Auth"], summary="Sign up a new employee user")
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    repo = EmployeeRepository(db)

    uname = payload.username.strip()
    email_clean = payload.email.strip().lower()

    if await repo.get_by_username(uname):
        return JSONResponse(status_code=400, content={"detail": {"code": "DUPLICATE_USERNAME", "message": "Username is already taken"}})
    if await repo.get_by_email(email_clean):
        return JSONResponse(status_code=400, content={"detail": {"code": "DUPLICATE_EMAIL", "message": "Email address is already registered"}})

    # Generate employee_id
    emp_id = f"EMP-{random.randint(1000, 9999)}"
    while await repo.get_by_employee_id(emp_id):
        emp_id = f"EMP-{random.randint(1000, 9999)}"

    hashed_pwd = hash_password(payload.password)
    employee = await repo.create(
        employee_id=emp_id,
        username=uname,
        email=email_clean,
        full_name=payload.full_name.strip(),
        hashed_password=hashed_pwd,
        department=payload.department or "Engineering",
        role=payload.role or "reviewer",
        is_active=True,
        is_admin=(payload.role == "admin"),
    )

    token = create_access_token(
        subject=employee.username,
        extra={"role": employee.role, "dept": employee.department, "name": employee.full_name},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": employee.full_name,
            "role": employee.role,
            "department": employee.department,
            "username": employee.username,
        }
    }

@app.get("/api/v1/auth/me", tags=["Auth"], summary="Get current user profile")
async def get_me(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    from app.dependencies import get_optional_user
    if not authorization:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    from app.core.security import extract_token, decode_access_token
    try:
        token   = extract_token(authorization)
        payload = decode_access_token(token)
        repo    = EmployeeRepository(db)
        emp     = await repo.get_by_username(payload["sub"])
        if not emp:
            return JSONResponse(status_code=404, content={"detail": "User not found"})
        return {
            "name":       emp.full_name,
            "role":       emp.role,
            "department": emp.department,
            "email":      emp.email,
            "username":   emp.username,
        }
    except Exception as e:
        return JSONResponse(status_code=401, content={"detail": str(e)})

# ── API routers ───────────────────────────────────────────────
from app.api.api import api_router
app.include_router(api_router, prefix="/api/v1")

# ── WebSocket routers ─────────────────────────────────────────
from app.websocket.events import router as ws_router
app.include_router(ws_router)

# ── System health ─────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check")
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status":  "ok" if db_status == "healthy" else "degraded",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
    }

# ── Dev runner ────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        ws_ping_interval=20,
        ws_ping_timeout=30,
    )
