from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, DoctorProfile, PatientProfile
from app.middleware.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str                          # "patient" | "doctor"
    phone: Optional[str] = None
    # Doctor fields
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    # Patient fields
    diabetes_type: Optional[str] = None

    @field_validator("password")
    @classmethod
    def pw_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in ("patient", "doctor"):
            raise ValueError("role must be 'patient' or 'doctor'")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: dict


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role=body.role,
        name=body.name,
        phone=body.phone,
    )
    db.add(user)
    await db.flush()  # generate user.id

    if body.role == "doctor":
        db.add(DoctorProfile(user_id=user.id, specialty=body.specialty, hospital=body.hospital))
    else:
        db.add(PatientProfile(user_id=user.id, diabetes_type=body.diabetes_type))

    await db.commit()

    token = create_access_token(
        {"sub": user.id, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": user.id, "role": user.role})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile: dict = {}
    if current_user.role == "doctor":
        dp = await db.get(DoctorProfile, current_user.id)
        if dp:
            profile = {"specialty": dp.specialty, "hospital": dp.hospital, "verified": dp.verified}
    elif current_user.role == "patient":
        pp_res = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        pp = pp_res.scalar_one_or_none()
        if pp:
            profile = {
                "diabetes_type": pp.diabetes_type,
                "doctor_id": pp.doctor_id,
                "device_paired": pp.device_paired,
                "device_id": pp.device_id,
            }
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "profile": profile,
    }
