"""Database Manager for MySQL.

Manages connection pooling, schema initialization, transactional scopes,
and schema introspection for the DBMS Explorer.
"""

import os
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple

import mysql.connector
from mysql.connector import errorcode

from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_DIR

class DatabaseManager:
    """Manages connections and schema operations for MySQL."""

    def __init__(
        self,
        host: str = DB_HOST,
        port: int = DB_PORT,
        database: str = DB_NAME,
        user: str = DB_USER,
        password: str = DB_PASSWORD
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def get_connection(self, include_db: bool = True) -> mysql.connector.MySQLConnection:
        """Create and return a raw MySQL connection.
        
        Args:
            include_db: If True, connects directly to target database DB_NAME.
        """
        config = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "connection_timeout": 5,
            "autocommit": False
        }
        if include_db:
            config["database"] = self.database

        return mysql.connector.connect(**config)

    @contextmanager
    def cursor_scope(self, dictionary: bool = True):
        """Context manager for safe transactional database operations."""
        conn = None
        try:
            conn = self.get_connection(include_db=True)
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to MySQL Server and target database."""
        try:
            # Check server connection first
            server_conn = self.get_connection(include_db=False)
            server_version = getattr(server_conn, "server_info", "8.0")
            server_conn.close()

            # Check specific database
            has_db = False
            try:
                db_conn = self.get_connection(include_db=True)
                has_db = True
                db_conn.close()
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_BAD_DB_ERROR:
                    has_db = False
                else:
                    raise

            return {
                "success": True,
                "server_version": server_version,
                "host": f"{self.host}:{self.port}",
                "user": self.user,
                "database_exists": has_db,
                "database_name": self.database,
                "message": (
                    f"Successfully connected to MySQL Server {server_version}. "
                    f"Database '{self.database}' {'exists and is accessible' if has_db else 'does not exist yet (run Schema Init)'}."
                )
            }
        except mysql.connector.Error as err:
            return {
                "success": False,
                "error_code": err.errno,
                "error_message": err.msg,
                "message": f"MySQL Connection Error [{err.errno}]: {err.msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e),
                "message": f"Connection Error: {e}"
            }

    def init_database_and_schema(self, schema_file: Optional[str] = None) -> Dict[str, Any]:
        """Create database if missing, then execute schema.sql statements."""
        schema_path = schema_file or str(DATABASE_DIR / "schema.sql")
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found at {schema_path}")

        try:
            # 1. Connect without database and create database if missing
            server_conn = self.get_connection(include_db=False)
            server_cursor = server_conn.cursor()
            server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4;")
            server_conn.commit()
            server_cursor.close()
            server_conn.close()

            # 2. Read schema file
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # Strip comments line by line
            clean_lines = [line for line in schema_sql.splitlines() if not line.strip().startswith("--")]
            clean_sql = "\n".join(clean_lines)

            # Split statements by semicolon
            statements = [stmt.strip() for stmt in clean_sql.split(";") if stmt.strip()]

            # 3. Connect to database and execute statements
            db_conn = self.get_connection(include_db=True)
            db_cursor = db_conn.cursor()
            executed_count = 0

            for stmt in statements:
                if stmt:
                    db_cursor.execute(stmt)
                    executed_count += 1

            db_conn.commit()
            db_cursor.close()
            db_conn.close()

            return {
                "success": True,
                "database": self.database,
                "statements_executed": executed_count,
                "message": f"Successfully initialized database '{self.database}' with {executed_count} schema statements."
            }
        except mysql.connector.Error as err:
            return {
                "success": False,
                "error_code": err.errno,
                "error_message": err.msg,
                "message": f"Schema Initialization Failed: {err.msg}"
            }

    def get_tables(self) -> List[str]:
        """Return list of all project tables in the database."""
        try:
            with self.cursor_scope(dictionary=False) as cursor:
                cursor.execute("SHOW TABLES;")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception:
            return []

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Return schema structure and column definitions for a table."""
        try:
            with self.cursor_scope(dictionary=True) as cursor:
                query = """
                    SELECT 
                        COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, 
                        COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION;
                """
                cursor.execute(query, (self.database, table_name))
                return cursor.fetchall()
        except Exception:
            return []

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Return foreign key constraints for a table."""
        try:
            with self.cursor_scope(dictionary=True) as cursor:
                query = """
                    SELECT 
                        CONSTRAINT_NAME, COLUMN_NAME,
                        REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                      AND REFERENCED_TABLE_NAME IS NOT NULL;
                """
                cursor.execute(query, (self.database, table_name))
                return cursor.fetchall()
        except Exception:
            return []

    def get_row_counts(self) -> Dict[str, int]:
        """Return current row count for every table."""
        counts = {}
        tables = self.get_tables()
        for t in tables:
            try:
                with self.cursor_scope(dictionary=False) as cursor:
                    # Table name safely validated against get_tables() list
                    cursor.execute(f"SELECT COUNT(*) FROM `{t}`;")
                    counts[t] = cursor.fetchone()[0]
            except Exception:
                counts[t] = 0
        return counts

    def get_table_rows(self, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch rows from a table with pagination."""
        tables = self.get_tables()
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' does not exist in database '{self.database}'.")

        with self.cursor_scope(dictionary=True) as cursor:
            # Query table safely
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s;", (limit, offset))
            return cursor.fetchall()
