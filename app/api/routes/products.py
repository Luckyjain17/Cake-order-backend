from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
import re, time

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductListOut, PaginatedProducts,
)

router = APIRouter(prefix="/products", tags=["Products"])


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


def _attach_cover(product: Product) -> ProductOut:
    out = ProductOut.model_validate(product)
    if out.images:
        out.images.sort(key=lambda img: (not img.is_cover, img.sort_order))
    covers = [img for img in out.images if img.is_cover]
    if covers:
        out.cover_image = covers[0]
    elif out.images:
        out.cover_image = out.images[0]
    return out


def _attach_cover_list(product: Product) -> ProductListOut:
    out = ProductListOut.model_validate(product)
    covers = [img for img in product.images if img.is_cover]
    if covers:
        out.cover_image = covers[0]
    elif product.images:
        out.cover_image = product.images[0]
    return out


# ─── Public ──────────────────────────────────────────────────────────────────

@router.get("/filters-list")
async def get_filters_list(db: AsyncSession = Depends(get_db)):
    # Fetch unique flavors and cake types
    flavors_query = select(Product.flavor).where(Product.flavor != None).distinct()
    cake_types_query = select(Product.cake_type).where(Product.cake_type != None).distinct()

    flavors_res = await db.execute(flavors_query)
    cake_types_res = await db.execute(cake_types_query)

    # Convert distinct tuples to a clean sorted list of strings, splitting comma-separated multiple flavors
    raw_flavors = []
    for r in flavors_res.all():
        if r[0]:
            raw_flavors.extend([part.strip() for part in r[0].split(",") if part.strip()])
    flavors = sorted(list(set(raw_flavors)))
    cake_types = sorted(list(set([r[0].strip() for r in cake_types_res.all() if r[0] and r[0].strip()])))

    return {
        "flavors": flavors,
        "cake_types": cake_types
    }


@router.get("/", response_model=PaginatedProducts)
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    flavor: Optional[str] = None,
    cake_type: Optional[str] = None,
    is_best_seller: Optional[bool] = None,
    is_trending: Optional[bool] = None,
    is_new_arrival: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Product).where(Product.is_available == True).options(selectinload(Product.images))
    if category_id:
        q = q.where(Product.category_id == category_id)
    if search:
        q = q.where(or_(
            Product.name.ilike(f"%{search}%"),
            Product.short_description.ilike(f"%{search}%"),
        ))
    if flavor:
        q = q.where(Product.flavor.ilike(f"%{flavor}%"))
    if cake_type:
        q = q.where(Product.cake_type.ilike(f"%{cake_type}%"))
    if is_best_seller is not None:
        q = q.where(Product.is_best_seller == is_best_seller)
    if is_trending is not None:
        q = q.where(Product.is_trending == is_trending)
    if is_new_arrival is not None:
        q = q.where(Product.is_new_arrival == is_new_arrival)
    if min_price is not None:
        q = q.where(Product.selling_price >= min_price)
    if max_price is not None:
        q = q.where(Product.selling_price <= max_price)

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar() or 0

    q = q.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    products = result.scalars().all()

    items = [_attach_cover_list(p) for p in products]
    return PaginatedProducts(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/featured", response_model=PaginatedProducts)
async def featured_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .where(Product.is_available == True, Product.is_best_seller == True)
        .order_by(Product.total_sold.desc())
        .options(selectinload(Product.images))
        .limit(10)
    )
    products = result.scalars().all()
    return PaginatedProducts(
        items=[_attach_cover_list(p) for p in products],
        total=len(products), page=1, per_page=10, pages=1,
    )


@router.get("/trending", response_model=PaginatedProducts)
async def trending_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .where(Product.is_available == True, Product.is_trending == True)
        .options(selectinload(Product.images))
        .limit(10)
    )
    products = result.scalars().all()
    return PaginatedProducts(
        items=[_attach_cover_list(p) for p in products],
        total=len(products), page=1, per_page=10, pages=1,
    )


@router.get("/new-arrivals", response_model=PaginatedProducts)
async def new_arrivals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .where(Product.is_available == True, Product.is_new_arrival == True)
        .order_by(Product.created_at.desc())
        .options(selectinload(Product.images))
        .limit(10)
    )
    products = result.scalars().all()
    return PaginatedProducts(
        items=[_attach_cover_list(p) for p in products],
        total=len(products), page=1, per_page=10, pages=1,
    )


@router.get("/{slug}", response_model=ProductOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .where(Product.slug == slug)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _attach_cover(product)


@router.get("/id/{product_id}", response_model=ProductOut)
async def get_product_by_id(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _attach_cover(product)




# ─── Admin ───────────────────────────────────────────────────────────────────

@router.get("/admin/all", response_model=PaginatedProducts)
async def admin_list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = select(Product)
    if search:
        search_term = search.strip()
        conditions = [
            Product.name.ilike(f"%{search_term}%"),
            Product.short_description.ilike(f"%{search_term}%"),
            Product.flavor.ilike(f"%{search_term}%"),
        ]
        try:
            val = int(search_term)
            conditions.append(Product.id == val)
        except ValueError:
            pass
        q = q.where(or_(*conditions))
    if category_id:
        q = q.where(Product.category_id == category_id)

    count_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_res.scalar() or 0
    q = q.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    products = result.scalars().all()
    return PaginatedProducts(
        items=[_attach_cover_list(p) for p in products],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("/", response_model=ProductOut)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    slug = _slugify(data.name)
    existing = await db.execute(select(Product).where(Product.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(time.time())}"
    product = Product(**data.model_dump(exclude={"is_eggless"}), slug=slug, is_eggless=True)
    db.add(product)
    await db.flush()
    res = await db.execute(
        select(Product)
        .where(Product.id == product.id)
        .options(selectinload(Product.images))
    )
    product = res.scalar_one()
    return _attach_cover(product)


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    await db.flush()
    res = await db.execute(
        select(Product)
        .where(Product.id == product.id)
        .options(selectinload(Product.images))
    )
    product = res.scalar_one()
    return _attach_cover(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Delete Cloudinary images first
    from app.services.cloudinary_service import delete_image
    for img in product.images:
        await delete_image(img.cloudinary_public_id)
    await db.delete(product)
    return {"message": "Product deleted"}


@router.patch("/{product_id}/toggle-availability", response_model=ProductOut)
async def toggle_availability(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_available = not product.is_available
    await db.flush()
    return _attach_cover(product)


@router.delete("/flavors/{flavor_name}")
async def delete_flavor(
    flavor_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(
        select(Product).where(Product.flavor.ilike(f"%{flavor_name}%"))
    )
    products = result.scalars().all()
    for p in products:
        if p.flavor:
            parts = [part.strip() for part in p.flavor.split(",") if part.strip()]
            new_parts = [part for part in parts if part.lower() != flavor_name.lower()]
            p.flavor = ",".join(new_parts) if new_parts else None
    await db.flush()
    return {"message": "Flavor deleted"}


@router.delete("/cake-types/{type_name}")
async def delete_cake_type(
    type_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    from sqlalchemy import update
    await db.execute(
        update(Product)
        .where(Product.cake_type == type_name)
        .values(cake_type=None)
    )
    return {"message": "Cake type deleted"}


@router.post("/bulk", response_model=List[ProductOut])
async def create_products_bulk(
    data: List[ProductCreate],
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    created_products = []
    for item in data:
        slug = _slugify(item.name)
        existing = await db.execute(select(Product).where(Product.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{int(time.time())}-{int(1000 * time.time()) % 1000}"
        product = Product(**item.model_dump(exclude={"is_eggless"}), slug=slug, is_eggless=True)
        db.add(product)
        created_products.append(product)
    
    await db.flush()
    
    result_list = []
    for p in created_products:
        res = await db.execute(
            select(Product)
            .where(Product.id == p.id)
            .options(selectinload(Product.images))
        )
        loaded = res.scalar_one()
        result_list.append(_attach_cover(loaded))
    return result_list

