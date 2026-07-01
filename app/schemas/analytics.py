from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime


class BusinessDataCreate(BaseModel):
    date: str  # YYYY-MM-DD
    daily_revenue: float = 0
    cakes_sold: int = 0
    total_profit: float = 0
    category_sales: Optional[Dict[str, int]] = None
    product_sales: Optional[List[Any]] = None
    notes: Optional[str] = None


class BusinessDataUpdate(BaseModel):
    daily_revenue: Optional[float] = None
    cakes_sold: Optional[int] = None
    total_profit: Optional[float] = None
    category_sales: Optional[Dict[str, int]] = None
    product_sales: Optional[List[Any]] = None
    notes: Optional[str] = None


class BusinessDataOut(BusinessDataCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    # Orders today/week/month/total
    today_orders: int
    weekly_orders: int
    monthly_orders: int
    total_orders: int

    # Revenue
    today_revenue: float
    monthly_revenue: float
    total_revenue: float
    avg_order_value: float

    # Sales
    total_cakes_sold: int
    best_selling_cake: Optional[str] = None
    best_selling_category: Optional[str] = None

    # Status breakdown
    pending_orders: int
    completed_orders: int
    cancelled_orders: int

    # Source breakdown
    manual_orders: int
    website_orders: int
    whatsapp_orders: int
    phone_orders: int

    # Charts data
    monthly_sales_chart: List[Any] = []
    daily_orders_chart: List[Any] = []
    category_sales_chart: List[Any] = []
    best_selling_products: List[Any] = []
