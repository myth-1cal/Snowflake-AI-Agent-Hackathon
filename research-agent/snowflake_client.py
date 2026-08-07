import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

class SnowflakeClient:
    def __init__(self):
        self.conn = None
        self.connection_error = None
        self.table_ready = False
        self._connect()

    def _connect(self):
        try:
            self.conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                database=os.getenv("SNOWFLAKE_DATABASE"),
                schema=os.getenv("SNOWFLAKE_SCHEMA"),
                login_timeout=15,
            )
            self.connection_error = None
            self.table_ready = False
            self._create_table_if_not_exists()
        except Exception as e:
            self.connection_error = str(e)
            self.conn = None
            print(f"Snowflake Connection Failed: {e}")

    def _create_table_if_not_exists(self):
        if not self.conn:
            return
        cursor = self.conn.cursor()
        database = os.getenv("SNOWFLAKE_DATABASE", "")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "")

        try:
            if database and schema:
                cursor.execute(f"USE DATABASE {database}")
                cursor.execute(f"USE SCHEMA {database}.{schema}")

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {database}.{schema}.TOKEN_ECONOMY_LOGS (
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
            self.table_ready = True
        except Exception as e:
            self.connection_error = str(e)
            self.table_ready = False
            print(f"Snowflake Table Setup Warning: {e}")

    def log_usage(self, session_id, query, tokens, latency_ms, memory_enabled=True):
        """Logs usage metrics to Snowflake."""
        if not self.conn or not self.table_ready:
            return

        prompt_tokens = tokens.get("prompt_tokens", 0)
        completion_tokens = tokens.get("completion_tokens", 0)
        total_tokens = tokens.get("total_tokens", prompt_tokens + completion_tokens)
        cost = (prompt_tokens * 0.000000075) + (completion_tokens * 0.00000030)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO TOKEN_ECONOMY_LOGS 
            (session_id, query, prompt_tokens, completion_tokens, total_tokens, latency_ms, memory_enabled, estimated_cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id,
            query[:100],
            prompt_tokens,
            completion_tokens,
            total_tokens,
            latency_ms,
            memory_enabled,
            cost,
        ))
        self.conn.commit()

    def get_comparison_analytics(self):
        if not self.conn:
            return {
                "error": f"Snowflake analytics are unavailable: {self.connection_error or 'Please verify the Snowflake credentials and schema in your .env file.'}",
                "total_queries": 0,
                "avg_tokens_per_query": 0.0,
                "avg_cost_usd": 0.0,
                "total_tokens_saved": 0,
                "baseline_tokens": 0,
                "memory_tokens": 0,
                "baseline_cost": 0.0,
                "memory_cost": 0.0,
                "baseline_queries": 0,
                "memory_queries": 0,
            }

        if not self.table_ready:
            return {
                "error": f"Snowflake analytics table is not ready: {self.connection_error or 'Table setup was skipped.'}",
                "total_queries": 0,
                "avg_tokens_per_query": 0.0,
                "avg_cost_usd": 0.0,
                "total_tokens_saved": 0,
                "baseline_tokens": 0,
                "memory_tokens": 0,
                "baseline_cost": 0.0,
                "memory_cost": 0.0,
                "baseline_queries": 0,
                "memory_queries": 0,
            }

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total_queries,
                AVG(total_tokens) AS avg_tokens_per_query,
                AVG(estimated_cost_usd) AS avg_cost_usd,
                SUM(CASE WHEN memory_enabled THEN total_tokens ELSE 0 END) AS memory_tokens,
                SUM(CASE WHEN NOT memory_enabled THEN total_tokens ELSE 0 END) AS baseline_tokens,
                SUM(CASE WHEN memory_enabled THEN estimated_cost_usd ELSE 0 END) AS memory_cost,
                SUM(CASE WHEN NOT memory_enabled THEN estimated_cost_usd ELSE 0 END) AS baseline_cost,
                SUM(CASE WHEN memory_enabled THEN 1 ELSE 0 END) AS memory_queries,
                SUM(CASE WHEN NOT memory_enabled THEN 1 ELSE 0 END) AS baseline_queries
            FROM TOKEN_ECONOMY_LOGS
        """)
        row = cursor.fetchone()
        if not row:
            row = (0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0, 0)

        total_queries, avg_tokens_per_query, avg_cost_usd, memory_tokens, baseline_tokens, memory_cost, baseline_cost, memory_queries, baseline_queries = row
        total_tokens_saved = max(0, int(baseline_tokens or 0) - int(memory_tokens or 0))

        return {
            "total_queries": int(total_queries or 0),
            "avg_tokens_per_query": float(avg_tokens_per_query or 0.0),
            "avg_cost_usd": float(avg_cost_usd or 0.0),
            "total_tokens_saved": int(total_tokens_saved),
            "baseline_tokens": int(baseline_tokens or 0),
            "memory_tokens": int(memory_tokens or 0),
            "baseline_cost": float(baseline_cost or 0.0),
            "memory_cost": float(memory_cost or 0.0),
            "baseline_queries": int(baseline_queries or 0),
            "memory_queries": int(memory_queries or 0),
        }
