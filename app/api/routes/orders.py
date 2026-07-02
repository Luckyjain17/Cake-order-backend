from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
import random, string

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.order import Order, ManualOrder
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderOut, PaginatedOrders,
    ManualOrderCreate, ManualOrderUpdate, ManualOrderOut, PaginatedManualOrders,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def _gen_order_number(prefix: str = "CK") -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"{prefix}{suffix}"


# ─── Website Orders (public) ─────────────────────────────────────────────────

@router.post("/", response_model=OrderOut)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    order = Order(
        **data.model_dump(),
        order_number=_gen_order_number("WB"),
    )
    db.add(order)
    await db.flush()
    return OrderOut.model_validate(order)


# ─── Admin: Website Orders ────────────────────────────────────────────────────
# NOTE: /admin/all MUST come before /{order_number} to avoid wildcard capture

@router.get("/admin/all", response_model=PaginatedOrders)
async def admin_list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    if payment_status:
        q = q.where(Order.payment_status == payment_status)
    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar() or 0
    q = q.order_by(Order.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    orders = result.scalars().all()
    return PaginatedOrders(
        items=[OrderOut.model_validate(o) for o in orders],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.patch("/admin/{order_id}", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    return OrderOut.model_validate(order)


# ─── Admin: Manual Orders ─────────────────────────────────────────────────────
# NOTE: /manual, /manual/all MUST come before /{order_number} to avoid wildcard capture

@router.post("/manual", response_model=ManualOrderOut)
async def create_manual_order(
    data: ManualOrderCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    order = ManualOrder(
        **data.model_dump(),
        order_number=_gen_order_number("MN"),
    )
    db.add(order)
    await db.flush()
    return ManualOrderOut.model_validate(order)


@router.get("/manual/all", response_model=PaginatedManualOrders)
async def list_manual_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    order_source: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = select(ManualOrder)
    if status:
        q = q.where(ManualOrder.status == status)
    if order_source:
        q = q.where(ManualOrder.order_source == order_source)
    if start_date:
        q = q.where(func.to_char(ManualOrder.created_at, 'YYYY-MM-DD') >= start_date)
    if end_date:
        q = q.where(func.to_char(ManualOrder.created_at, 'YYYY-MM-DD') <= end_date)
    if search:
        q = q.where(or_(
            ManualOrder.customer_name.ilike(f"%{search}%"),
            ManualOrder.mobile_number.ilike(f"%{search}%"),
            ManualOrder.cake_name.ilike(f"%{search}%"),
            ManualOrder.order_number.ilike(f"%{search}%"),
        ))
    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar() or 0
    q = q.order_by(ManualOrder.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    orders = result.scalars().all()
    return PaginatedManualOrders(
        items=[ManualOrderOut.model_validate(o) for o in orders],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/manual/{order_id}", response_model=ManualOrderOut)
async def get_manual_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(ManualOrder).where(ManualOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Manual order not found")
    return ManualOrderOut.model_validate(order)


@router.put("/manual/{order_id}", response_model=ManualOrderOut)
async def update_manual_order(
    order_id: int,
    data: ManualOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(ManualOrder).where(ManualOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Manual order not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    return ManualOrderOut.model_validate(order)


@router.delete("/manual/{order_id}")
async def delete_manual_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(ManualOrder).where(ManualOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Manual order not found")
    await db.delete(order)
    return {"message": "Manual order deleted"}


# ─── Public: Lookup by order number (wildcard — MUST be last) ─────────────────

@router.get("/{order_number}", response_model=OrderOut)
async def get_order(order_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.order_number == order_number))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderOut.model_validate(order)
