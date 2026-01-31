import sqlite3
import os

db_name = "maintenance.db"

# ลบของเก่าทิ้งเพื่อเริ่มใหม่แบบสะอาด (Clean Start)
if os.path.exists(db_name):
    os.remove(db_name)
    print(f"🗑️ ลบฐานข้อมูลเก่า {db_name} แล้ว...")

conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# 1. สร้างตาราง Users
cursor.execute('''
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    fullname TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
)
''')

# 2. สร้างตาราง Repairs (เพิ่ม spare_parts และ cost ให้แล้ว)
cursor.execute('''
CREATE TABLE repairs (
    repair_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    device_name TEXT NOT NULL,
    problem_detail TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    technician_note TEXT,
    spare_parts TEXT, 
    cost INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)
''')

# 3. สร้างตาราง Evaluations
cursor.execute('''
CREATE TABLE evaluations (
    eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repair_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    FOREIGN KEY (repair_id) REFERENCES repairs (repair_id)
)
''')

# เพิ่ม User และ Admin สำหรับทดสอบ
users = [
    ('admin', '1234', 'Admin (ช่างเทคนิค)', 'admin'),
    ('student', '1234', 'Student (นักศึกษา)', 'user')
]
cursor.executemany("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)", users)

conn.commit()
conn.close()
print("✅ สร้างฐานข้อมูลใหม่สำเร็จ! (พร้อมใช้งาน)")