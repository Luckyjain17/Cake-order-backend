from sqlalchemy import create_engine, text
from app.core.config import settings

def check():
    url = settings.DATABASE_URL
    url_sync = url.replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(url_sync)
    with engine.connect() as conn:
        print("Checking tables in database...")
        res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in res]
        print("Tables found:", tables)
        
        if "products" in tables:
            print("\nColumns in 'products' table:")
            res_cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='products'"))
            for r in res_cols:
                print(f" - {r[0]}: {r[1]}")
        else:
            print("Table 'products' does not exist!")

if __name__ == "__main__":
    check()
