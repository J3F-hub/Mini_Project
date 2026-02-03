from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'it_helpdesk_secret_key'

# โฟลเดอร์เก็บรูปสลิป
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('maintenance.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
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
    
    # ดึงข้อมูลมาทั้งหมด
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
    conn.close()

    active_repairs = [r for r in all_repairs if r['status'] != 'Completed']
    completed_repairs = [r for r in all_repairs if r['status'] == 'Completed']
    
    return render_template('homepage.html', 
                           name=session['fullname'], 
                           role=session['role'], 
                           active_repairs=active_repairs, 
                           completed_repairs=completed_repairs)

# แจ้งซ่อม (บันทึกชื่อผู้ส่ง)
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        reporter_name = request.form['reporter_name']
        device_name = request.form['device_name']
        problem_detail = request.form['problem_detail']
        location = request.form['location']
        conn = get_db_connection()
        conn.execute('''INSERT INTO repairs (user_id, reporter_name, device_name, problem_detail, location) 
                        VALUES (?, ?, ?, ?, ?)''',
                     (session['user_id'], reporter_name, device_name, problem_detail, location))
        conn.commit()
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

# --- ระบบชำระเงิน (แก้ใหม่: อัปโหลดแล้วเป็น Paid เลย) ---
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
            
            # แก้ตรงนี้: เปลี่ยนสถานะเป็น 'Paid' ทันที
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