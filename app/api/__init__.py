from app.api.routes import auth, products, categories, images, orders, analytics
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(images.router)
api_router.include_router(orders.router)
api_router.include_router(analytics.router)
