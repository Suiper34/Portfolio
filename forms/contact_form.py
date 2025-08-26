from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    name = StringField('Name',
                       validators=[DataRequired(), Length(max=200)],
                       id='name')
    email = EmailField('Email',
                       validators=[DataRequired(), Email(), Length(max=200)],
                       id='email')
    subject = StringField('Subject',
                          validators=[Length(max=250)],
                          id='subject')
    message = TextAreaField('Message',
                            validators=[DataRequired(), Length(max=500)],
                            id='message')
    send = SubmitField('Send')
