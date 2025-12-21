import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="NewPassword123!",
    database="expense_tracker"
)

if conn.is_connected():
    print("Connected to MySQL successfully!")

conn.close()
