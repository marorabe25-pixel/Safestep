from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Preorder, DemoRequest
from app.middleware.auth import require_role
from app.services.email_service import send_preorder_confirmation

router = APIRouter(prefix="/orders", tags=["orders"])

PLAN_PRICES = {
    "patient":    29900,   # $299.00
    "clinical":   79900,   # $799.00
    "enterprise": 0,       # custom / contact us
}


class PreorderIn(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "US"
    plan: str
    quantity: int = 1
    notes: Optional[str] = None


class DemoIn(BaseModel):
    name: str
    email: EmailStr
    organization: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None


# ── POST /api/orders/preorder ─────────────────────────────────────────────────
@router.post("/preorder", status_code=201)
async def create_preorder(body: PreorderIn, db: AsyncSession = Depends(get_db)):
    if body.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose from: {list(PLAN_PRICES)}")

    amount = PLAN_PRICES[body.plan] * body.quantity

    order = Preorder(
        name=body.name,
        email=body.email.lower(),
        phone=body.phone,
        address=body.address,
        city=body.city,
        country=body.country,
        plan=body.plan,
        quantity=body.quantity,
        amount_cents=amount,
        notes=body.notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Send confirmation email (non-blocking on failure)
    await send_preorder_confirmation(
        to=body.email,
        name=body.name,
        plan=body.plan,
        order_id=order.id,
        amount_cents=amount,
    )

    return {
        "id": order.id,
        "order_ref": order.id[:8].upper(),
        "message": "Preorder confirmed! Check your email for details.",
        "amount": f"${amount / 100:.2f}",
        "status": order.status,
    }


# ── POST /api/orders/demo ─────────────────────────────────────────────────────
@router.post("/demo", status_code=201)
async def request_demo(body: DemoIn, db: AsyncSession = Depends(get_db)):
    req = DemoRequest(
        name=body.name,
        email=body.email.lower(),
        organization=body.organization,
        role=body.role,
        phone=body.phone,
        message=body.message,
    )
    db.add(req)
    await db.commit()

    return {"id": req.id, "message": "Thanks! Our clinical team will contact you within 24 hours."}


# ── GET /api/orders  (admin only) ─────────────────────────────────────────────
@router.get("/")
async def list_orders(
    _admin=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Preorder).order_by(Preorder.created_at.desc()).limit(200)
    )
    orders = result.scalars().all()
    return [
        {
            "id": o.id, "name": o.name, "email": o.email,
            "plan": o.plan, "quantity": o.quantity,
            "amount": f"${o.amount_cents / 100:.2f}",
            "status": o.status, "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]
