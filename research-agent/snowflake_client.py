import os
import snowflake.connector
import time
from dotenv import load_dotenv

load_dotenv()

class SnowflakeClient:
    def __init__(self):
        try:
            self.conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                database=os.getenv("SNOWFLAKE_DATABASE"),
                schema=os.getenv("SNOWFLAKE_SCHEMA")
            )
            self._create_table_if_not_exists()
        except Exception as e:
            print(f"Snowflake Connection Failed: {e}")
            self.conn = None

    def _create_table_if_not_exists(self):
        if not self.conn: return
        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS TOKEN_ECONOMY_LOGS (
                timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                session_id STRING,
                query STRING,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms FLOAT,
                memory_enabled BOOLEAN,
                estimated_cost_usd FLOAT
            )
        """)
        self.conn.commit()

    def log_usage(self, session_id, query, tokens, latency_ms, memory_enabled=True):
        """Logs usage metrics to Snowflake."""
        if not self.conn: return
        
        # Price estimate for Gemini 1.5 Flash (approximate)
        # $0.075 / 1M input tokens, $0.30 / 1M output tokens
        cost = (tokens['prompt_tokens'] * 0.000000075) + (tokens['completion_tokens'] * 0.00000030)
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
            INSERT INTO TOKEN_ECONOMY_LOGS 
            (session_id, query, prompt_tokens, completion_tokens, total_tokens, latency_ms, memory_enabled, estimated_cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id, 
            query[:100], # Truncate for log
            tokens['prompt_tokens'], 
            tokens['completion_tokens'], 
            tokens['total_tokens'], 
            latency_ms, 
            memory_enabled, 
            cost
        ))
        self.conn.commit()
