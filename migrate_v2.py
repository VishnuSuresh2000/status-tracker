import sqlite3
import os

DB_PATH = '/app/data/tasks.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Migrating tasks table...")
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN agent_name VARCHAR DEFAULT 'Main Agent'")
            print("- Added agent_name to tasks")
        except sqlite3.OperationalError as e:
            print(f"- agent_name: {e}")

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN skills VARCHAR")
            print("- Added skills to tasks")
        except sqlite3.OperationalError as e:
            print(f"- skills: {e}")

        print("Migrating phases table...")
        try:
            cursor.execute("ALTER TABLE phases ADD COLUMN description VARCHAR")
            print("- Added description to phases")
        except sqlite3.OperationalError as e:
            print(f"- phases description: {e}")

        print("Migrating todos table...")
        try:
            cursor.execute("ALTER TABLE todos ADD COLUMN description VARCHAR")
            print("- Added description to todos")
        except sqlite3.OperationalError as e:
            print(f"- todos description: {e}")
        
        conn.commit()
        print("Migration successful!")
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()