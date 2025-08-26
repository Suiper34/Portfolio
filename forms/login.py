from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


class Login(FlaskForm):
    name_or_email = StringField('Username/Email',
                                validators=[DataRequired()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    login = SubmitField('Login')
