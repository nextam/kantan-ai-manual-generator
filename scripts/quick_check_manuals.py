import sqlite3
conn = sqlite3.connect(r'instance\manual_generator.db')
cursor = conn.cursor()
cursor.execute("SELECT id, title, generation_status, created_at FROM manuals WHERE id >= 20 ORDER BY id DESC")
for row in cursor.fetchall():
    print(f"ID: {row[0]} | Title: {row[1]} | Status: {row[2]} | Created: {row[3]}")
conn.close()
