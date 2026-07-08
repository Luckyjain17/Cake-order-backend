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
    per_page: int = Query(20, ge=1, le=10000),
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    else:
        q = q.where(Order.status.notin_(['ready', 'delivered']))
    if payment_status:
        q = q.where(Order.payment_status == payment_status)
    if start_date:
        q = q.where(func.coalesce(Order.delivery_date, func.to_char(Order.created_at, 'YYYY-MM-DD')) >= start_date)
    if end_date:
        q = q.where(func.coalesce(Order.delivery_date, func.to_char(Order.created_at, 'YYYY-MM-DD')) <= end_date)
    if search:
        q = q.where(or_(
            Order.customer_name.ilike(f"%{search}%"),
            Order.mobile_number.ilike(f"%{search}%"),
            Order.order_number.ilike(f"%{search}%"),
        ))
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


@router.delete("/admin/{order_id}")
async def delete_website_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    return {"message": "Order deleted"}


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


def order_to_manual(o: Order) -> dict:
    cake_name = "Website Order"
    quantity = 1
    weight = "1kg"
    if o.items and isinstance(o.items, list) and len(o.items) > 0:
        names = []
        tot_qty = 0
        w_list = []
        for it in o.items:
            name = it.get("name", "Cake")
            flavor = it.get("flavor")
            if flavor:
                name = f"{name} ({flavor})"
            names.append(f"{name} x{it.get('qty', 1)}")
            tot_qty += it.get('qty', 1)
            if it.get("weight"):
                w_list.append(it.get("weight"))
        cake_name = ", ".join(names)
        quantity = tot_qty
        weight = ", ".join(list(set(w_list))) if w_list else "Standard"

    paid_amt = o.paid_amount or 0
    if paid_amt == 0:
        if o.payment_status == 'paid':
            paid_amt = o.total_amount
        elif o.payment_status == 'half':
            paid_amt = o.total_amount / 2

    return {
        "id": o.id + 1000000,
        "order_number": o.order_number,
        "customer_name": o.customer_name,
        "mobile_number": o.mobile_number,
        "address": (o.delivery_address or "") + (f" (Landmark: {o.landmark})" if o.landmark else ""),
        "cake_name": cake_name,
        "quantity": quantity,
        "weight": weight,
        "amount": o.total_amount,
        "paid_amount": paid_amt,
        "order_source": "website",
        "payment_status": o.payment_status,
        "status": o.status,
        "notes": o.special_instructions or "",
        "delivery_date": o.delivery_date or "",
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


@router.get("/manual/all", response_model=PaginatedManualOrders)
async def list_manual_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=10000),
    status: Optional[str] = None,
    order_source: Optional[str] = None,
    payment_status: Optional[str] = None,
    weight: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    # Query ManualOrder
    q_manual = select(ManualOrder)
    if status:
        q_manual = q_manual.where(ManualOrder.status == status)
    if order_source:
        q_manual = q_manual.where(ManualOrder.order_source == order_source)
    if payment_status:
        q_manual = q_manual.where(ManualOrder.payment_status == payment_status)
    if weight:
        q_manual = q_manual.where(ManualOrder.weight == weight)
    if start_date:
        q_manual = q_manual.where(func.coalesce(ManualOrder.delivery_date, func.to_char(ManualOrder.created_at, 'YYYY-MM-DD')) >= start_date)
    if end_date:
        q_manual = q_manual.where(func.coalesce(ManualOrder.delivery_date, func.to_char(ManualOrder.created_at, 'YYYY-MM-DD')) <= end_date)
    if search:
        q_manual = q_manual.where(or_(
            ManualOrder.customer_name.ilike(f"%{search}%"),
            ManualOrder.mobile_number.ilike(f"%{search}%"),
            ManualOrder.cake_name.ilike(f"%{search}%"),
            ManualOrder.order_number.ilike(f"%{search}%"),
        ))

    # Query website Order ONLY if preparation is Complete (status == 'ready' or status == 'delivered')
    fetch_website = not order_source or order_source == "website"
    orders_web = []
    if fetch_website:
        q_web = select(Order).where(Order.status.in_(['ready', 'delivered']))
        if status:
            q_web = q_web.where(Order.status == status)
        if payment_status:
            q_web = q_web.where(Order.payment_status == payment_status)
        if start_date:
            q_web = q_web.where(func.coalesce(Order.delivery_date, func.to_char(Order.created_at, 'YYYY-MM-DD')) >= start_date)
        if end_date:
            q_web = q_web.where(func.coalesce(Order.delivery_date, func.to_char(Order.created_at, 'YYYY-MM-DD')) <= end_date)
        if search:
            q_web = q_web.where(or_(
                Order.customer_name.ilike(f"%{search}%"),
                Order.mobile_number.ilike(f"%{search}%"),
                Order.order_number.ilike(f"%{search}%"),
            ))

        res_web = await db.execute(q_web)
        orders_web = res_web.scalars().all()

    res_manual = await db.execute(q_manual)
    orders_manual = res_manual.scalars().all()

    # Convert all
    merged_items = []
    for o in orders_manual:
        merged_items.append({
            "id": o.id,
            "order_number": o.order_number,
            "customer_name": o.customer_name,
            "mobile_number": o.mobile_number,
            "address": o.address or "",
            "cake_name": o.cake_name,
            "quantity": o.quantity,
            "weight": o.weight or "1kg",
            "amount": o.amount,
            "paid_amount": o.paid_amount or 0,
            "order_source": o.order_source,
            "payment_status": o.payment_status,
            "status": o.status,
            "notes": o.notes or "",
            "delivery_date": o.delivery_date or "",
            "created_at": o.created_at,
            "updated_at": o.updated_at,
        })

    for o in orders_web:
        converted = order_to_manual(o)
        if weight:
            if weight.lower() not in converted["weight"].lower():
                continue
        merged_items.append(converted)

    # Sort merged list
    merged_items.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(merged_items)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = merged_items[start_idx:end_idx]

    return PaginatedManualOrders(
        items=[ManualOrderOut(**item) for item in paginated_items],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/manual/{order_id}", response_model=ManualOrderOut)
async def get_manual_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    if order_id >= 1000000:
        result = await db.execute(select(Order).where(Order.id == order_id - 1000000))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return ManualOrderOut(**order_to_manual(order))
    else:
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
    try:
        if order_id >= 1000000:
            result = await db.execute(select(Order).where(Order.id == order_id - 1000000))
            order = result.scalar_one_or_none()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            
            # Map manual order updates to website order columns
            update_dict = data.model_dump(exclude_unset=True)
            if "customer_name" in update_dict:
                order.customer_name = update_dict["customer_name"]
            if "mobile_number" in update_dict:
                order.mobile_number = update_dict["mobile_number"]
            if "address" in update_dict:
                order.delivery_address = update_dict["address"]
            if "amount" in update_dict:
                order.total_amount = update_dict["amount"]
            if "notes" in update_dict:
                order.special_instructions = update_dict["notes"]
            if "delivery_date" in update_dict:
                order.delivery_date = update_dict["delivery_date"]
            if "status" in update_dict:
                order.status = update_dict["status"]
            if "payment_status" in update_dict:
                order.payment_status = update_dict["payment_status"]
            if "paid_amount" in update_dict:
                order.paid_amount = update_dict["paid_amount"]
                
            await db.flush()
            return ManualOrderOut(**order_to_manual(order))
        else:
            result = await db.execute(select(ManualOrder).where(ManualOrder.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                raise HTTPException(status_code=404, detail="Manual order not found")
            for k, v in data.model_dump(exclude_unset=True).items():
                setattr(order, k, v)
            return ManualOrderOut.model_validate(order)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")


@router.delete("/manual/{order_id}")
async def delete_manual_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    if order_id >= 1000000:
        result = await db.execute(select(Order).where(Order.id == order_id - 1000000))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        await db.delete(order)
        return {"message": "Order deleted"}
    else:
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
