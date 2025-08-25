import os
import psycopg2
from datetime import datetime
from typing import Optional, Dict, Any

Psycopg2Connection = 'psycopg2.extensions.connection'

def get_db_connection() -> Optional[Psycopg2Connection]:
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"), host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initializes and upgrades the database schema."""
    conn = get_db_connection()
    if conn is None: return

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
            
            new_columns = {
                "response_time_ms": "INTEGER",
                "sources_found": "INTEGER",
                "docs_retrieved": "INTEGER",
                "is_error": "BOOLEAN DEFAULT FALSE",
                "feedback_score": "SMALLINT"
            }
            
            for col_name, col_type in new_columns.items():
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'rag_monitoring'::regclass AND attname = '{col_name}') THEN
                            ALTER TABLE rag_monitoring ADD COLUMN {col_name} {col_type};
                        END IF;
                    END $$;
                """)
        conn.commit()
        print("Database initialized and schema verified successfully.")
    except psycopg2.Error as e:
        print(f"Error during database initialization: {e}")
    finally:
        if conn: conn.close()

def log_interaction(log_data: Dict[str, Any]) -> Optional[int]:
    """Logs a user interaction and returns the ID of the new record."""
    conn = get_db_connection()
    if conn is None: return None

    # --- THIS IS THE CRITICAL FIX ---
    # This safety check ensures all required dictionary keys exist before the SQL query.
    # If a key is missing from the input, it's added with a default value of None.
    required_keys = [
        "query", "answer", "sources", "response_time_ms", 
        "sources_found", "docs_retrieved", "is_error", "feedback_score"
    ]
    for key in required_keys:
        log_data.setdefault(key, None)
    # --- END OF FIX ---

    sql = """
        INSERT INTO rag_monitoring (
            query, answer, sources, response_time_ms, sources_found, 
            docs_retrieved, is_error, feedback_score, timestamp
        ) VALUES (%(query)s, %(answer)s, %(sources)s, %(response_time_ms)s, 
                  %(sources_found)s, %(docs_retrieved)s, %(is_error)s, 
                  %(feedback_score)s, %(timestamp)s)
        RETURNING id;
    """
    try:
        with conn.cursor() as cur:
            log_data['timestamp'] = datetime.now()
            cur.execute(sql, log_data)
            interaction_id = cur.fetchone()[0]
            conn.commit()
            return interaction_id
    except psycopg2.Error as e:
        print(f"Error logging to database: {e}")
        return None
    finally:
        if conn: conn.close()

def update_feedback(interaction_id: int, score: int):
    """Updates the feedback score for a specific interaction."""
    conn = get_db_connection()
    if conn is None: return

    sql = "UPDATE rag_monitoring SET feedback_score = %s WHERE id = %s;"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (score, interaction_id))
        conn.commit()
        print(f"Updated feedback for interaction ID {interaction_id} with score {score}")
    except psycopg2.Error as e:
        print(f"Error updating feedback: {e}")
    finally:
        if conn: conn.close()