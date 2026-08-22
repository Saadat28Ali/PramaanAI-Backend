import os
import mysql.connector
from mysql.connector import pooling, Error
from dotenv import load_dotenv

# Load variables from root .env
load_dotenv()

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="pramaan_pool",
        pool_size=5,
        pool_reset_session=True,
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "pramaanai_db"),
        port=int(os.getenv("DB_PORT", 3306))
    )
    print("[DB] Connection pool established successfully.")
except Error as e:
    print(f"[DB ERROR] Error initializing connection pool: {e}")
    db_pool = None


def get_db_connection():
    """Fetches a connection from the pool."""
    if db_pool is None:
        raise Exception("Database connection pool is not initialized.")
    return db_pool.get_connection()