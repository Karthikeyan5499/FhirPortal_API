import pyodbc
from app.config import settings

def get_connection():
    conn_str = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={settings.DB_SERVER};"
        f"Database={settings.DB_NAME};"
        f"UID={settings.DB_USERNAME};"
        f"PWD={settings.DB_PASSWORD};"
    )
    return pyodbc.connect(conn_str)
