import asyncio
from sqlalchemy import select
from app.core.database import AsyncSession, sessionmaker, engine
from app.models.order import Order
from app.api.routes.orders import order_to_manual
from app.schemas.order import ManualOrderUpdate, ManualOrderOut

async def debug_test():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Load order ID 32
        result = await session.execute(select(Order).where(Order.id == 32))
        order = result.scalar_one_or_none()
        if not order:
            print("Order 32 not found!")
            return
        
        print("Original Order 32 items:", order.items)
        print("Original Order 32 total_amount:", order.total_amount)
        print("Original Order 32 paid_amount:", order.paid_amount)
        
        # Test order_to_manual conversion
        try:
            mapped = order_to_manual(order)
            print("Mapped order:", mapped)
            ManualOrderOut(**mapped)
            print("Pydantic validation succeeded!")
        except Exception as e:
            import traceback
            print("Pydantic validation failed:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_test())
