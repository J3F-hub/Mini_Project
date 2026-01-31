import sqlite3
import os

# ลบฐานข้อมูลเก่าทิ้งก่อนเพื่อความชัวร์
if os.path.exists("maintenance.db"):
    os.remove("maintenance.db")
    print("🗑️ ลบฐานข้อมูลเก่าแล้ว...")

conn = sqlite3.connect('maintenance.db')
cursor = conn.cursor()

# 1. ตาราง Users
cursor.execute('''
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    fullname TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
)
''')

# 2. ตาราง Repairs (รวม Cost และ Spare_parts แล้ว)
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

# 3. ตาราง Evaluations
cursor.execute('''
CREATE TABLE evaluations (
    eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repair_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    FOREIGN KEY (repair_id) REFERENCES repairs (repair_id)
)
''')

# เพิ่มข้อมูลทดสอบ
users = [
    ('admin', '1234', 'Admin (ช่างเทคนิค)', 'admin'),
    ('student', '1234', 'Student (นักศึกษา)', 'user')
]
cursor.executemany("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)", users)

print("✅ สร้างฐานข้อมูลใหม่สำเร็จ! (User: student/1234, Admin: admin/1234)")
conn.commit()
conn.close()