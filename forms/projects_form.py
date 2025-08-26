from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import (BooleanField, DateTimeField, FileField, FloatField,
                     IntegerField, RadioField, StringField, SubmitField,
                     TextAreaField, URLField)
from wtforms.validators import URL, DataRequired, Length, NumberRange


class Project(FlaskForm):
    ALLOWED_IMG_EXTENSIONS: set[str] = {'jpg', 'png', 'jpeg', 'gif'}
    ALLOWED_FILE_EXTENSIONS: set[str] = {
        'apk', 'zip', 'png', 'jpg', 'fig', 'jpeg', 'mp4', 'mkv', 'pdf'}

    title = StringField('Project Title',
                        validators=[DataRequired(), Length(max=250)])
    category = RadioField('Project Category',
                          choices=[
                              'Mobile App',
                              'Web App',
                              'UI/UX',
                              'Data Science',
                              'Desktop App',
                              'Game',
                              'Graphic Design',
                              'Video Editing'],
                          validators=[DataRequired(),
                                      Length(max=100)])
    description = TextAreaField('Description',
                                validators=[Length(min=4, max=999)])
    image = FileField('Image',
                      validators=[
                          FileRequired('Load an image file'),
                          FileAllowed(
                              ALLOWED_IMG_EXTENSIONS,
                              'Only (.jpeg, .jpg, .png, .gif ) are allowed!')])
    demo_url = URLField('Demo URL',
                        validators=[
                            URL(message='Enter a valid URL'),
                            Length(max=250)])
    github_url = URLField('Github URL',
                          validators=[
                              URL(message='Enter a valid URL'),
                              Length(max=250)])
    created_at = DateTimeField('Created At')
    apk_size = FloatField('Apk Size',
                          validators=[NumberRange(max=100), Length(max=20)])
    platform = StringField('Platform',
                           validators=[Length(max=50)])
    github_stars = IntegerField('Github Stars')
    tech_stack = StringField('Project\'s Tech Stack',
                             validators=[Length(max=250)])
    responsive = BooleanField(label='Is Responsive')
    figma_url = URLField('Figma URL',
                         validators=[URL(), Length(max=250)])
    file_name = FileField('File name',
                          validators=[
                              FileAllowed(
                                  ALLOWED_FILE_EXTENSIONS,
                                  'Extension used not allowed!\n\n \
                                      Upload file with either of these \
                                          ("apk", "zip", "png", "jpg", "fig") \
                                              extension'
                              )])
    current_version = StringField('Current Version',
                                  validators=[Length(max=20)])
    is_live = BooleanField('Is Live')
    add = SubmitField('Save')

    def allowed_img_files(self, filename: str) -> bool:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_IMG_EXTENSIONS

    def allowed_files(self, filename: str) -> bool:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_FILE_EXTENSIONS
