from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models import db


class Skills(db.Model):
    __tablename__ = 'skills'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    proficiency: Mapped[float]  # 0-100%
    my_id: Mapped[int] = mapped_column(
        ForeignKey('admin.id', ondelete='CASCADE'))

    def __repr__(self):
        return f'skill: <{self.name}>'
