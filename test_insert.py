import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.product import Product

async def test():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("Attempting to insert test product...")
            p = Product(
                name="Test Cake",
                slug="test-cake-123",
                original_price=100.0,
                selling_price=100.0,
                discount_percent=0.0,
                is_eggless=True,
                is_available=True,
                is_new_arrival=True,
                is_trending=False,
                is_best_seller=False,
                is_customizable=False
            )
            session.add(p)
            await session.flush()
            print("Flush successful! Product ID:", p.id)
            await session.commit()
            print("Commit successful!")
        except Exception as e:
            print("ERROR INSERTING:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
