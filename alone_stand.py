import pymysql
import os 
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
load_dotenv()

def get_db_connection():
    """Establish and return a database connection."""
    try:
        print("Attempting to connect to the database...")
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            charset='utf8mb4',
            port=int(os.getenv('DB_PORT')),
            cursorclass=DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        raise RuntimeError(f"Database connection failed: {e}") from e
