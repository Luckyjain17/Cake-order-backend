from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, ForeignKey, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Basic
    name = Column(String(200), nullable=False, index=True)
    short_description = Column(String(500), nullable=True)
    full_description = Column(Text, nullable=True)
    slug = Column(String(250), unique=True, nullable=False, index=True)

    # Category FK
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Cake attributes
    cake_type = Column(String(50), nullable=True)     # Fondant, Cream Cake, etc.
    flavor = Column(String(100), nullable=True)
    shape = Column(String(50), nullable=True)         # Round, Square, Heart, etc.

    # Weight options stored as JSON string (e.g. ["500g","1kg","2kg"])
    weight_options = Column(String(500), nullable=True)

    # Pricing
    original_price = Column(Float, nullable=False, default=0)
    selling_price = Column(Float, nullable=False, default=0)
    discount_percent = Column(Float, default=0)
    price_base_weight = Column(String(50), nullable=False, default="500g")

    # Extra info
    preparation_time = Column(String(100), nullable=True)   # e.g. "24 hours"
    serves = Column(String(50), nullable=True)              # e.g. "8-10 people"
    storage_instructions = Column(Text, nullable=True)
    storage_instructions = Column(Text, nullable=True)

    # Flags
    is_customizable = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    is_best_seller = Column(Boolean, default=False)
    is_trending = Column(Boolean, default=False)
    is_new_arrival = Column(Boolean, default=True)
    is_eggless = Column(Boolean, default=True)       # Always True per shop policy

    # Ratings (manually set or computed from orders)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    total_sold = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="products")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
        lazy="selectin",
    )
