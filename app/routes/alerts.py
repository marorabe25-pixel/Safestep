from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Alert, User, PatientProfile
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    unresolved: bool = Query(False),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "patient":
        q = select(Alert).where(Alert.patient_id == current_user.id)
    elif current_user.role == "doctor":
        # Get all patient IDs under this doctor
        pp_res = await db.execute(
            select(PatientProfile.user_id).where(PatientProfile.doctor_id == current_user.id)
        )
        patient_ids = [r for r in pp_res.scalars().all()]
        if not patient_ids:
            return []
        q = select(Alert).where(Alert.patient_id.in_(patient_ids))
    else:
        q = select(Alert)  # admin sees all

    if unresolved:
        q = q.where(Alert.resolved == False)

    q = q.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(q)
    alerts = result.scalars().all()
    return [_alert_dict(a) for a in alerts]


@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Permission check
    if current_user.role == "patient" and alert.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if current_user.role == "doctor" and alert.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return _alert_dict(alert)


def _alert_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "doctor_id": a.doctor_id,
        "type": a.type,
        "severity": a.severity,
        "message": a.message,
        "detail": a.detail,
        "resolved": a.resolved,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "notified_email": a.notified_email,
        "created_at": a.created_at.isoformat(),
    }
