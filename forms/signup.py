from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class SignUp(FlaskForm):
    name = StringField('Full name',
                       validators=[DataRequired(), Length(max=250)])
    username = StringField('Username',
                           validators=[DataRequired(), Length(max=50)])
    email = EmailField('Email',
                       validators=[DataRequired(), Email(), Length(max=200)])
    password = PasswordField('Password',
                             validators=[
                                 DataRequired(), Length(min=8, max=100)
                             ])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Enter same password as %(Password)')
        ])
    signup = SubmitField('Sign Up')
