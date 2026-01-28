from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'my_secret_key'

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
            return "รหัสผ่านผิด! <a href='/login'>ลองใหม่</a>"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # ส่งข้อมูลว่างเพื่อกัน error
    return render_template(
        'index.html',
        name=session.get('fullname', 'Local User'),
        role=session.get('role', 'user'),
        active_repairs=[],
        completed_repairs=[]
    )

    conn = get_db_connection()
    if session['role'] == 'admin':
        all_repairs = conn.execute('''
            SELECT r.*, u.fullname, e.rating, e.comment
            FROM repairs r 
            JOIN users u ON r.user_id = u.user_id
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

    active_repairs = []
    completed_repairs = []
    for repair in all_repairs:
        if repair['status'] == 'Completed':
            completed_repairs.append(repair)
        else:
            active_repairs.append(repair)
    
    return render_template('index.html', 
                           name=session['fullname'], 
                           role=session['role'], 
                           active_repairs=active_repairs, 
                           completed_repairs=completed_repairs)

@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        device_name = request.form['device_name']
        problem_detail = request.form['problem_detail']
        location = request.form['location']
        conn = get_db_connection()
        conn.execute('INSERT INTO repairs (user_id, device_name, problem_detail, location) VALUES (?, ?, ?, ?)',
                     (session['user_id'], device_name, problem_detail, location))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/update/<int:repair_id>', methods=['GET', 'POST'])
def update_repair(repair_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        status = request.form['status']
        technician_note = request.form['technician_note']
        spare_parts = request.form.get('spare_parts', '')
        cost = request.form.get('cost', 0)
        if cost == '': cost = 0

        conn.execute('''UPDATE repairs SET status=?, technician_note=?, spare_parts=?, cost=? WHERE repair_id=?''',
                     (status, technician_note, spare_parts, cost, repair_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    repair = conn.execute('SELECT * FROM repairs WHERE repair_id = ?', (repair_id,)).fetchone()
    conn.close()
    return render_template('update_repair.html', repair=repair)

@app.route('/evaluate/<int:repair_id>', methods=['GET', 'POST'])
def evaluate(repair_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        conn.execute('INSERT INTO evaluations (repair_id, rating, comment) VALUES (?, ?, ?)', (repair_id, rating, comment))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    repair = conn.execute('SELECT * FROM repairs WHERE repair_id = ?', (repair_id,)).fetchone()
    conn.close()
    return render_template('evaluate.html', repair=repair)

@app.route('/delete/<int:repair_id>')
def delete_repair(repair_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if session['role'] == 'admin':
        conn.execute('DELETE FROM evaluations WHERE repair_id = ?', (repair_id,))
        conn.execute('DELETE FROM repairs WHERE repair_id = ?', (repair_id,))
        conn.commit()
    else:
        check = conn.execute('SELECT * FROM repairs WHERE repair_id = ? AND user_id = ?', (repair_id, session['user_id'])).fetchone()
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