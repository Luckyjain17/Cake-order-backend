import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.core.config import settings
from fastapi import HTTPException


def clean_env_var(val: str) -> str:
    """Strip outer quotes and whitespace from environment variable values."""
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    return val


# Configure Cloudinary
cloudinary.config(
    cloud_name=clean_env_var(settings.CLOUDINARY_CLOUD_NAME),
    api_key=clean_env_var(settings.CLOUDINARY_API_KEY),
    api_secret=clean_env_var(settings.CLOUDINARY_API_SECRET),
    secure=True,
)

FOLDER = "cake_shop"


async def upload_image(file_bytes: bytes, filename: str, folder: str = FOLDER) -> dict:
    """Upload image to Cloudinary. Raises HTTPException if not configured or upload fails."""
    cloud_name = clean_env_var(settings.CLOUDINARY_CLOUD_NAME)
    api_key = clean_env_var(settings.CLOUDINARY_API_KEY)
    api_secret = clean_env_var(settings.CLOUDINARY_API_SECRET)

    is_placeholder = (
        cloud_name in ("your_cloud_name", "") or
        api_key in ("your_api_key", "") or
        api_secret in ("your_api_secret", "")
    )

    if is_placeholder:
        raise HTTPException(
            status_code=500,
            detail="Cloudinary is not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
        )

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            resource_type="image",
            format="webp",
            quality="auto:good",
            transformation=[
                {"width": 2000, "crop": "limit"},
            ],
        )
        public_id = result["public_id"]
        return {
            "cloudinary_public_id": public_id,
            "url": result["secure_url"],
            "thumbnail_url": cloudinary.CloudinaryImage(public_id).build_url(
                width=200, height=200, crop="fit", fetch_format="auto", quality="auto"
            ),
            "medium_url": cloudinary.CloudinaryImage(public_id).build_url(
                width=600, fetch_format="auto", quality="auto"
            ),
            "large_url": cloudinary.CloudinaryImage(public_id).build_url(
                width=1200, fetch_format="auto", quality="auto"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("Cloudinary upload failed! Error:", e)
        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary upload failed: {str(e)}"
        )


async def delete_image(public_id: str) -> bool:
    """Delete image from Cloudinary."""
    if not public_id or public_id.startswith("local_"):
        # Old local image – nothing to delete on Cloudinary
        return True
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        return result.get("result") == "ok"
    except Exception:
        return False
