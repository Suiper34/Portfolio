from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import IntegerField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange


class ExperienceForm(FlaskForm):
    category = RadioField('Field Category',
                          validators=[DataRequired()],
                          choices=['Industry', 'School'])
    role = StringField('Role on field',
                       validators=[DataRequired(), Length(max=100)])
    start_year = IntegerField('Start year',
                              validators=[
                                  InputRequired(),
                                  NumberRange(
                                      min=1970, max=datetime.now().year)
                              ])
    end_year = IntegerField('Current/End year',
                            validators=[
                                NumberRange(
                                    min=1970, max=datetime.now().year)
                            ])
    experience_field = StringField('Industry or School Name')
    submit = SubmitField('Submit')
