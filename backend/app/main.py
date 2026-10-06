"""FastAPI entrypoint for the HR Chat Agent."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.agent.graph import run_hr_agent
from backend.app.agent.llm import resolve_llm_provider
from backend.app.agent.tools import set_current_employee
from backend.app.auth.security import authenticate_employee, create_access_token, decode_access_token
from backend.app.config import get_settings
from backend.app.db.models import Base, Employee, get_engine, get_session_factory
from backend.app.db.seed import seed
from backend.app.schemas import ChatRequest, ChatResponse, HealthResponse, LoginRequest, TokenResponse

security = HTTPBearer()
app = FastAPI(
    title="HR Chat Agent API",
    description="Authenticated Agentic AI HR assistant with policy RAG and leave tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_employee(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Employee:
    payload = decode_access_token(credentials.credentials)
    if not payload or "employee_id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    emp = db.query(Employee).filter(Employee.employee_id == payload["employee_id"], Employee.is_active.is_(True)).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found")
    return emp


@app.on_event("startup")
def on_startup() -> None:
    settings = get_settings()
    Path(settings.policies_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(engine)
    # Auto-seed if empty
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        if session.query(Employee).count() == 0:
            seed(force=False)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="hr-chat-agent", llm_provider=resolve_llm_provider())


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    employee = authenticate_employee(db, body.email, body.password)
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email, employee ID, or password")
    token = create_access_token(
        {
            "sub": employee.email,
            "employee_id": employee.employee_id,
            "full_name": employee.full_name,
        }
    )
    return TokenResponse(
        access_token=token,
        employee_id=employee.employee_id,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        employment_type=employee.employment_type,
    )


@app.get("/me")
def me(employee: Employee = Depends(get_current_employee)) -> dict:
    return {
        "employee_id": employee.employee_id,
        "full_name": employee.full_name,
        "email": employee.email,
        "department": employee.department,
        "role_title": employee.role_title,
        "employment_type": employee.employment_type,
        "join_date": employee.join_date.isoformat(),
        "manager_email": employee.manager_email,
        "location": employee.location,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, employee: Employee = Depends(get_current_employee)) -> ChatResponse:
    set_current_employee(employee.employee_id)
    try:
        history = [{"role": m.role, "content": m.content} for m in body.history[-12:]]
        result = run_hr_agent(body.message, history=history)
    except Exception as exc:  # noqa: BLE001 - surface agent errors cleanly to clients
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    finally:
        set_current_employee(None)

    return ChatResponse(
        answer=result["answer"],
        employee_id=employee.employee_id,
        tool_trace=result.get("tool_trace", []),
    )


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
