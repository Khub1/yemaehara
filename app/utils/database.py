import pyodbc
from config import DB_CONFIG

def get_connection():
    """Establish a database connection using config"""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_CONFIG['SERVER']};"
        f"DATABASE={DB_CONFIG['DATABASE']};"
        f"UID={DB_CONFIG['USERNAME']};"
        f"PWD={DB_CONFIG['PASSWORD']}"
    )
    return pyodbc.connect(conn_str)
