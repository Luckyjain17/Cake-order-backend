from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ─── Website Order ───────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    customer_name: str
    mobile_number: str
    delivery_address: str
    landmark: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time: Optional[str] = None
    special_instructions: Optional[str] = None
    items: List[Any]  # [{product_id, name, qty, weight, price, image_url}]
    subtotal: float
    total_amount: float
    payment_method: Optional[str] = None
    paid_amount: Optional[float] = 0
    order_source: str = "website"


class OrderUpdate(BaseModel):
    payment_status: Optional[str] = None
    status: Optional[str] = None
    paid_amount: Optional[float] = None
    delivery_date: Optional[str] = None


class OrderOut(OrderCreate):
    id: int
    order_number: str
    payment_status: str
    status: str
    paid_amount: Optional[float] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Manual Order ────────────────────────────────────────────────────────────

class ManualOrderCreate(BaseModel):
    customer_name: str
    mobile_number: str
    address: Optional[str] = None
    cake_name: str
    quantity: int = 1
    weight: Optional[str] = None
    amount: float
    paid_amount: Optional[float] = 0
    order_source: str
    payment_status: str = "pending"
    status: str = "new"
    notes: Optional[str] = None
    delivery_date: Optional[str] = None


class ManualOrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    mobile_number: Optional[str] = None
    address: Optional[str] = None
    cake_name: Optional[str] = None
    quantity: Optional[int] = None
    weight: Optional[str] = None
    amount: Optional[float] = None
    paid_amount: Optional[float] = None
    order_source: Optional[str] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    delivery_date: Optional[str] = None


class ManualOrderOut(ManualOrderCreate):
    id: int
    order_number: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedOrders(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedManualOrders(BaseModel):
    items: List[ManualOrderOut]
    total: int
    page: int
    per_page: int
    pages: int
