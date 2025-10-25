# database.py
import aiosqlite
import asyncio

from config import DB_NAME

CREATE_TABLE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,            -- Название товара или услуги
    url TEXT,             -- URL
    description TEXT,     -- Описание (HTML ok)
    visible BOOLEAN ,      -- 1 => выставлен, 0 => скрыт
    category TEXT,        -- Размещение на сайте
    article TEXT,         -- Артикул 
    price REAL,           -- Цена продажи
    old_price REAL,       -- Старая цена
    stock INTEGER,        -- Остаток
    message_id INTEGER    -- message_id in Telegram channel (optional)
);
"""

CREATE_TABLE_IMAGES = """
CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
"""


async def init_db():
    """Create the DB file and products table if they don't exist."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(CREATE_TABLE_IMAGES)
        await db.execute(CREATE_TABLE_PRODUCTS)
        await db.commit()


async def add_product(product: dict):
    """Insert a new product record.
    product keys: name, url, description, visible (0/1), category, article, price, old_price, stock, message_id(optional)
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO products
            (name, url, description, visible, category, article, price, old_price, stock, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.get("name"),
                product.get("url"),
                product.get("description"),
                1 if product.get("visible") else 0,
                product.get("category"),
                product.get("article"),
                product.get("price"),
                product.get("old_price"),
                product.get("stock"),
                product.get("message_id"),
            ),
        )
        await db.commit()


async def get_all_products():
    """Return a list of rows (tuples) for all products."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM products") as cursor:
            rows = await cursor.fetchall()
            return rows


async def update_stock(product_id: int, new_stock: int):
    """Update stock for a product by id."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        await db.commit()


async def delete_product(product_id: int):
    """Delete product by id."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()

if __name__ == "__main__":
    asyncio.run(init_db())