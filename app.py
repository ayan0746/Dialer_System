from flask import Flask, request, render_template, redirect, url_for, send_file
import sqlite3
import pandas as pd
from datetime import datetime
import io

app = Flask(__name__)

DATABASE = 'dialer_system.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            role TEXT
        )''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_name TEXT,
            assigned_to INTEGER,
            status TEXT,
            feedback TEXT,
            updated_at TIMESTAMP,
            FOREIGN KEY(assigned_to) REFERENCES users(id)
        )''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            old_feedback TEXT,
            new_feedback TEXT,
            change_date TIMESTAMP,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )''')
        conn.execute('INSERT OR IGNORE INTO users (username, role) VALUES (?, ?)', ('admin', 'admin'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM leads')
        leads = cur.fetchall()
        cur.execute('SELECT * FROM users WHERE role = "telecaller"')
        telecallers = cur.fetchall()
    return render_template('admin_dashboard.html', leads=leads, telecallers=telecallers)

@app.route('/add_lead', methods=['POST'])
def add_lead():
    lead_name = request.form['lead_name']
    assigned_to = int(request.form['assigned_to'])
    with get_db() as conn:
        conn.execute('INSERT INTO leads (lead_name, assigned_to, status, feedback, updated_at) VALUES (?, ?, ?, ?, ?)', 
                     (lead_name, assigned_to, 'New', '', datetime.now()))
    return redirect(url_for('admin_dashboard'))

@app.route('/update_lead/<int:lead_id>', methods=['POST'])
def update_lead(lead_id):
    new_feedback = request.form['feedback']
    username = request.form['username']
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT feedback FROM leads WHERE id = ?', (lead_id,))
        old_feedback = cur.fetchone()[0]
        conn.execute('UPDATE leads SET feedback = ?, status = ?, updated_at = ? WHERE id = ?', 
                     (new_feedback, 'Updated', datetime.now(), lead_id))
        conn.execute('INSERT INTO feedback_changes (lead_id, old_feedback, new_feedback, change_date) VALUES (?, ?, ?, ?)', 
                     (lead_id, old_feedback, new_feedback, datetime.now()))
    return redirect(url_for('telecaller_dashboard', username=username))

@app.route('/generate_report')
def generate_report():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
        SELECT l.lead_name, l.status, fc.old_feedback, fc.new_feedback, fc.change_date
        FROM feedback_changes fc
        JOIN leads l ON fc.lead_id = l.id
        ''')
        data = cur.fetchall()
        df = pd.DataFrame(data, columns=['Lead Name', 'Status', 'Old Feedback', 'New Feedback', 'Change Date'])
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(output, attachment_filename='feedback_report.xlsx', as_attachment=True)

@app.route('/telecaller')
def telecaller_dashboard():
    username = request.args.get('username')
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE username = ?', (username,))
        user_id = cur.fetchone()[0]
        cur.execute('SELECT * FROM leads WHERE assigned_to = ?', (user_id,))
        leads = cur.fetchall()
    return render_template('telecaller_dashboard.html', leads=leads, username=username)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)