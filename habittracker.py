import time
from flask import Flask,url_for,redirect,render_template,request,session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask import flash,get_flashed_messages
from forms import RegisterForm,LoginForm,addHabitForm

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

        # hash the pass
        hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')

        # save into db
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO user_login (username,password) VALUES (%s,%s)', (username,hashed_pass))
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
                    session['lock_time'] = time.time()  # returns current time
                    flash('Tries limit exceeded','danger')
                    return redirect(url_for('blocktime'))     # feature is coming soon!
                else:
                    flash('Incorrect password','message')
                    return redirect(url_for('login'))
        
        flash('No user found','warning')
        return redirect(url_for('register'))
    
    return render_template('login.html', form=form)


@app.route('/blocktime')
def blocktime():
    lock_time = session.get('lock_time')

    if not lock_time:
        return redirect(url_for('login'))
    
    now = time.time()
    elapsed= now - lock_time
    wait_sec = 60   

    if elapsed >= wait_sec:
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
        habits = form.myhabit.data
        its_frequency = form.habit_frequency.data

        # db
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO habits (user_id,habit_name,frequency) VALUES (%s,%s,%s)',(session['user_id'],habits,its_frequency))
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
    cursor.close()
    return render_template('show_habits.html', my_data=user_data, username=session.get('username'))

@app.route('/mark_done/<int:id>',methods=['POST'])
def mark_done(id):
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE habits SET status="done" where id=%s', (id,))
    mysql.connection.commit()
    cursor.close()
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

# 



# run app
app.run(debug=True)