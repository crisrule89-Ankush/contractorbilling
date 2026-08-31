from database import get_connection

try:
    conn = get_connection()
    print("SQL Server Connected Successfully")
    conn.close()
except Exception as e:
    print("SQL Server Connection Failed")
    print(e)
