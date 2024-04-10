import sqlite3
import string
import random
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "b_5#y762u7y21wqL'F4Q8z98,fun9xeytc]/"

paused_time = 0
start_time = None
timer_running = False


conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id))''')

conn.commit()

conn.close()

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        cursor = sqlite3.connect('database.db', check_same_thread=False).cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_record = cursor.fetchone()
        if user_record:
            return User(user_record[0], user_record[1], user_record[2])
        else:
            return None

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_record = cursor.fetchone()
        conn.close()
        if user_record and check_password_hash(user_record[2], password):
            user = User(user_record[0], user_record[1], user_record[2])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
        conn.commit()
        conn.close()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/protected')
@login_required
def protected():
    return 'This is a protected page'

def custom_enumerate(sequence, start=0):
    return zip(range(start, start + len(sequence)), sequence)

app.jinja_env.globals.update(enumerate=custom_enumerate)

tasks = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/task_list', methods=['GET', 'POST'])
@login_required
def task_list():
    if request.method == 'POST':
        task = request.form['task']
        tasks.append(task)
        return redirect(url_for('task_list'))
    return render_template('tasks.html', tasks=tasks)

@app.route('/delete_task/<int:task_index>', methods=['POST'])
@login_required
def delete_task(task_index):
    if task_index < len(tasks):
        del tasks[task_index]
    return redirect(request.referrer or url_for('index'))

@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn = sqlite3.connect('database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", (current_user.id, title, content))
        conn.commit()
        conn.close()
        flash('Note added successfully', 'success')
        return redirect(url_for('notes'))
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE user_id = ?", (current_user.id,))
    user_notes = cursor.fetchall()
    conn.close()
    return render_template('notes.html', user_notes=user_notes)


@app.route('/stopwatch', methods=['GET', 'POST'])
def stopwatch():
    global paused_time
    global start_time
    global timer_running

    if request.method == 'POST':
        action = request.form['action']

        if action == 'start':
            start_time = time.time() - paused_time
            timer_running = True
        elif action == 'pause':
            paused_time = time.time() - start_time
            timer_running = False
        elif action == 'stop':
            start_time = None
            paused_time = 0
            timer_running = False

    if start_time is not None and timer_running:
        elapsed_time = time.time() - start_time
    else:
        elapsed_time = paused_time

    return render_template('stopwatch.html', elapsed_time=elapsed_time, timer_running=timer_running)


@app.route('/calculate', methods=['GET', 'POST'])
def calculate():
    if request.method == 'POST':
        try:
            num1 = float(request.form['num1'])
            num2 = float(request.form['num2'])
            operation = request.form['operation']
        except ValueError:
            return "Please enter valid numbers."

        if operation == 'add':
            result = num1 + num2
        elif operation == 'subtract':
            result = num1 - num2
        elif operation == 'multiply':
            result = num1 * num2
        elif operation == 'divide':
            if num2 == 0:
                return "Division by zero is not possible."
            else:
                result = num1 / num2

        formatted_result = "{:.2f}".format(result) if result % 1 else str(int(result))

        return render_template('result.html', result=formatted_result)
    else:
        return render_template('calculator.html')


@app.route('/timer', methods=['GET', 'POST'])
def timer():
    if request.method == 'POST':
        if 'start' in request.form:
            session['start_time'] = time.time()
            return redirect(url_for('timer'))
        elif 'pause' in request.form:
            session['elapsed_time'] = session.get('elapsed_time', 0) + (time.time() - session.get('start_time', time.time()))
            session.pop('start_time', None)
            return redirect(url_for('timer'))
        elif 'reset' in request.form:
            session.pop('start_time', None)
            session.pop('elapsed_time', None)
            return redirect(url_for('timer'))
    elif 'start_time' in session:
        elapsed_time = session.get('elapsed_time', 0) + (time.time() - session.get('start_time', time.time()))
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time - int(elapsed_time)) * 1000)
        return render_template('timer.html', running=True, hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)
    return render_template('timer.html', running=False)


def generate_password(length, include_digits, include_uppercase, include_special):
    chars = string.ascii_lowercase
    if include_digits:
        chars += string.digits
    if include_uppercase:
        chars += string.ascii_uppercase
    if include_special:
        chars += '!@#%&?*'
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/password_generator', methods=['GET', 'POST'])
def password_generator():
    if request.method == 'POST':
        length = int(request.form['length'])
        include_digits = request.form.get('include_digits', False)
        include_uppercase = request.form.get('include_uppercase', False)
        include_special = request.form.get('include_special', False)
        password = generate_password(length, include_digits, include_uppercase, include_special)
        return render_template('password_generator.html', password=password)
    return render_template('password_generator.html')


if __name__ == '__main__':
    app.run(debug=True)
