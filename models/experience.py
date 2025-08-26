from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models import db


class Experience(db.Model):
    __tablename__ = 'experience'

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str]
    role: Mapped[str] = mapped_column(String(250))
    start_year: Mapped[int]
    end_year: Mapped[int] = mapped_column(default=datetime.now().year)
    experience_field: Mapped[str] = mapped_column(String(250))
    my_id: Mapped[int] = mapped_column(
        ForeignKey('admin.id', ondelete='CASCADE'))

    def __repr__(self):
        return f'role: <{self.role}>'


# class SchoolExperience(db.Model):
#     __tablename__ = 'school_experience'

#     id: Mapped[int] = mapped_column(primary_key=True)
#     role: Mapped[str] = mapped_column(String(250))
#     start_year: Mapped[int]
#     end_year: Mapped[int] = mapped_column(default=datetime.now().year)
#     experience_field: Mapped[str] = mapped_column(String(250))
#   my_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete='CASCADE'))

#     def __repr__(self):
#         return f'skill: <{self.role}>'
