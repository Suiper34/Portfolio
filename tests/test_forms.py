from forms.projects_form import Project
from forms.clients_form import ClientForm


def test_project_form_allowed_file_checks():
    """
    Project form helpers should accept allowed extensions and reject others.
    """

    form = Project()
    assert form.allowed_img_files('image.jpg') is True
    assert form.allowed_img_files('image.jpeg') is True
    assert form.allowed_img_files('image.png') is True
    assert form.allowed_img_files('image.gif') is True
    assert form.allowed_img_files('image.bmp') is False

    assert form.allowed_files('app.apk') is True
    assert form.allowed_files('archive.zip') is True
    assert form.allowed_files('document.pdf') is True
    assert form.allowed_files('unknown.ext') is False


def test_client_form_fields_simple():
    """
    ClientForm should expose validators and fields without raising on import.
    """

    form = ClientForm()
    # basic assertions that fields exist
    assert hasattr(form, 'client_name')
    assert hasattr(form, 'profession')
    assert hasattr(form, 'testimonial')
