import sqlite3

def upgrade_database():
    conn = sqlite3.connect('maintenance.db')
    cursor = conn.cursor()

    try:
        # 1. เพิ่มคอลัมน์ spare_parts (ชื่ออะไหล่)
        cursor.execute("ALTER TABLE repairs ADD COLUMN spare_parts TEXT")
        print("✅ เพิ่มคอลัมน์ spare_parts สำเร็จ")
    except sqlite3.OperationalError:
        print("⚠️ คอลัมน์ spare_parts มีอยู่แล้ว")

    try:
        # 2. เพิ่มคอลัมน์ cost (ค่าใช้จ่าย)
        cursor.execute("ALTER TABLE repairs ADD COLUMN cost INTEGER DEFAULT 0")
        print("✅ เพิ่มคอลัมน์ cost สำเร็จ")
    except sqlite3.OperationalError:
        print("⚠️ คอลัมน์ cost มีอยู่แล้ว")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade_database()