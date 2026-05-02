import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

def get_connection():
    """Create and return a psycopg2 connection, reading fresh from .env."""
    # Always reload .env to get the latest changes
    load_dotenv(ENV_PATH, override=True)
    
    host = os.getenv('DB_HOST', '13.239.118.235')
    port = os.getenv('DB_PORT', '5432')
    dbname = os.getenv('DB_NAME', 'data-mining')
    user = os.getenv('DB_USER', 'user2')
    password = os.getenv('DB_PASSWORD', 'datamining')
    
    # If password is empty string, force use of default
    if not password:
        password = 'datamining'

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )

def query_db(query):
    """Execute a SQL query and return the result as a Pandas DataFrame."""
    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

if __name__ == "__main__":
    # Test connection
    try:
        conn = get_connection()
        print("Connection successful!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
