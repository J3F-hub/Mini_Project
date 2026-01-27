import sqlite3

def create_database():
    conn = sqlite3.connect('maintenance.db')
    cursor = conn.cursor()

    # 1. สร้างตาราง Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    ''')

    # 2. สร้างตาราง Repairs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS repairs (
        repair_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        device_name TEXT NOT NULL,
        problem_detail TEXT NOT NULL,
        location TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        technician_note TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # 3. สร้างตาราง Evaluations (สำหรับเก็บดาว)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        repair_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        FOREIGN KEY (repair_id) REFERENCES repairs (repair_id)
    )
    ''')

    # 4. เพิ่มข้อมูลตัวอย่าง
    try:
        cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)",
                       ('admin', '1234', 'ช่างเทคนิค ประจำศูนย์', 'admin'))
        cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)",
                       ('student', '1234', 'นักเรียน นักศึกษา', 'user'))
        print("✅ เพิ่มข้อมูล Admin และ User เรียบร้อย!")
    except sqlite3.IntegrityError:
        print("⚠️ มีข้อมูลผู้ใช้นี้อยู่แล้ว")

    conn.commit()
    conn.close()
    print("✅ สร้างฐานข้อมูลเสร็จสมบูรณ์!")

if __name__ == '__main__':
    create_database()