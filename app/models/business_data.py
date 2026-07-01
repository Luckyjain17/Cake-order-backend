from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class BusinessData(Base):
    """Manual business data entry by admin for offline tracking."""
    __tablename__ = "business_data"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(20), nullable=False, unique=True, index=True)  # YYYY-MM-DD

    # Revenue
    daily_revenue = Column(Float, default=0)
    cakes_sold = Column(Integer, default=0)
    total_profit = Column(Float, default=0)

    # Category-wise sales JSON: {"Birthday": 5, "Wedding": 2}
    category_sales = Column(JSON, nullable=True)

    # Product-wise sales JSON: [{"name": "Choco Cake", "qty": 3, "revenue": 600}]
    product_sales = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
