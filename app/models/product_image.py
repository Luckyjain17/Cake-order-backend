from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Cloudinary data
    cloudinary_public_id = Column(String(300), nullable=False)
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)    # w_200 transform
    medium_url = Column(String(500), nullable=True)       # w_600 transform
    large_url = Column(String(500), nullable=True)        # w_1200 transform

    # Metadata
    alt_text = Column(String(200), nullable=True)
    image_type = Column(String(50), nullable=True)        # front, side, top, slice, packaging, other
    sort_order = Column(Integer, default=0)
    is_cover = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="images")
