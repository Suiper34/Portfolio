from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models import db


class Clients(db.Model):
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(100))
    profession: Mapped[str] = mapped_column(String(100))
    testimonial: Mapped[str | None] = mapped_column(String(999))
    client_img: Mapped[str] = mapped_column(String(250), unique=True)

    def __repr__(self):
        return f'role: <{self.client_name}>'
