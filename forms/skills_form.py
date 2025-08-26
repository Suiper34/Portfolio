from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, InputRequired, NumberRange, \
    Length


class SkillsForm(FlaskForm):
    skill_name = StringField('Skill',
                             validators=[DataRequired(), Length(max=100)])
    proficiency = FloatField('Proficiency',
                             validators=[
                                 InputRequired(), NumberRange(min=1, max=100)])
    submit = SubmitField('Submit')
