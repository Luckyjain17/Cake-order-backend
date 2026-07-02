from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON
)
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    """Orders placed through the website."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)

    # Customer info
    customer_name = Column(String(150), nullable=False)
    mobile_number = Column(String(15), nullable=False)
    delivery_address = Column(Text, nullable=False)
    landmark = Column(String(200), nullable=True)
    delivery_date = Column(String(50), nullable=True)
    delivery_time = Column(String(50), nullable=True)
    special_instructions = Column(Text, nullable=True)

    # Cart items stored as JSON: [{product_id, name, qty, weight, price, image_url}]
    items = Column(JSON, nullable=False, default=list)

    # Pricing
    subtotal = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)

    # Payment
    payment_method = Column(String(30), nullable=True)   # "qr_code" | "whatsapp"
    payment_status = Column(String(20), default="pending")  # pending | paid | failed

    # Order status
    status = Column(String(30), default="new")           # new | confirmed | processing | ready | delivered | cancelled

    # Source
    order_source = Column(String(30), default="website")  # website | whatsapp | phone | walkin | instagram | facebook | other

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ManualOrder(Base):
    """Orders manually entered by admin from WhatsApp, calls, etc."""
    __tablename__ = "manual_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)

    # Customer info
    customer_name = Column(String(150), nullable=False)
    mobile_number = Column(String(15), nullable=False)
    address = Column(Text, nullable=True)

    # Cake details
    cake_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    weight = Column(String(50), nullable=True)
    amount = Column(Float, nullable=False, default=0)
    paid_amount = Column(Float, nullable=True, default=0)

    # Meta
    order_source = Column(String(30), nullable=False)   # whatsapp | phone | walkin | instagram | facebook | other
    payment_status = Column(String(20), default="pending")
    status = Column(String(30), default="new")
    notes = Column(Text, nullable=True)
    delivery_date = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
