from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, URLField
from wtforms.validators import URL, DataRequired, Length


class TeamForm(FlaskForm):
    member_name = StringField('Member Name',
                              validators=[DataRequired(), Length(max=250)])
    role = StringField('Role in team',
                       validators=[DataRequired(), Length(max=250)])
    portfolio_link = URLField('Portfolio Link',
                              validators=[URL(), Length(max=250)])
    github_link = URLField('Github Profile link',
                           validators=[URL(), Length(max=250)])
    submit = SubmitField('Submit')
