# 🌐 JhapTech — Portfolio Web App ⚡️

A personal portfolio / admin CMS built with Flask, SQLAlchemy and Bootstrap.

---

**Features🚀**: user auth, admin dashboard, projects, clients, team, skills, experience, file uploads, migrations and Docker support.

---

## 🔗 Quick links

- 📁 Source: this repository
- 🐳 Docker & docker-compose ready
- ⚙️ CI: GitHub Actions workflow included (build & migrate)
- 🗄️ DB: PostgreSQL (local via docker-compose / production via DATABASE_URI)

---

## 📈 Prerequisites

- Python 3.11
- Docker & Docker Compose (for containerized run)

---

## 💻 Requirements

- Python 3.8+
- Bootstrap_Flask
- Flask_Login
- Flask_WTF
- WTForms
- Werkzeug
- Flask
- flask_sqlalchemy
- SQLAlchemy
- gunicorn
- psycopg2-binary
- dotenv
- bleach  # for deployment
- email_validator
- Flask-Migrate

---

## Project Structure

   ```
   Portfolio/
    ├── app.py
    ├── forms/
    | ├── clients_form.py
    | ├── contact_form.py
    | ├── exoerience_form.py
    | ├── login.py
    | ├── projects_form.py
    | ├── signup.py
    | ├── skills_form.py
    | ├── team_form.py
    ├── instance/
    │ └── jhaps_db.db (local dev db)
    ├── migrations/
    ├── models/
    | ├── admin.py
    | ├── clients.py
    | ├── exoerience.py
    | ├── projects.py
    | ├── skills.py
    | ├── team.py
    │ └── css/
    │ | ├── bootsrap.min.css
    │ | ├── style.css
    │ └── files
    │ └── img/
    │ | ├── app_images
    ├ └── js/
    │ | ├── main.js
    │ └── lib/
    │ | └── animate/
    │ | └── counterup/
    │ | └── easing/
    │ | └── isotope/
    │ | └── lightbox/
    │ | | └── css/
    │ | | └── images/
    ├ | | └── js/
    │ | | ├── links.php
    │ | └── owlcarousel/
    │ | | └── assets/
    │ | | ├── license
    │ | | ├── helpers
    │ | | ├── owl.carousel.min.js
    | | └── typed/
    │ | └── waypoints/
    | | └── wow/
    │ └── scss/
    │ | └── bootstrap/
    │ | | └── scss/
    │ | | | └── forms/
    │ | | | └── helpers/
    │ | | | └── mixins/
    │ | | | └── utilities/
    │ | | | └── vendor/
    │ | | | ├── other_scss.scss
    │ | └── bootstrap.scss
    ├── templates
    │ ├── base.html
    │ ├── about.html
    │ ├── add-client.html
    │ ├── add-experience.html
    │ ├── add-member.html
    │ ├── add-project.html
    │ ├── add-skill.html
    │ ├── admin_dashboard.html
    │ ├── admin_users.html
    │ ├── codex.html
    │ ├── contact.html
    │ ├── flash_msg.html
    │ ├── header.html
    │ ├── index.html
    │ ├── login.html
    │ ├── map.html
    │ ├── projects.html
    │ ├── read-more.html
    │ ├── services.html
    │ ├── signup.html
    │ ├── skills.html
    ├── .env
    ├── CI_Build
    ├── deploy.sh
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    ├── Procfile
    └── README.md
   ```

---

## 👩‍💻 Setup (local, venv)

1. **Copy env sample and edit**:

   ```bash
   cp .env.sample .env
   ```

2. **Create and activate virtualenv**:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows PowerShell
   ```

3. **Install**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize DB (sqlite quick-start) or configure DATABASE_URI in .env**:

   ```bash
   flask db init
   flask db migrate -m "init"
   flask db upgrade
   ```

5. **Run**:

   ```bash
   python -m app.py
   ```

---

## 🐳 Run with Docker (recommended for parity)

- Build & run:

  ```bash
  docker compose up --build -d
  ```

- Create migrations and apply (run in web container):

  ```bash
  docker compose run --rm web flask db upgrade
  ```

- Visit: [`http://localhost:8000`](http://localhost:8000)

---

## ⚙️ Environment variables

- SECRET_KEY — strong random secret (in .env)
- DATABASE_URI — SQLAlchemy connection string (Postgres recommended)
- MAIL, PASSWORD — for contact-form email (use app-specific Gmail password)
- UPLOAD_FOLDER — defaults to `static/files`
See `.env.sample` for the full list.

---

## 📝 Deployment notes

- CI workflow provided builds image and runs migrations (uses GHCR by default). Add secrets to GitHub: `DATABASE_URI`, `GHCR_PAT`.
- **Recommended free platforms**: Railway, Fly.io , Render — all provide Postgres and support Docker images . Configure `DATABASE_URI` with the platform DB connection string and run migrations (CI or one-off container).
- Use Gunicorn (Procfile & Dockerfile included) for production.

---

## 🗂️ File uploads & storage

- Uploaded files saved to `static/files` by default. For production use S3 or a managed object store. Always validate and sanitize filenames (secure_filename is used).

---

## ✨ Migrations

- Uses Flask-Migrate / Alembic. Always run `flask db migrate` then `flask db upgrade` when schema changes are introduced.

---

## ⚠️ Security & best practices

- Never commit .env with secrets.
- Use app-specific email/passwords
- Run behind HTTPS in production.
- Limit file upload sizes (MAX_CONTENT_LENGTH configured).

---

## 🧩 Troubleshooting

- 404 on uploaded images → ensure `client.client_img` is used in template and path built with:

  ```python
  url_for('static', filename='files/' ~ client.client_img)
  ```

- 'list object is not callable' → avoid shadowing function names (e.g., `admins`).

---

## 🤝 Contributing ✨

- Add issues for new categories or bugs.
- Submit PRs with tests and clear commit messages.
- **Keep changes backwards compatible**: preserve the default categories and move behavior.

---

## 🧾 License

- This project is released under the MIT License. See [`LICENSE`](https://github.com/Suiper34) for details.

---

## 🛠️ Maintainer

- JhapTech / Theophilus Asamoah Gyapong — [`email`]('jhapson34@gmail.com') or [`whatsapp`](wa.me/+233201166556)
