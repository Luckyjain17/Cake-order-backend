from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS price_base_weight VARCHAR(50) NOT NULL DEFAULT '500g';"))
        except Exception as e:
            print("Auto migration column check:", e)
    # Seed default admin + categories
    await seed_initial_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Cake Ordering Web Application API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

app.include_router(api_router)

# Mount local static uploads directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(static_dir, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


async def seed_initial_data():
    """Seed admin user and default categories if not present."""
    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import AdminUser
    from app.models.category import Category
    from sqlalchemy import select
    import re

    def slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[\s_-]+", "-", text)

    async with AsyncSessionLocal() as db:
        # Admin user
        result = await db.execute(select(AdminUser).where(AdminUser.username == settings.ADMIN_USERNAME))
        if not result.scalar_one_or_none():
            admin = AdminUser(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
            )
            db.add(admin)

        # Default categories
        default_categories = [
            {"name": "Birthday Cake", "icon": "🎂", "sort_order": 0},
            {"name": "Anniversary Cake", "icon": "💑", "sort_order": 1},
            {"name": "Wedding Cake", "icon": "💍", "sort_order": 2},
            {"name": "Kids Cake", "icon": "🧒", "sort_order": 3},
            {"name": "Cup Cake", "icon": "🧁", "sort_order": 4},
            {"name": "Pastry", "icon": "🥐", "sort_order": 5},
            {"name": "Theme Cake", "icon": "🎨", "sort_order": 6},
            {"name": "Festival Cake", "icon": "🎉", "sort_order": 7},
            {"name": "Photo Cake", "icon": "📸", "sort_order": 8},
        ]
        for cat_data in default_categories:
            slug = slugify(cat_data["name"])
            existing = await db.execute(select(Category).where(Category.slug == slug))
            if not existing.scalar_one_or_none():
                db.add(Category(**cat_data, slug=slug))

        await db.commit()
