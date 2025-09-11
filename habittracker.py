import time
from datetime import datetime
from flask import Flask,url_for,redirect,render_template,request,session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask import flash,get_flashed_messages
from forms import RegisterForm,LoginForm,addHabitForm
from flask_mail import Mail,Message

# .env
from dotenv import load_dotenv
import os
# load variables from .env
load_dotenv()
app = Flask(__name__)  
# configure flask and db 
app.config['MYSQL_HOST']=os.getenv('DB_HOST')
app.config['MYSQL_USER']=os.getenv('DB_USER')
app.config['MYSQL_PASSWORD']=os.getenv('DB_PASSWORD')
app.config['MYSQL_DB']=os.getenv('DB_NAME')
app.config['SECRET_KEY'] =os.getenv('APP_SECURITY')
mysql = MySQL(app)
# hasshing
bcrypt = Bcrypt(app)

# email config with flask app
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'sirhammad760@gmail.com'
app.config['MAIL_PASSWORD'] = 'mhfg dbby bcrd eqty '
app.config['MAIL_DEFAULT_SENDER'] = 'sirhammad760@gmail.com'
mail = Mail(app)


#
@app.route('/')
def base():
    form = RegisterForm()
    return render_template('register.html',form=form)


@app.route('/register',methods=['POST','GET'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        # hash the pass
        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')

        # save into db
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO user_login (username,password,email) VALUES (%s,%s,%s)', (username,hashed_pass,email))
        mysql.connection.commit()
        cursor.close()
        flash('Registration successfull','success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login',methods=['POST','GET'])
def login():
    form= LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # access db
        cursor= mysql.connection.cursor()
        cursor.execute('SELECT * FROM user_login WHERE username=%s', (username,))
        user = cursor.fetchone()
        cursor.close()

        # tries session
        if 'tries' not in session:
            session['tries'] = 0

        if user:
            hashed_pass = user[3]
            if bcrypt.check_password_hash(hashed_pass,password):
                session['tries'] = 0
                session['username'] = user[2]
                session['user_id'] = user[0]
                flash('Login successfull','success')
                return redirect(url_for('add_habits'))  
            else:
                session['tries'] += 1
                if session['tries'] >= 3:
                    session['lock_time'] = time.time()  
                    return redirect(url_for('blocktime'))     
                else:
                    flash('Incorrect password','message')
                    return redirect(url_for('login'))
        
        flash('No user found','warning')
        return redirect(url_for('register'))
    
    return render_template('login.html', form=form)

### Still not clicked #######
@app.route('/blocktime')
def blocktime():
    lock_time = session.get('lock_time')
    print("Session create time: ",lock_time)

    if not lock_time:
        return redirect(url_for('login'))
    
    now = time.time()
    print('Current time:', now)
    elapsed= now - lock_time   # why this
    print('Elapsed time: ',elapsed)
    wait_sec = 120   # ?

    if elapsed >= wait_sec:   # how this catches... 
        # reset tries
        session['tries'] = 0
        session.pop('lock_time', None)
        return redirect(url_for('login'))
    
    remaining = int(elapsed - wait_sec)
    return render_template('time.html', remaining=remaining)

# logout
@app.route('/logout',methods=['POST'])
def logout():
    session.clear()
    flash('You are logout','success')
    return redirect(url_for('login'))


# Add habits
@app.route('/add_habits', methods=['POST','GET'])
def add_habits():
    # check if user logged in 
    if 'user_id' not in session:
        flash('Please login first','warning')
        return redirect(url_for('login'))
    # else go for adding habits
    form = addHabitForm()
    if form.validate_on_submit():
        habits = form.myhabit.data.capitalize()
        its_frequency = form.habit_frequency.data.upper()  # upper() for Frequency in capital letters 

        # db
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO habits (user_id,habit_name,frequency) VALUES (%s,%s,%s)',(session['user_id'],habits,its_frequency))
        last_habit_id = cursor.lastrowid    

        # get the current date fron datetime()
        current_date = datetime.today()
        cursor.execute('INSERT INTO habit_logs (user_id,habit_id,log_date) VALUES (%s,%s,%s)', (session['user_id'],last_habit_id,current_date))
        mysql.connection.commit()
        cursor.close()
        flash('Task has been successfully added into database.',"success")
        return redirect(url_for('show_habits'))
    
    return render_template('add_habits.html', form=form)


@app.route('/show_habits', methods=['GET'])
def show_habits():
    # check if user logged in
    if 'user_id' not in session:
        flash('Please login first','warning')
        redirect(url_for('login'))

    # retrieve data from database
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT id,habit_name,frequency,status FROM habits WHERE user_id =%s', (session['user_id'],))
    user_data = cursor.fetchall()

    return render_template('show_habits.html', my_data=user_data, username=session.get('username'))

@app.route('/mark_done/<int:id>',methods=['POST'])
def mark_done(id):
    cursor = mysql.connection.cursor()

    # update habits table
    cursor.execute('UPDATE habits SET status="done" where id=%s AND user_id=%s', (id,session['user_id']))
    mysql.connection.commit()

    # update habit_logs table too
    cursor.execute(""" INSERT INTO habit_logs (user_id,habit_id,log_date,status) 
                   VALUES (%s,%s,CURDATE(),'done') 
                   ON DUPLICATE KEY UPDATE status ='done'""",
                   (session['user_id'],id))

    # get user email
    cursor.execute('SELECT * from user_login')
    my_data = cursor.fetchone()
    my_email = my_data[4]
    
    # get habit name
    cursor.execute('Select * from habits where id=%s',(id,))  
    habit_table = cursor.fetchone()
    habit_name = habit_table[2]
    print(habit_table)

    msg = Message(

        subject='HABIT TRACKER APP',
        sender='sirhammad760@gmail.com',
        recipients=[my_email]
    )
    msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
                <div style="max-width: 500px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0px 2px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #2c7be5; text-align: center;">Habit Tracker ✅</h2>
                <p style="font-size: 16px; color: #333;">
                    Congratulations! 🎉
                </p>
                <p style="font-size: 16px; color: #333;">
                    You have <b>successfully completed your habit '{habit_name}' today</b>. Keep up the great consistency!
                </p>
                <hr style="margin: 20px 0;">
                <p style="font-size: 14px; color: #666; text-align: center;">
                    — Sent automatically by <b>Habit Tracker App</b>
                </p>
                </div>
            </body>
            </html>
            """

    mail.send(msg)
    cursor.close()
# pending work 
    flash('Status Updated','success')
    return redirect(url_for('show_habits'))

# remove functionality
@app.route('/remove/<int:id>',methods=['POST','GET'])
def remove(id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM habits WHERE user_id =%s AND id=%s',(session['user_id'],id))
    mysql.connection.commit()
    cursor.close()
    flash('Habit has been successfully removed from list', 'sucess')
    return redirect(url_for('show_habits'))

# run app
app.run(debug=True)