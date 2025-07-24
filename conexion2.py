import os
from dotenv import load_dotenv
import pyodbc

load_dotenv()

def conectarsql():
    try:
        driver = os.getenv("DB_DRIVER", "SQL Server")
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_NAME")
        trusted = os.getenv("DB_TRUSTED", "yes")

        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection={trusted};"

        conn = pyodbc.connect(conn_str)
        print("✅ Conexión exitosa a SQL Server")
        return conn

    except pyodbc.Error as e:
        print("❌ Error al conectar a SQL Server:", e)
        return None
    