from flask import Flask,url_for,redirect,render_template,request,session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask import flash,get_flashed_messages
from forms import RegisterForm,LoginForm
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

        if user:
            hashed_pass = user[3]
            if bcrypt.check_password_hash(password,hashed_pass):
                session['username'] = user[2]
                session['user_id'] = user[1]
                flash('Login successfull','success')
                return render_template('application.html')
            else:
                flash('Incorrect password','message')
                return redirect(url_for('login'))
        
        flash('No user found','warning')
        return redirect(url_for('register'))
    
    return render_template('login.html', form=form)
    
            
                



app.run(debug=True)