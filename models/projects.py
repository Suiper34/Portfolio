from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models import db


class Projects(db.Model):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    image: Mapped[str] = mapped_column(
        String(250), default='default_project_pic.jpg')
    demo_url: Mapped[str | None] = mapped_column(String(250), unique=True)
    github_url: Mapped[str | None] = mapped_column(String(250), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    apk_size: Mapped[str | None] = mapped_column(String(20))
    platform: Mapped[str | None] = mapped_column(String(50))
    github_stars: Mapped[int] = mapped_column(default=0)
    tech_stack: Mapped[str | None] = mapped_column(String(250))
    responsive: Mapped[bool] = mapped_column(default=False)
    figma_canva_url: Mapped[str | None] = mapped_column(
        String(250), unique=True)                                 # For UI/UX
    file_name: Mapped[str | None] = mapped_column(
        String(100), unique=True)                          # Uploaded file path
    version: Mapped[str | None] = mapped_column(String(50))
    is_live: Mapped[bool] = mapped_column(default=False)

    my_id: Mapped[int] = mapped_column(
        ForeignKey('admin.id', ondelete='CASCADE'))

    def __repr__(self):
        return f'title: {self.title} \n\n category: {self.category}'
