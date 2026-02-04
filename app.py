from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'it_helpdesk_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- ระบบจัดการฐานข้อมูล (Database Manager) ---
def get_db_connection():
    conn = sqlite3.connect('maintenance.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """ สร้างตารางใหม่ถ้ายังไม่มี หรือถ้าไฟล์หายไป """
    conn = sqlite3.connect('maintenance.db')
    cursor = conn.cursor()
    
    # 1. ตาราง Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    ''')

    # 2. ตาราง Repairs (เวอร์ชันครบ: มี reporter_name, payment_status, payment_slip)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS repairs (
        repair_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reporter_name TEXT, 
        device_name TEXT NOT NULL,
        problem_detail TEXT NOT NULL,
        location TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        technician_note TEXT,
        spare_parts TEXT,
        cost INTEGER DEFAULT 0,
        payment_status TEXT DEFAULT 'Unpaid',
        payment_slip TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # 3. ตาราง Evaluations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        repair_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        FOREIGN KEY (repair_id) REFERENCES repairs (repair_id)
    )
    ''')
    
    # ตรวจสอบว่ามี Admin หรือยัง ถ้าไม่มีให้เพิ่ม
    try:
        check_admin = cursor.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        if not check_admin:
            # เพิ่ม Admin
            cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)",
                           ('admin', '1234', 'Admin (ช่างเทคนิค)', 'admin'))
            # เพิ่ม User นักศึกษา
            cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)",
                           ('student', '1234', 'Student (นักศึกษา)', 'user'))
            print("✅ สร้างบัญชี Admin และ Student เรียบร้อยแล้ว")
    except Exception as e:
        print(f"⚠️ Error creating users: {e}")

    conn.commit()
    conn.close()

# สั่งให้ทำงานทันทีเมื่อรันไฟล์
initialize_database()

# ----------------------------------------------------

@app.route('/')
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == password:
            session['user_id'] = user['user_id']
            session['fullname'] = user['fullname']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="รหัสผ่านผิด")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    
    # ใช้ try-except ป้องกันกรณี Column หาย (Database เก่า)
    try:
        if session['role'] == 'admin':
            all_repairs = conn.execute('''
                SELECT r.*, e.rating, e.comment
                FROM repairs r 
                LEFT JOIN evaluations e ON r.repair_id = e.repair_id
                ORDER BY r.report_date DESC
            ''').fetchall()
        else:
            all_repairs = conn.execute('''
                SELECT r.*, e.rating, e.comment
                FROM repairs r 
                LEFT JOIN evaluations e ON r.repair_id = e.repair_id
                WHERE r.user_id = ?
                ORDER BY r.report_date DESC
            ''', (session['user_id'],)).fetchall()
    except sqlite3.OperationalError:
        # ถ้า Database พัง ให้ส่งกลับเป็นลิสต์ว่างๆ ดีกว่า Error หน้าขาว
        all_repairs = []
        print("⚠️ Database Error: Column missing. Please reset database.")
        
    conn.close()

    active_repairs = [r for r in all_repairs if r['status'] != 'Completed']
    completed_repairs = [r for r in all_repairs if r['status'] == 'Completed']
    
    return render_template('homepage.html', 
                           name=session['fullname'], 
                           role=session['role'], 
                           active_repairs=active_repairs, 
                           completed_repairs=completed_repairs)

@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        reporter_name = request.form['reporter_name']
        device_name = request.form['device_name']
        problem_detail = request.form['problem_detail']
        location = request.form['location']
        conn = get_db_connection()
        
        # จุดที่มักจะ Error ถ้า DB เก่า
        try:
            conn.execute('''INSERT INTO repairs (user_id, reporter_name, device_name, problem_detail, location) 
                            VALUES (?, ?, ?, ?, ?)''',
                        (session['user_id'], reporter_name, device_name, problem_detail, location))
            conn.commit()
        except sqlite3.OperationalError as e:
            return f"<h1>Error: ฐานข้อมูลเก่าเกินไป</h1><p>กรุณาติดต่อ Admin ให้รีเซ็ตระบบ หรือทำตามวิธีแก้ใน Start Command ({e})</p>"
            
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/update/<int:repair_id>', methods=['GET', 'POST'])
def update_repair(repair_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        status = request.form['status']
        technician_note = request.form['technician_note']
        spare_parts = request.form.get('spare_parts', '')
        cost = request.form.get('cost', 0)
        payment_status = request.form.get('payment_status', 'Unpaid')
        if not cost: cost = 0
        conn.execute('''UPDATE repairs SET status=?, technician_note=?, spare_parts=?, cost=?, payment_status=? 
                        WHERE repair_id=?''',
                     (status, technician_note, spare_parts, cost, payment_status, repair_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    repair = conn.execute('SELECT * FROM repairs WHERE repair_id = ?', (repair_id,)).fetchone()
    conn.close()
    return render_template('update_repair.html', repair=repair)

@app.route('/payment/<int:repair_id>', methods=['GET', 'POST'])
def payment(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        if 'slip' not in request.files: return 'No file part'
        file = request.files['slip']
        if file.filename == '': return 'No selected file'
        if file:
            filename = secure_filename(f"slip_{repair_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE repairs SET payment_slip = ?, payment_status = 'Paid' WHERE repair_id = ?", 
                         (filename, repair_id))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
    repair = conn.execute('SELECT * FROM repairs WHERE repair_id = ?', (repair_id,)).fetchone()
    conn.close()
    return render_template('payment.html', repair=repair)

@app.route('/evaluate/<int:repair_id>', methods=['GET', 'POST'])
def evaluate(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        conn.execute('INSERT INTO evaluations (repair_id, rating, comment) VALUES (?, ?, ?)', 
                     (repair_id, rating, comment))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    repair = conn.execute('SELECT * FROM repairs WHERE repair_id = ?', (repair_id,)).fetchone()
    conn.close()
    return render_template('evaluate.html', repair=repair)

@app.route('/delete/<int:repair_id>')
def delete_repair(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if session['role'] == 'admin':
        conn.execute('DELETE FROM evaluations WHERE repair_id = ?', (repair_id,))
        conn.execute('DELETE FROM repairs WHERE repair_id = ?', (repair_id,))
        conn.commit()
    else:
        check = conn.execute('SELECT * FROM repairs WHERE repair_id = ? AND user_id = ?', 
                             (repair_id, session['user_id'])).fetchone()
        if check and check['status'] == 'Pending':
            conn.execute('DELETE FROM repairs WHERE repair_id = ?', (repair_id,))
            conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)