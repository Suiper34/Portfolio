from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import FileField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ClientForm(FlaskForm):
    ALLOWED_IMG_EXTENSIONS: set[str] = {'jpg', 'png', 'jpeg'}
    client_name = StringField('Client\'s name',
                              validators=[DataRequired(), Length(max=100)])
    profession = StringField('Profession',
                             validators=[DataRequired(), Length(max=100)])
    testimonial = TextAreaField('Testimonial', validators=[Length(max=999)])
    client_img = FileField(
        'Client\'s photo',
        validators=[
            FileAllowed(upload_set=ALLOWED_IMG_EXTENSIONS,
                        message='Only(.jpeg, .jpg, .png) extensions are \
                            allowed!')])
    submit = SubmitField('Submit')

    def allowed_img_files(self, filename: str) -> bool:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_IMG_EXTENSIONS
