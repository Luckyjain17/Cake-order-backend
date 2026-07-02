from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ─── Product Image ──────────────────────────────────────────────────────────

class ProductImageOut(BaseModel):
    id: int
    cloudinary_public_id: str
    url: str
    thumbnail_url: Optional[str] = None
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    alt_text: Optional[str] = None
    image_type: Optional[str] = None
    sort_order: int
    is_cover: bool

    class Config:
        from_attributes = True


class ImageReorderItem(BaseModel):
    id: int
    sort_order: int


class ImageReorderRequest(BaseModel):
    images: List[ImageReorderItem]


# ─── Product ────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    category_id: Optional[int] = None
    cake_type: Optional[str] = None
    flavor: Optional[str] = None
    shape: Optional[str] = None
    weight_options: Optional[str] = None
    original_price: float = 0
    selling_price: float = 0
    discount_percent: float = 0
    price_base_weight: Optional[str] = "500g"
    preparation_time: Optional[str] = None
    serves: Optional[str] = None
    storage_instructions: Optional[str] = None
    is_customizable: bool = False
    is_available: bool = True
    is_best_seller: bool = False
    is_trending: bool = False
    is_new_arrival: bool = True
    is_eggless: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    category_id: Optional[int] = None
    cake_type: Optional[str] = None
    flavor: Optional[str] = None
    shape: Optional[str] = None
    weight_options: Optional[str] = None
    original_price: Optional[float] = None
    selling_price: Optional[float] = None
    discount_percent: Optional[float] = None
    price_base_weight: Optional[str] = None
    preparation_time: Optional[str] = None
    serves: Optional[str] = None
    storage_instructions: Optional[str] = None
    is_customizable: Optional[bool] = None
    is_available: Optional[bool] = None
    is_best_seller: Optional[bool] = None
    is_trending: Optional[bool] = None
    is_new_arrival: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    slug: str
    rating: float
    rating_count: int
    total_sold: int
    images: List[ProductImageOut] = []
    cover_image: Optional[ProductImageOut] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    id: int
    name: str
    slug: str
    short_description: Optional[str] = None
    selling_price: float
    original_price: float
    discount_percent: float
    flavor: Optional[str] = None
    is_available: bool
    is_best_seller: bool
    is_trending: bool
    is_new_arrival: bool
    rating: float
    cover_image: Optional[ProductImageOut] = None
    category_id: Optional[int] = None
    price_base_weight: Optional[str] = "500g"

    class Config:
        from_attributes = True


class PaginatedProducts(BaseModel):
    items: List[ProductListOut]
    total: int
    page: int
    per_page: int
    pages: int
