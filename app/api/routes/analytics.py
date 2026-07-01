from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.order import Order, ManualOrder
from app.models.product import Product
from app.models.category import Category
from app.models.business_data import BusinessData
from app.schemas.analytics import BusinessDataCreate, BusinessDataUpdate, BusinessDataOut, DashboardStats

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def count_orders(model, filter_=None):
        q = select(func.count()).select_from(model)
        if filter_ is not None:
            q = q.where(filter_)
        res = await db.execute(q)
        return res.scalar() or 0

    async def sum_revenue(model, filter_=None):
        q = select(func.coalesce(func.sum(model.total_amount if hasattr(model, 'total_amount') else model.amount), 0))
        if filter_ is not None:
            q = q.where(filter_)
        res = await db.execute(q)
        return float(res.scalar() or 0)

    # Order counts
    today_orders = await count_orders(Order, Order.created_at >= today_start)
    weekly_orders = await count_orders(Order, Order.created_at >= week_start)
    monthly_orders = await count_orders(Order, Order.created_at >= month_start)
    total_orders_web = await count_orders(Order)

    today_manual = await count_orders(ManualOrder, ManualOrder.created_at >= today_start)
    total_manual = await count_orders(ManualOrder)
    total_orders = total_orders_web + total_manual

    # Revenue
    today_revenue = await sum_revenue(Order, Order.created_at >= today_start)
    monthly_revenue_web = await sum_revenue(Order, Order.created_at >= month_start)
    total_revenue_web = await sum_revenue(Order)

    # Business data (offline) revenue aggregation
    biz_res = await db.execute(select(BusinessData))
    biz_records = biz_res.scalars().all()
    offline_total = sum(b.daily_revenue for b in biz_records)
    offline_monthly = sum(
        b.daily_revenue for b in biz_records
        if b.date >= month_start.strftime("%Y-%m-%d")
    )
    total_revenue = total_revenue_web + offline_total
    monthly_revenue = monthly_revenue_web + offline_monthly

    # Status
    pending = await count_orders(Order, Order.status == "new")
    completed = await count_orders(Order, Order.status == "delivered")
    cancelled = await count_orders(Order, Order.status == "cancelled")

    # Sources
    whatsapp = await count_orders(ManualOrder, ManualOrder.order_source == "whatsapp")
    phone = await count_orders(ManualOrder, ManualOrder.order_source == "phone")

    # Best seller
    best_res = await db.execute(
        select(Product.name).order_by(Product.total_sold.desc()).limit(1)
    )
    best_cake = best_res.scalar_one_or_none()

    best_cat_res = await db.execute(
        select(Category.name, func.count(Product.id).label("cnt"))
        .join(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(Product.id).desc())
        .limit(1)
    )
    best_cat_row = best_cat_res.first()
    best_cat = best_cat_row[0] if best_cat_row else None

    # Avg order value
    avg_val = total_revenue / max(total_orders, 1)

    # Charts — last 12 months daily revenue from business_data
    monthly_chart = []
    for i in range(11, -1, -1):
        month_dt = (now - timedelta(days=30 * i)).replace(day=1)
        month_label = month_dt.strftime("%b %Y")
        month_prefix = month_dt.strftime("%Y-%m")
        rev = sum(b.daily_revenue for b in biz_records if b.date.startswith(month_prefix))
        monthly_chart.append({"month": month_label, "revenue": rev})

    # Daily last 7 days
    daily_chart = []
    for i in range(6, -1, -1):
        day = (today_start - timedelta(days=i))
        label = day.strftime("%a")
        cnt = await count_orders(Order, and_(
            Order.created_at >= day,
            Order.created_at < day + timedelta(days=1),
        ))
        daily_chart.append({"day": label, "orders": cnt})

    # Category sales from business_data
    cat_totals: dict = {}
    for b in biz_records:
        if b.category_sales:
            for cat, qty in b.category_sales.items():
                cat_totals[cat] = cat_totals.get(cat, 0) + qty
    cat_chart = [{"category": k, "sales": v} for k, v in cat_totals.items()]

    # Best selling products from products table
    best_prod_res = await db.execute(
        select(Product.name, Product.total_sold)
        .order_by(Product.total_sold.desc())
        .limit(5)
    )
    best_products = [{"name": r[0], "sold": r[1]} for r in best_prod_res.all()]

    total_cakes = sum(b.cakes_sold for b in biz_records)

    return DashboardStats(
        today_orders=today_orders + today_manual,
        weekly_orders=weekly_orders,
        monthly_orders=monthly_orders,
        total_orders=total_orders,
        today_revenue=today_revenue,
        monthly_revenue=monthly_revenue,
        total_revenue=total_revenue,
        avg_order_value=avg_val,
        total_cakes_sold=total_cakes,
        best_selling_cake=best_cake,
        best_selling_category=best_cat,
        pending_orders=pending,
        completed_orders=completed,
        cancelled_orders=cancelled,
        manual_orders=total_manual,
        website_orders=total_orders_web,
        whatsapp_orders=whatsapp,
        phone_orders=phone,
        monthly_sales_chart=monthly_chart,
        daily_orders_chart=daily_chart,
        category_sales_chart=cat_chart,
        best_selling_products=best_products,
    )


# ─── Business Data CRUD ───────────────────────────────────────────────────────

@router.post("/business-data", response_model=BusinessDataOut)
async def create_business_data(
    data: BusinessDataCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    from sqlalchemy import select
    existing = await db.execute(select(BusinessData).where(BusinessData.date == data.date))
    record = existing.scalar_one_or_none()
    if record:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(record, k, v)
    else:
        record = BusinessData(**data.model_dump())
        db.add(record)
    await db.flush()
    return BusinessDataOut.model_validate(record)


@router.get("/business-data", response_model=list)
async def list_business_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = select(BusinessData).order_by(BusinessData.date.desc())
    if start_date:
        q = q.where(BusinessData.date >= start_date)
    if end_date:
        q = q.where(BusinessData.date <= end_date)
    result = await db.execute(q)
    return [BusinessDataOut.model_validate(r) for r in result.scalars().all()]


@router.put("/business-data/{record_id}", response_model=BusinessDataOut)
async def update_business_data(
    record_id: int,
    data: BusinessDataUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(BusinessData).where(BusinessData.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    return BusinessDataOut.model_validate(record)
