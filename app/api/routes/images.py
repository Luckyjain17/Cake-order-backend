from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.product import ProductImageOut, ImageReorderRequest
from app.services.cloudinary_service import upload_image, delete_image

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload/{product_id}", response_model=List[ProductImageOut])
async def upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    image_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Determine next sort order
    existing = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id)
    )
    existing_images = existing.scalars().all()
    next_order = max([img.sort_order for img in existing_images], default=-1) + 1

    uploaded = []
    for i, file in enumerate(files):
        content = await file.read()
        cloud_data = await upload_image(content, file.filename or f"product_{product_id}_{i}")

        is_cover = len(existing_images) == 0 and i == 0  # first image is cover by default

        img = ProductImage(
            product_id=product_id,
            cloudinary_public_id=cloud_data["cloudinary_public_id"],
            url=cloud_data["url"],
            thumbnail_url=cloud_data["thumbnail_url"],
            medium_url=cloud_data["medium_url"],
            large_url=cloud_data["large_url"],
            alt_text=product.name,
            image_type=image_type or "other",
            sort_order=next_order + i,
            is_cover=is_cover,
        )
        db.add(img)
        await db.flush()
        uploaded.append(ProductImageOut.model_validate(img))

    return uploaded


@router.delete("/{image_id}")
async def delete_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(ProductImage).where(ProductImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    was_cover = img.is_cover
    product_id = img.product_id

    await delete_image(img.cloudinary_public_id)
    await db.delete(img)
    await db.flush()

    # If deleted image was cover, assign cover to next available image
    if was_cover:
        remaining = await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
        )
        first = remaining.scalars().first()
        if first:
            first.is_cover = True

    return {"message": "Image deleted"}


@router.patch("/{image_id}/set-cover")
async def set_cover_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(ProductImage).where(ProductImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    # Unset all covers for this product
    all_imgs = await db.execute(
        select(ProductImage).where(ProductImage.product_id == img.product_id)
    )
    for other in all_imgs.scalars().all():
        other.is_cover = False

    img.is_cover = True
    return {"message": "Cover image updated"}


@router.patch("/reorder")
async def reorder_images(
    data: ImageReorderRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    for item in data.images:
        result = await db.execute(select(ProductImage).where(ProductImage.id == item.id))
        img = result.scalar_one_or_none()
        if img:
            img.sort_order = item.sort_order
    return {"message": "Images reordered"}
