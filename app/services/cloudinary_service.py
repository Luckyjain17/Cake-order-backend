import os
import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

FOLDER = "cake_shop"


def _build_urls(public_id: str) -> dict:
    """Build optimized URLs at multiple sizes using Cloudinary transformations."""
    base = f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/image/upload"
    return {
        "url": f"{base}/f_auto,q_auto/{public_id}",
        "thumbnail_url": f"{base}/f_auto,q_auto,w_200,h_200,c_fit/{public_id}",
        "medium_url": f"{base}/f_auto,q_auto,w_600/{public_id}",
        "large_url": f"{base}/f_auto,q_auto,w_1200/{public_id}",
    }


async def upload_image(file_bytes: bytes, filename: str, folder: str = FOLDER) -> dict:
    """Upload image to Cloudinary (with fallback to local static storage if credentials are placeholders or upload fails)."""
    is_placeholder = (
        settings.CLOUDINARY_CLOUD_NAME == "your_cloud_name" or
        settings.CLOUDINARY_API_KEY == "your_api_key" or
        settings.CLOUDINARY_API_SECRET == "your_api_secret" or
        not settings.CLOUDINARY_CLOUD_NAME or
        not settings.CLOUDINARY_API_KEY or
        not settings.CLOUDINARY_API_SECRET
    )

    if not is_placeholder:
        try:
            result = cloudinary.uploader.upload(
                file_bytes,
                folder=folder,
                use_filename=True,
                unique_filename=True,
                overwrite=False,
                resource_type="image",
                format="webp",            # auto-convert to WebP
                quality="auto:good",
                transformation=[
                    {"width": 2000, "crop": "limit"},
                ],
            )
            public_id = result["public_id"]
            urls = _build_urls(public_id)
            return {"cloudinary_public_id": public_id, **urls}
        except Exception as e:
            print("Cloudinary upload failed, falling back to local storage. Error:", e)

    # Fallback to local storage
    import re
    safe_name = re.sub(r"[^\w\s-]", "", filename.rsplit(".", 1)[0].lower())
    safe_name = re.sub(r"[\s_-]+", "_", safe_name)
    unique_filename = f"{safe_name}_{int(time.time())}.webp"

    static_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    os.makedirs(static_uploads_dir, exist_ok=True)
    file_path = os.path.join(static_uploads_dir, unique_filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    local_url = f"/static/uploads/{unique_filename}"
    return {
        "cloudinary_public_id": f"local_{unique_filename}",
        "url": local_url,
        "thumbnail_url": local_url,
        "medium_url": local_url,
        "large_url": local_url,
    }


async def delete_image(public_id: str) -> bool:
    """Delete image from Cloudinary or local storage."""
    if public_id.startswith("local_"):
        filename = public_id.replace("local_", "")
        static_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
        file_path = os.path.join(static_uploads_dir, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception:
            return False

    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        return result.get("result") == "ok"
    except Exception:
        return False
