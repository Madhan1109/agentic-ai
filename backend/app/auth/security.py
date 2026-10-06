from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db.models import Employee

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def authenticate_employee(session: Session, login: str, password: str) -> Employee | None:
    login = (login or "").strip().lower()
    employee = session.query(Employee).filter(Employee.email == login, Employee.is_active.is_(True)).first()
    if not employee:
        employee = (
            session.query(Employee)
            .filter(Employee.employee_id == login.upper(), Employee.is_active.is_(True))
            .first()
        )
    if not employee:
        employee = (
            session.query(Employee)
            .filter(Employee.employee_id == login, Employee.is_active.is_(True))
            .first()
        )
    if not employee or not verify_password(password, employee.password_hash):
        return None
    return employee


def create_access_token(subject: dict[str, Any]) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {**subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
