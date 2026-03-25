"""
Alert service — evaluates sensor thresholds and auto-creates alerts.
Also handles email notifications to patients + their assigned doctors.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Alert, User, PatientProfile
from app.services import email_service

# ── Clinical thresholds ───────────────────────────────────────────────────────
TEMP_WARN     = 35.0   # °C
TEMP_CRITICAL = 36.0
PRESS_WARN    = 85.0   # % of max safe pressure
PRESS_CRITICAL= 95.0
RISK_CRITICAL = 70.0   # combined AI risk score (0–100)


async def evaluate_reading(
    db: AsyncSession,
    reading_id: str,
    patient_id: str,
    temp_max: Optional[float],
    press_max: Optional[float],
    risk_score: float,
) -> list[Alert]:
    """Check thresholds and create alerts. Returns list of new Alert objects."""

    # Fetch patient + their doctor
    patient = await db.get(User, patient_id)
    if not patient:
        return []

    pp_res = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == patient_id)
    )
    pp = pp_res.scalar_one_or_none()
    doctor_id = pp.doctor_id if pp else None
    doctor: Optional[User] = await db.get(User, doctor_id) if doctor_id else None

    created: list[Alert] = []

    # ── Temperature alerts ────────────────────────────────────────────────────
    if temp_max is not None:
        if temp_max >= TEMP_CRITICAL:
            a = await _create_alert(
                db, patient_id=patient_id, doctor_id=doctor_id,
                reading_id=reading_id, alert_type="temperature", severity="critical",
                message=f"Critical foot temperature: {temp_max:.1f}°C",
                detail=(
                    f"Temperature has exceeded {TEMP_CRITICAL}°C. "
                    "Risk of tissue damage — immediate clinical review recommended."
                ),
            )
            created.append(a)
            await _notify(patient, doctor, a, severity="critical")

        elif temp_max >= TEMP_WARN:
            a = await _create_alert(
                db, patient_id=patient_id, doctor_id=doctor_id,
                reading_id=reading_id, alert_type="temperature", severity="high",
                message=f"Elevated foot temperature: {temp_max:.1f}°C",
                detail="Temperature above normal range. Monitor closely for the next 24 hours.",
            )
            created.append(a)
            await _notify(patient, doctor, a, severity="warning")

    # ── Pressure alerts ───────────────────────────────────────────────────────
    if press_max is not None:
        if press_max >= PRESS_CRITICAL:
            a = await _create_alert(
                db, patient_id=patient_id, doctor_id=doctor_id,
                reading_id=reading_id, alert_type="pressure", severity="critical",
                message=f"Dangerous peak pressure: {press_max:.0f}%",
                detail=(
                    "Sustained high pressure detected. Risk of pressure ulcer formation. "
                    "Offloading footwear recommended immediately."
                ),
            )
            created.append(a)
            await _notify(patient, doctor, a, severity="critical")

        elif press_max >= PRESS_WARN:
            a = await _create_alert(
                db, patient_id=patient_id, doctor_id=doctor_id,
                reading_id=reading_id, alert_type="pressure", severity="medium",
                message=f"High pressure point detected: {press_max:.0f}%",
                detail="Pressure above safe threshold. Consider footwear adjustment.",
            )
            created.append(a)

    # ── Combined risk score (only if no other critical alert was already sent) ─
    if risk_score >= RISK_CRITICAL and not any(a.severity == "critical" for a in created):
        a = await _create_alert(
            db, patient_id=patient_id, doctor_id=doctor_id,
            reading_id=reading_id, alert_type="critical", severity="critical",
            message=f"High overall risk score: {risk_score:.0f}/100",
            detail="AI model detected elevated combined risk. Review pressure and temperature trends.",
        )
        created.append(a)
        await _notify(patient, doctor, a, severity="critical")

    # Mark all new alerts as email-notified
    for a in created:
        a.notified_email = True

    return created


async def _create_alert(
    db: AsyncSession,
    *,
    patient_id: str,
    doctor_id: Optional[str],
    reading_id: Optional[str],
    alert_type: str,
    severity: str,
    message: str,
    detail: Optional[str] = None,
) -> Alert:
    alert = Alert(
        patient_id=patient_id,
        doctor_id=doctor_id,
        reading_id=reading_id,
        type=alert_type,
        severity=severity,
        message=message,
        detail=detail,
    )
    db.add(alert)
    await db.flush()  # get the generated id without committing
    return alert


async def _notify(
    patient: User,
    doctor: Optional[User],
    alert: Alert,
    severity: str,
) -> None:
    # Email patient
    await email_service.send_alert_email(
        to=patient.email,
        name=patient.name,
        message=alert.message,
        detail=alert.detail or "",
        severity=severity,
    )
    # Email assigned doctor
    if doctor:
        await email_service.send_alert_email(
            to=doctor.email,
            name=doctor.name,
            message=f"Patient {patient.name}: {alert.message}",
            detail=alert.detail or "",
            severity=severity,
        )
