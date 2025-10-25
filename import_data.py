import pandas as pd
import asyncio
import aiosqlite
from config import DB_NAME, EXCEL_FILE


COLUMN_MAP = {
    "Артикул": "article",
    "Название товара или услуги": "name",
    "Описание": "description",
    "Цена продажи": "price",
    "Старая цена": "old_price",
    "Остаток": "stock",
    "Размещение на сайте": "category",
    "URL": "url",
    "Видимость на витрине": "visible",
    "Изображения": "image"  # Now mapping images column
}

async def main():
    # Clear table first
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products;")
        await db.execute("DELETE FROM product_images;")  # also clear images
        await db.commit()
        print("✅ Cleared 'products' and 'product_images' tables.")

    # Import new data
    df = pd.read_excel(EXCEL_FILE)
    df = df.rename(columns=COLUMN_MAP)
    df = df[[c for c in COLUMN_MAP.values() if c in df.columns]]
    df = df.where(pd.notnull(df), None)

    async with aiosqlite.connect(DB_NAME) as db:
        for _, row in df.iterrows():
            cursor = await db.execute(
                """
                INSERT INTO products
                (article, name, description, price, old_price, stock, category, url, visible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("article"),
                    row.get("name"),
                    row.get("description"),
                    row.get("price"),
                    row.get("old_price"),
                    row.get("stock"),
                    row.get("category"),
                    row.get("url"),
                    1 if row.get("visible") == "выставлен" else 0
                )
            )
            product_id = cursor.lastrowid

            # Insert images
            image_urls = str(row.get("image") or "").split()
            for url in image_urls:
                await db.execute(
                    "INSERT INTO product_images (product_id, image_url) VALUES (?, ?)",
                    (product_id, url)
                )
        await db.commit()
        print(f"✅ Imported {len(df)} products with their images.")


if __name__ == "__main__":
    asyncio.run(main())
