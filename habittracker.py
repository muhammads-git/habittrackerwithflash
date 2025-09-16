import time
from datetime import datetime, timedelta
from flask import Flask, url_for, redirect, render_template, request, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm, addHabitForm
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os

# Load variables from .env
load_dotenv()

app = Flask(__name__)

# Configure Flask and DB 
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')
app.config['SECRET_KEY'] = os.getenv('APP_SECURITY')

mysql = MySQL(app)
bcrypt = Bcrypt(app)

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'sirhammad760@gmail.com'
app.config['MAIL_PASSWORD'] = 'mhfg dbby bcrd eqty'
app.config['MAIL_DEFAULT_SENDER'] = 'sirhammad760@gmail.com'
mail = Mail(app)


# Dashboard
@app.route('/')
def base():
    form = RegisterForm()
    return render_template('register.html', form=form)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data

        # Hash password
        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO user_login (username,password,email) VALUES (%s,%s,%s)',
            (username, hashed_pass, email)
        )
        mysql.connection.commit()
        cursor.close()

        flash('Registration successful', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user_login WHERE username=%s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if 'tries' not in session:
            session['tries'] = 0

        if user:
            hashed_pass = user['password']
            if bcrypt.check_password_hash(hashed_pass, password):
                session['tries'] = 0
                session['username'] = user['username']
                session['user_id'] = user['id']
                flash('Login successful', 'success')
                return redirect(url_for('add_habits'))
            else:
                session['tries'] += 1
                if session['tries'] >= 3:
                    session['lock_time'] = time.time()
                    return redirect(url_for('blocktime'))
                else:
                    flash('Incorrect password', 'danger')
                    return redirect(url_for('login'))

        flash('No user found', 'warning')
        return redirect(url_for('register'))

    return render_template('login.html', form=form)


@app.route('/blocktime')
def blocktime():
    lock_time = session.get('lock_time')
    if not lock_time:
        return redirect(url_for('login'))

    now = time.time()
    elapsed = now - lock_time
    wait_sec = 120

    if elapsed >= wait_sec:
        session['tries'] = 0
        session.pop('lock_time', None)
        return redirect(url_for('login'))

    remaining = int(wait_sec - elapsed)
    return render_template('time.html', remaining=remaining)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('login'))


@app.route('/add_habits', methods=['POST', 'GET'])
def add_habits():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    form = addHabitForm()
    if form.validate_on_submit():
        habits = form.myhabit.data.capitalize()
        its_frequency = form.habit_frequency.data.upper()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'INSERT INTO habits (user_id,habit_name,frequency) VALUES (%s,%s,%s)',
            (session['user_id'], habits, its_frequency)
        )
        last_habit_id = cursor.lastrowid

        current_date = datetime.today()
        cursor.execute(
            'INSERT INTO habit_logs (user_id,habit_id,log_date) VALUES (%s,%s,%s)',
            (session['user_id'], last_habit_id, current_date)
        )
        mysql.connection.commit()
        cursor.close()

        flash('Task added successfully.', "success")
        return redirect(url_for('show_habits'))

    return render_template('add_habits.html', form=form)


def calculate_streaks(logs):
    streak = 0
    today = datetime.today().date()

    for log in logs:
        log_date = log['log_date']
        status = log['status']

        if log_date == today - timedelta(days=streak) and status == 'done':
            streak += 1
        else:
            break
    return streak


@app.route('/show_habits', methods=['GET'])
def show_habits():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'SELECT id,habit_name,frequency,status FROM habits WHERE user_id = %s',
        (session['user_id'],)
    )
    habits = cursor.fetchall()

    for habit in habits:
        habit_id = habit['id']
        cursor.execute(
            'SELECT log_date, status FROM habit_logs WHERE habit_id = %s ORDER BY log_date DESC',
            (habit_id,)
        )
        logs = cursor.fetchall()

        # calculate streak
        habit['streak'] = calculate_streaks(logs)

        # ✅ calculate progress as a percentage of 30 days
        streak = habit['streak'] or 0
        habit['progress'] = int((streak / 30) * 100)

    cursor.close()
    return render_template('show_habits.html',my_data=habits,username=session.get('username'))



@app.route('/mark_done/<int:id>', methods=['POST'])
def mark_done(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(
        'UPDATE habits SET status="done" WHERE id=%s AND user_id=%s',
        (id, session['user_id'])
    )

    current_date = datetime.today()
    cursor.execute(
        """INSERT INTO habit_logs (user_id,habit_id,log_date,status) 
           VALUES (%s,%s,%s,'done') 
           ON DUPLICATE KEY UPDATE status ='done'""",
        (session['user_id'], id, current_date)
    )
    mysql.connection.commit()

    cursor.execute('SELECT email FROM user_login WHERE id=%s', (session['user_id'],))
    my_email = cursor.fetchone()['email']

    cursor.execute('SELECT habit_name FROM habits WHERE id=%s', (id,))
    habit_name = cursor.fetchone()['habit_name']
    cursor.close()

    msg = Message(
        subject='HABIT TRACKER APP',
        recipients=[my_email]
    )
    msg.html = f"""
        <html>
        <body>
            <h2>Habit Tracker ✅</h2>
            <p>Congratulations 🎉 You completed your habit <b>{habit_name}</b> today!</p>
        </body>
        </html>
    """
    mail.send(msg)

    flash('Status Updated', 'success')
    return redirect(url_for('show_habits'))


@app.route('/remove/<int:id>', methods=['POST', 'GET'])
def remove(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM habits WHERE user_id =%s AND id=%s', (session['user_id'], id))
    cursor.execute('DELETE FROM habit_logs WHERE user_id=%s AND habit_id=%s', (session['user_id'], id))
    mysql.connection.commit()
    cursor.close()
    flash('Habit removed successfully', 'success')
    return redirect(url_for('show_habits'))


# Run app
if __name__ == "__main__":
    app.run(debug=True)
