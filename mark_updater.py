# mark_updated.py
import sqlite3
from config import DB_NAME

def mark_product_updated(product_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE products SET needs_update = 1 WHERE id = ?",
        (product_id,)
    )
    conn.commit()
    conn.close()
    print(f"✅ Marked product {product_id} as needing update.")

if __name__ == "__main__":
    try:
        product_id = int(input("Enter product ID to mark for update: "))
        mark_product_updated(product_id)
    except ValueError:
        print("❌ Invalid input. Please enter a valid product ID (integer).")