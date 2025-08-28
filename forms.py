from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import DataRequired,Length



# register form
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(),Length(min=6,max=20)])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=8,max=20)])
    submit = SubmitField('Register')

# register form    
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(),Length(min=6,max=20)])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=8,max=20)])
    submit = SubmitField('Login')