import os
import base64
from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'it_helpdesk_secret_key'

# ดึง URL ฐานข้อมูลจาก Render (ถ้าไม่มีจะพยายามใช้ SQLite แต่มันจะไม่ถาวรนะ)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def initialize_database():
    """สร้างตารางใน PostgreSQL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. ตาราง Users (ใช้ SERIAL แทน AUTOINCREMENT)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
        ''')

        # 2. ตาราง Repairs (เปลี่ยน payment_slip เป็น TEXT เพื่อเก็บ Base64)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            repair_id SERIAL PRIMARY KEY,
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
        );
        ''')

        # 3. ตาราง Evaluations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            eval_id SERIAL PRIMARY KEY,
            repair_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            FOREIGN KEY (repair_id) REFERENCES repairs (repair_id)
        );
        ''')
        
        # สร้าง Admin และ Student ถ้ายังไม่มี
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()['count'] == 0:
            print("🌱 Creating initial users...")
            cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (%s, %s, %s, %s)",
                           ('admin', '1234', 'Admin (ช่างเทคนิค)', 'admin'))
            cursor.execute("INSERT INTO users (username, password, fullname, role) VALUES (%s, %s, %s, %s)",
                           ('student', '1234', 'Student (นักศึกษา)', 'user'))
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully on PostgreSQL!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

# รันฟังก์ชันสร้างตารางทันที
if DATABASE_URL:
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
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user and user['password'] == password:
                session['user_id'] = user['user_id']
                session['fullname'] = user['fullname']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="รหัสผ่านผิด")
        except Exception as e:
            return f"Database Connection Error: {e}"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session['role'] == 'admin':
        cursor.execute('''
            SELECT r.*, e.rating, e.comment
            FROM repairs r 
            LEFT JOIN evaluations e ON r.repair_id = e.repair_id
            ORDER BY r.report_date DESC
        ''')
    else:
        cursor.execute('''
            SELECT r.*, e.rating, e.comment
            FROM repairs r 
            LEFT JOIN evaluations e ON r.repair_id = e.repair_id
            WHERE r.user_id = %s
            ORDER BY r.report_date DESC
        ''', (session['user_id'],))
        
    all_repairs = cursor.fetchall()
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
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO repairs (user_id, reporter_name, device_name, problem_detail, location) 
                        VALUES (%s, %s, %s, %s, %s)''',
                     (session['user_id'], reporter_name, device_name, problem_detail, location))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/update/<int:repair_id>', methods=['GET', 'POST'])
def update_repair(repair_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        status = request.form['status']
        technician_note = request.form['technician_note']
        spare_parts = request.form.get('spare_parts', '')
        cost = request.form.get('cost', 0)
        payment_status = request.form.get('payment_status', 'Unpaid')
        if not cost: cost = 0
        
        cursor.execute('''UPDATE repairs SET status=%s, technician_note=%s, spare_parts=%s, cost=%s, payment_status=%s 
                        WHERE repair_id=%s''',
                     (status, technician_note, spare_parts, cost, payment_status, repair_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    
    cursor.execute('SELECT * FROM repairs WHERE repair_id = %s', (repair_id,))
    repair = cursor.fetchone()
    conn.close()
    return render_template('update_repair.html', repair=repair)

@app.route('/payment/<int:repair_id>', methods=['GET', 'POST'])
def payment(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        if 'slip' not in request.files: return 'No file part'
        file = request.files['slip']
        if file.filename == '': return 'No selected file'
        
        if file:
            # เทคนิคพิเศษ: แปลงรูปภาพเป็น Text (Base64) เพื่อเก็บใน Database
            # วิธีนี้รูปจะไม่หายเมื่อ Render รีเซ็ต
            image_data = file.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            # ใส่ prefix ให้ browser รู้ว่าเป็นรูป
            mime_type = file.mimetype
            db_image_string = f"data:{mime_type};base64,{encoded_image}"

            cursor.execute("UPDATE repairs SET payment_slip = %s, payment_status = 'Paid' WHERE repair_id = %s", 
                         (db_image_string, repair_id))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))

    cursor.execute('SELECT * FROM repairs WHERE repair_id = %s', (repair_id,))
    repair = cursor.fetchone()
    conn.close()
    return render_template('payment.html', repair=repair)

@app.route('/evaluate/<int:repair_id>', methods=['GET', 'POST'])
def evaluate(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        cursor.execute('INSERT INTO evaluations (repair_id, rating, comment) VALUES (%s, %s, %s)', 
                     (repair_id, rating, comment))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    
    cursor.execute('SELECT * FROM repairs WHERE repair_id = %s', (repair_id,))
    repair = cursor.fetchone()
    conn.close()
    return render_template('evaluate.html', repair=repair)

@app.route('/delete/<int:repair_id>')
def delete_repair(repair_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session['role'] == 'admin':
        cursor.execute('DELETE FROM evaluations WHERE repair_id = %s', (repair_id,))
        cursor.execute('DELETE FROM repairs WHERE repair_id = %s', (repair_id,))
        conn.commit()
    else:
        cursor.execute('SELECT * FROM repairs WHERE repair_id = %s AND user_id = %s', 
                             (repair_id, session['user_id']))
        check = cursor.fetchone()
        if check and check['status'] == 'Pending':
            cursor.execute('DELETE FROM repairs WHERE repair_id = %s', (repair_id,))
            conn.commit()
            
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)