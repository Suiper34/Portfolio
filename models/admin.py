from flask_login import UserMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from models import db

from .experience import Experience
from .projects import Projects
from .skills import Skills


class User(db.Model, UserMixin):
    __tablename__ = 'admin'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    projects: WriteOnlyMapped['Projects'] = relationship(
        backref='suipjhaps', cascade='all, delete-orphan')
    skills: WriteOnlyMapped['Skills'] = relationship(
        backref='suipjhaps', cascade='all, delete-orphan')
    experience: WriteOnlyMapped['Experience'] = relationship(
        backref='suipjhaps', cascade='all, delete-orphan')

    is_admin: Mapped[bool] = mapped_column(default=False)

    def set_password(self, signup_password: str) -> str:
        self.password = generate_password_hash(signup_password, salt_length=24)

    def affirm_password(self, login_password: str) -> bool:
        return check_password_hash(self.password, login_password)

    def __repr__(self):
        return f'username: <{self.username}>'
