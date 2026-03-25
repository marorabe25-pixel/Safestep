from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import SensorReading, PatientProfile, User
from app.middleware.auth import get_current_user, require_role
from app.services.alert_service import evaluate_reading

router = APIRouter(prefix="/sensors", tags=["sensors"])


# ── Schemas ────────────────────────────────────────────────────────────────────
class ReadingIn(BaseModel):
    device_id: str
    foot_side: str = "left"
    # Temperature zones (°C)
    temp_heel: Optional[float] = None
    temp_arch: Optional[float] = None
    temp_ball: Optional[float] = None
    temp_toes: Optional[float] = None
    # Pressure zones (% of max safe)
    press_heel: Optional[float] = None
    press_arch: Optional[float] = None
    press_ball: Optional[float] = None
    press_toes: Optional[float] = None
    step_count:  int = 0
    battery_pct: int = 100


def _avg(vals):
    v = [x for x in vals if x is not None]
    return round(sum(v) / len(v), 2) if v else None


def _max(vals):
    v = [x for x in vals if x is not None]
    return max(v) if v else None


def _risk_score(temp_max: Optional[float], press_max: Optional[float]) -> float:
    t_risk = max(0.0, min(100.0, (temp_max - 33.0) * 25)) if temp_max and temp_max > 33 else 0.0
    p_risk = max(0.0, min(100.0, (press_max - 70.0) * 2))  if press_max and press_max > 70 else 0.0
    return round(t_risk * 0.6 + p_risk * 0.4, 1)


# ── POST /api/sensors/reading ─────────────────────────────────────────────────
@router.post("/reading", status_code=201)
async def post_reading(
    body: ReadingIn,
    current_user: User = Depends(require_role("patient", "admin")),
    db: AsyncSession = Depends(get_db),
):
    # Verify / auto-pair device
    pp_res = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    pp = pp_res.scalar_one_or_none()
    if not pp:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    if not pp.device_paired or not pp.device_id:
        pp.device_id = body.device_id
        pp.device_paired = True
    elif pp.device_id != body.device_id:
        raise HTTPException(status_code=403, detail="Device not associated with this account")

    temps  = [body.temp_heel,  body.temp_arch,  body.temp_ball,  body.temp_toes]
    presses = [body.press_heel, body.press_arch, body.press_ball, body.press_toes]
    temp_max  = _max(temps)
    press_max = _max(presses)
    risk      = _risk_score(temp_max, press_max)

    reading = SensorReading(
        patient_id=current_user.id,
        device_id=body.device_id,
        foot_side=body.foot_side,
        temp_heel=body.temp_heel, temp_arch=body.temp_arch,
        temp_ball=body.temp_ball, temp_toes=body.temp_toes,
        temp_avg=_avg(temps),    temp_max=temp_max,
        press_heel=body.press_heel, press_arch=body.press_arch,
        press_ball=body.press_ball, press_toes=body.press_toes,
        press_max=press_max,
        risk_score=risk,
        step_count=body.step_count,
        battery_pct=body.battery_pct,
    )
    db.add(reading)
    await db.flush()

    # Evaluate thresholds → auto-create alerts
    alerts = await evaluate_reading(
        db, reading_id=reading.id,
        patient_id=current_user.id,
        temp_max=temp_max,
        press_max=press_max,
        risk_score=risk,
    )

    await db.commit()
    return {"id": reading.id, "risk_score": risk, "alerts_created": len(alerts)}


# ── GET /api/sensors/latest ───────────────────────────────────────────────────
@router.get("/latest")
async def latest_reading(
    current_user: User = Depends(require_role("patient")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.patient_id == current_user.id)
        .order_by(desc(SensorReading.recorded_at))
        .limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="No readings yet")
    return _reading_dict(r)


# ── GET /api/sensors/history ──────────────────────────────────────────────────
@router.get("/history")
async def reading_history(
    hours: int = 24,
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hours = min(max(hours, 1), 720)
    pid = current_user.id if current_user.role == "patient" else patient_id

    if not pid:
        raise HTTPException(status_code=400, detail="patient_id required for doctor role")

    if current_user.role == "doctor":
        pp_res = await db.execute(
            select(PatientProfile).where(
                PatientProfile.user_id == pid,
                PatientProfile.doctor_id == current_user.id,
            )
        )
        if not pp_res.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Patient not under your care")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.patient_id == pid, SensorReading.recorded_at >= cutoff)
        .order_by(SensorReading.recorded_at.asc())
        .limit(1000)
    )
    return [_reading_dict(r) for r in result.scalars().all()]


# ── GET /api/sensors/patients  (doctor only) ──────────────────────────────────
@router.get("/patients")
async def doctor_patients(
    current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    # Fetch all patients assigned to this doctor
    pp_res = await db.execute(
        select(PatientProfile, User)
        .join(User, User.id == PatientProfile.user_id)
        .where(PatientProfile.doctor_id == current_user.id)
    )
    rows = pp_res.all()

    out = []
    for pp, user in rows:
        # Latest reading
        lr_res = await db.execute(
            select(SensorReading)
            .where(SensorReading.patient_id == user.id)
            .order_by(desc(SensorReading.recorded_at))
            .limit(1)
        )
        lr = lr_res.scalar_one_or_none()

        # Open alerts count
        al_res = await db.execute(
            select(SensorReading.id)  # just count
            .where(SensorReading.patient_id == user.id)
        )

        out.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "diabetes_type": pp.diabetes_type,
            "device_paired": pp.device_paired,
            "last_temp_max":  lr.temp_max  if lr else None,
            "last_press_max": lr.press_max if lr else None,
            "last_risk_score": lr.risk_score if lr else None,
            "last_battery":   lr.battery_pct if lr else None,
            "last_reading_at": lr.recorded_at.isoformat() if lr else None,
        })

    # Sort by risk score descending
    out.sort(key=lambda x: x["last_risk_score"] or 0, reverse=True)
    return out


def _reading_dict(r: SensorReading) -> dict:
    return {
        "id": r.id,
        "recorded_at": r.recorded_at.isoformat(),
        "foot_side": r.foot_side,
        "temp_avg": r.temp_avg, "temp_max": r.temp_max,
        "press_max": r.press_max,
        "risk_score": r.risk_score,
        "step_count": r.step_count,
        "battery_pct": r.battery_pct,
    }
