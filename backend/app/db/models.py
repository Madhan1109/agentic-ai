from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from backend.app.config import get_settings


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(128))
    employment_type: Mapped[str] = mapped_column(String(64))  # full-time, part-time, contractor
    role_title: Mapped[str] = mapped_column(String(128))
    manager_email: Mapped[str] = mapped_column(String(255))
    join_date: Mapped[date] = mapped_column(Date)
    location: Mapped[str] = mapped_column(String(128), default="Remote")
    is_active: Mapped[bool] = mapped_column(default=True)

    leave_balances: Mapped[list["LeaveBalance"]] = relationship(back_populates="employee")
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="employee")


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_pk: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    year: Mapped[int] = mapped_column(Integer)
    leave_type: Mapped[str] = mapped_column(String(32))  # PL, SL, CL
    entitled: Mapped[float] = mapped_column(Float)
    used: Mapped[float] = mapped_column(Float, default=0.0)
    pending: Mapped[float] = mapped_column(Float, default=0.0)
    carried_forward: Mapped[float] = mapped_column(Float, default=0.0)

    employee: Mapped[Employee] = relationship(back_populates="leave_balances")

    @property
    def available(self) -> float:
        return round(self.entitled + self.carried_forward - self.used - self.pending, 2)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_pk: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[Employee] = relationship(back_populates="leave_requests")


def get_engine():
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
