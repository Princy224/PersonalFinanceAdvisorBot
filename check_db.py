

import sqlite3

conn = sqlite3.connect("finance.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table in tables:
    name = table[0]
    print("\nTABLE:", name)

    if name == "transactions":
        cursor.execute("PRAGMA table_info(transactions)")
        print("Columns:", cursor.fetchall())

        cursor.execute("SELECT * FROM transactions")
        print("Transaction Data:", cursor.fetchall())

conn.close()


