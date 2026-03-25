import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Float, Integer, Boolean, Text,
    ForeignKey, DateTime, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str]           = mapped_column(String, primary_key=True, default=new_uuid)
    email: Mapped[str]        = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str]         = mapped_column(SAEnum("patient", "doctor", "admin", name="role_enum"), nullable=False)
    name: Mapped[str]         = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool]   = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    doctor_profile:  Mapped[Optional["DoctorProfile"]]  = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    patient_profile: Mapped[Optional["PatientProfile"]] = relationship(back_populates="user", foreign_keys="PatientProfile.user_id", uselist=False, cascade="all, delete-orphan")
    sensor_readings: Mapped[list["SensorReading"]]      = relationship(back_populates="patient", cascade="all, delete-orphan")
    alerts_received: Mapped[list["Alert"]]              = relationship(back_populates="patient", foreign_keys="Alert.patient_id", cascade="all, delete-orphan")


# ── Doctor profile ─────────────────────────────────────────────────────────────
class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[str]           = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    specialty: Mapped[Optional[str]] = mapped_column(String)
    hospital: Mapped[Optional[str]]  = mapped_column(String)
    license_num: Mapped[Optional[str]] = mapped_column(String)
    verified: Mapped[bool]           = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="doctor_profile")


# ── Patient profile ────────────────────────────────────────────────────────────
class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    user_id: Mapped[str]                = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dob: Mapped[Optional[str]]          = mapped_column(String)
    diabetes_type: Mapped[Optional[str]] = mapped_column(SAEnum("type1", "type2", "gestational", "other", name="diabetes_enum"))
    diagnosis_year: Mapped[Optional[int]] = mapped_column(Integer)
    doctor_id: Mapped[Optional[str]]    = mapped_column(String, ForeignKey("users.id"), index=True)
    device_id: Mapped[Optional[str]]    = mapped_column(String, unique=True)
    device_paired: Mapped[bool]         = mapped_column(Boolean, default=False)

    user:   Mapped["User"] = relationship(back_populates="patient_profile", foreign_keys=[user_id])
    doctor: Mapped[Optional["User"]] = relationship(foreign_keys=[doctor_id])


# ── Sensor readings ────────────────────────────────────────────────────────────
class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str]            = mapped_column(String, primary_key=True, default=new_uuid)
    patient_id: Mapped[str]    = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str]     = mapped_column(String, nullable=False)
    foot_side: Mapped[str]     = mapped_column(SAEnum("left", "right", name="foot_enum"), default="left")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    # Temperature readings (°C)
    temp_heel:  Mapped[Optional[float]] = mapped_column(Float)
    temp_arch:  Mapped[Optional[float]] = mapped_column(Float)
    temp_ball:  Mapped[Optional[float]] = mapped_column(Float)
    temp_toes:  Mapped[Optional[float]] = mapped_column(Float)
    temp_avg:   Mapped[Optional[float]] = mapped_column(Float)
    temp_max:   Mapped[Optional[float]] = mapped_column(Float)

    # Pressure readings (% of max safe)
    press_heel: Mapped[Optional[float]] = mapped_column(Float)
    press_arch: Mapped[Optional[float]] = mapped_column(Float)
    press_ball: Mapped[Optional[float]] = mapped_column(Float)
    press_toes: Mapped[Optional[float]] = mapped_column(Float)
    press_max:  Mapped[Optional[float]] = mapped_column(Float)

    # Derived
    risk_score:  Mapped[float]   = mapped_column(Float, default=0.0)
    step_count:  Mapped[int]     = mapped_column(Integer, default=0)
    battery_pct: Mapped[int]     = mapped_column(Integer, default=100)

    patient: Mapped["User"] = relationship(back_populates="sensor_readings")
    alerts:  Mapped[list["Alert"]] = relationship(back_populates="reading")


# ── Alerts ─────────────────────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str]            = mapped_column(String, primary_key=True, default=new_uuid)
    patient_id: Mapped[str]    = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[Optional[str]]  = mapped_column(String, ForeignKey("users.id"), index=True)
    reading_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("sensor_readings.id"))

    type: Mapped[str]     = mapped_column(SAEnum("temperature", "pressure", "critical", "info", name="alert_type_enum"))
    severity: Mapped[str] = mapped_column(SAEnum("low", "medium", "high", "critical", name="severity_enum"))
    message: Mapped[str]  = mapped_column(String, nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)

    resolved: Mapped[bool]            = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notified_email: Mapped[bool]      = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    patient: Mapped["User"]                    = relationship(foreign_keys=[patient_id])
    reading: Mapped[Optional["SensorReading"]] = relationship(back_populates="alerts")


# ── Preorders ──────────────────────────────────────────────────────────────────
class Preorder(Base):
    __tablename__ = "preorders"

    id: Mapped[str]           = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str]         = mapped_column(String, nullable=False)
    email: Mapped[str]        = mapped_column(String, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String)
    address: Mapped[Optional[str]] = mapped_column(String)
    city: Mapped[Optional[str]]    = mapped_column(String)
    country: Mapped[str]           = mapped_column(String, default="US")
    plan: Mapped[str]         = mapped_column(SAEnum("patient", "clinical", "enterprise", name="plan_enum"))
    quantity: Mapped[int]     = mapped_column(Integer, default=1)
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str]       = mapped_column(
        SAEnum("pending", "confirmed", "shipped", "cancelled", name="order_status_enum"),
        default="pending"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


# ── Demo requests ──────────────────────────────────────────────────────────────
class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id: Mapped[str]               = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str]             = mapped_column(String, nullable=False)
    email: Mapped[str]            = mapped_column(String, nullable=False)
    organization: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[Optional[str]]   = mapped_column(String)
    phone: Mapped[Optional[str]]  = mapped_column(String)
    message: Mapped[Optional[str]] = mapped_column(Text)
    contacted: Mapped[bool]       = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=now_utc)
