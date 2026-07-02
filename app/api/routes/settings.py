from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.setting import Setting
from app.schemas.setting import SettingSchema
from app.services.cloudinary_service import upload_image

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/{key}", response_model=SettingSchema)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingSchema(key=key, value=None)
    return setting


@router.post("/{key}", response_model=SettingSchema)
async def update_setting(
    key: str,
    value: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    await db.commit()
    await db.refresh(setting)
    return setting


@router.post("/{key}/upload", response_model=SettingSchema)
async def upload_setting_file(
    key: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    content = await file.read()
    cloud_data = await upload_image(content, file.filename or f"setting_{key}")
    image_url = cloud_data["url"]

    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(key=key, value=image_url)
        db.add(setting)
    else:
        setting.value = image_url
    await db.commit()
    await db.refresh(setting)
    return setting


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        await db.delete(setting)
        await db.commit()
    return {"message": f"Setting {key} deleted"}
