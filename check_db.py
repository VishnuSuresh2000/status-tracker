import sqlite3
conn = sqlite3.connect('/app/data/tasks.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(todos);")
print(cursor.fetchall())
conn.close()