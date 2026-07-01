from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import re

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categories"])


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


@router.get("/", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order)
    )
    categories = result.scalars().all()
    out = []
    for cat in categories:
        count_res = await db.execute(
            select(func.count()).where(
                Product.category_id == cat.id, Product.is_available == True
            )
        )
        count = count_res.scalar() or 0
        cat_out = CategoryOut.model_validate(cat)
        cat_out.product_count = count
        out.append(cat_out)
    return out


@router.get("/all", response_model=List[CategoryOut])
async def list_all_categories(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return [CategoryOut.model_validate(c) for c in result.scalars().all()]


@router.post("/", response_model=CategoryOut)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    slug = _slugify(data.name)
    existing = await db.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(__import__('time').time())}"
    cat = Category(**data.model_dump(), slug=slug)
    db.add(cat)
    await db.flush()
    return CategoryOut.model_validate(cat)


@router.put("/{cat_id}", response_model=CategoryOut)
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    await db.flush()
    return CategoryOut.model_validate(cat)


@router.delete("/{cat_id}")
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    return {"message": "Category deleted"}
