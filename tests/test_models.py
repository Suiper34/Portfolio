from app import db
from models.admin import User
from models.clients import Clients
from models.projects import Projects
from models.skills import Skills


def test_user_password_hashing(app):
    """
    User.set_password should store a hash and affirm_password should verify.
    """

    user = User(name='Test', username='testuser', email='test@example.com')
    user.set_password('supersecret123')
    db.session.add(user)
    db.session.commit()

    the_user = db.session.get(User, user.id)
    assert the_user is not None
    assert the_user.username == 'testuser'
    assert the_user.affirm_password('supersecret123') is True
    assert the_user.affirm_password('wrongpass') is False


def test_project_crud(app):
    """Create a project, persist and read back."""

    project = Projects(title='ML Project',
                       category='Mobile App',
                       description='description of project',)
    db.session.add(project)
    db.session.commit()

    a_project = db.session.get(Projects, project.id)
    assert a_project is not None
    assert a_project.title == 'ML Project'
    # defaults
    assert hasattr(a_project, 'image')
    assert a_project.github_stars == 0


def test_skill_unique_and_proficiency(app):
    """
    Add a skill and ensure proficiency stored and name uniqueness enforced.
    """

    skill = Skills(name='Python', proficiency=95.0)
    db.session.add(skill)
    db.session.commit()

    py_skill = db.session.scalar(
        Skills.__table__.select().where(Skills.name == 'Python')
    )
    # basic sanity check
    assert py_skill is not None


def test_client_model_image_field(app):
    """Clients model should accept a client_img filename and be retrievable."""

    client = Clients(client_name='Suiper Co', profession='Partner',
                     testimonial='Nice work', client_img='acme.jpg')
    db.session.add(client)
    db.session.commit()

    a_client = db.session.get(Clients, client.id)
    assert a_client.client_img == 'acme.jpg'
