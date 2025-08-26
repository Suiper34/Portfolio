from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models import db


class Team(db.Model):
    __tablename__ = 'my_team'

    id: Mapped[int] = mapped_column(primary_key=True)
    member_name: Mapped[str] = mapped_column(String(250))
    role: Mapped[str] = mapped_column(String(250))
    portfolio_link: Mapped[str | None] = mapped_column(
        String(250), unique=True)
    github_link: Mapped[str | None] = mapped_column(String(250), unique=True)

    def __repr__(self):
        return f'role: <{self.member_name}>'
