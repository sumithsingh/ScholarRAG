# database/connector.py

import os
import psycopg2
from datetime import datetime
from typing import Optional

# Define a type hint for clarity
Psycopg2Connection = 'psycopg2.extensions.connection'

def get_db_connection() -> Optional[Psycopg2Connection]:
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initializes the database by creating the monitoring table if it doesn't exist."""
    conn = get_db_connection()
    if conn is None:
        print("Could not initialize database. Connection failed.")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_monitoring (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    answer TEXT,
                    sources TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        print("Database initialized successfully. 'rag_monitoring' table is ready.")
    except psycopg2.Error as e:
        print(f"Error during database initialization: {e}")
    finally:
        if conn:
            conn.close()

def log_interaction(query: str, answer: str, sources: str):
    """Logs a user interaction to the database."""
    conn = get_db_connection()
    if conn is None:
        print("Could not log to database. Connection failed.")
        return

    sql = """
        INSERT INTO rag_monitoring (query, answer, sources, timestamp)
        VALUES (%s, %s, %s, %s);
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (query, answer, sources, datetime.now()))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error logging to database: {e}")
    finally:
        if conn:
            conn.close()