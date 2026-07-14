from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from database.models import Base
from database.repository import AdminRepository

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _migrate_sync(connection) -> None:
    inspector = inspect(connection)
    tables = inspector.get_table_names()

    if "products" in tables:
        cols = {c["name"] for c in inspector.get_columns("products")}
        if "sku" not in cols:
            connection.execute(text("ALTER TABLE products ADD COLUMN sku VARCHAR(50)"))
            connection.execute(
                text("UPDATE products SET sku = 'DS-' || id WHERE sku IS NULL OR sku = ''")
            )
        if "image_file_id" not in cols:
            connection.execute(
                text("ALTER TABLE products ADD COLUMN image_file_id VARCHAR(255)")
            )
        if "cost_price" not in cols:
            if "purchase_price" in cols:
                connection.execute(
                    text(
                        "ALTER TABLE products ADD COLUMN cost_price FLOAT "
                        "DEFAULT 0"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE products SET cost_price = purchase_price "
                        "WHERE cost_price IS NULL OR cost_price = 0"
                    )
                )
            else:
                connection.execute(
                    text("ALTER TABLE products ADD COLUMN cost_price FLOAT DEFAULT 0")
                )
        if "category" in cols:
            connection.execute(
                text("UPDATE products SET category = '' WHERE category IS NULL")
            )
        if "purchase_price" in cols and "cost_price" in cols:
            connection.execute(
                text(
                    "UPDATE products SET purchase_price = cost_price "
                    "WHERE purchase_price IS NULL OR purchase_price = 0"
                )
            )
        elif "purchase_price" in cols and "cost_price" not in cols:
            connection.execute(
                text("ALTER TABLE products ADD COLUMN cost_price FLOAT DEFAULT 0")
            )
            connection.execute(
                text("UPDATE products SET cost_price = purchase_price")
            )

    if "sales" in tables:
        cols = {c["name"] for c in inspector.get_columns("sales")}
        if "admin_id" not in cols:
            connection.execute(text("ALTER TABLE sales ADD COLUMN admin_id INTEGER"))
        if "admin_name" not in cols:
            connection.execute(
                text("ALTER TABLE sales ADD COLUMN admin_name VARCHAR(100) DEFAULT ''")
            )
        if "cost_price" not in cols:
            if "purchase_price" in cols:
                connection.execute(
                    text("ALTER TABLE sales ADD COLUMN cost_price FLOAT DEFAULT 0")
                )
                connection.execute(
                    text(
                        "UPDATE sales SET cost_price = purchase_price "
                        "WHERE cost_price IS NULL OR cost_price = 0"
                    )
                )
            else:
                connection.execute(
                    text("ALTER TABLE sales ADD COLUMN cost_price FLOAT DEFAULT 0")
                )
        if "is_cancelled" not in cols:
            connection.execute(
                text(
                    "ALTER TABLE sales ADD COLUMN is_cancelled BOOLEAN DEFAULT 0"
                )
            )
        if "cancelled_at" not in cols:
            connection.execute(text("ALTER TABLE sales ADD COLUMN cancelled_at DATETIME"))
        if "purchase_price" in cols and "cost_price" in cols:
            connection.execute(
                text(
                    "UPDATE sales SET purchase_price = cost_price "
                    "WHERE purchase_price IS NULL OR purchase_price = 0"
                )
            )

    if "expenses" not in tables:
        Base.metadata.tables["expenses"].create(connection)

    if "admins" in tables:
        cols = {c["name"] for c in inspector.get_columns("admins")}
        if "is_main" not in cols:
            connection.execute(
                text("ALTER TABLE admins ADD COLUMN is_main BOOLEAN DEFAULT 0")
            )
        if settings.admin_ids:
            ids_str = ",".join(str(i) for i in settings.admin_ids)
            connection.execute(
                text(f"UPDATE admins SET is_main = 1 WHERE telegram_id IN ({ids_str})")
            )

    if "products" in tables:
        cols = {c["name"] for c in inspector.get_columns("products")}
        if "is_active" not in cols:
            connection.execute(
                text("ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT 1")
            )
            connection.execute(
                text("UPDATE products SET is_active = 1 WHERE is_active IS NULL")
            )


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sync)
    await seed_admins()


async def seed_admins() -> None:
    async with async_session() as session:
        repo = AdminRepository(session)
        if await repo.count() > 0:
            return
        for admin_id in settings.admin_ids:
            await repo.create(
                telegram_id=admin_id, name=f"Admin {admin_id}", is_main=True
            )
