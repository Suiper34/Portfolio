from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from functools import wraps
from hashlib import sha256
from logging.handlers import RotatingFileHandler
from os import environ, makedirs, path, urandom
from pathlib import Path
from re import compile, sub
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, jsonify, redirect,
                   render_template, request, send_from_directory, url_for)
# from flask_admin import Admin
from flask_bootstrap import Bootstrap5
from flask_caching import Cache
from flask_login import (LoginManager, current_user, login_required, login_url,
                         login_user, logout_user)
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from sqlalchemy import func, select, update
from sqlalchemy.exc import (DatabaseError, IntegrityError, NoSuchTableError,
                            OperationalError)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from forms.clients_form import ClientForm
from forms.contact_form import ContactForm
from forms.experience_form import ExperienceForm
from forms.login import Login
from forms.projects_form import Project
from forms.signup import SignUp
from forms.skills_form import SkillsForm
from forms.team_form import TeamForm
from models import db
from models.admin import User
from models.clients import Clients
from models.experience import Experience
from models.projects import Projects
from models.skills import Skills
from models.team import Team
from services.ai_client import AssistantClientError, jhaptech_assistant_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

upload_dir = BASE_DIR / 'static' / 'files'
upload_dir.mkdir(parents=True, exist_ok=True)


def resolve_secret_key() -> str:
    """
    Return a deterministic secret key from env vars or generate a random
    fallback.
    """

    for candidate in (
        environ.get('SECRET_KEY'),
        environ.get('FLASK_SECRET_KEY'),
        environ.get('APP_SECRET_KEY'),
    ):
        if candidate:
            return candidate

    return urandom(32).hex()


def resolve_database_uri() -> str:
    """
    Resolve the SQLAlchemy database URI from environment fallbacks.
    """

    return (
        environ.get('DATABASE_URI')
        or environ.get('DB_URI_DOCKER')
        or 'sqlite:///jhaps_db.db'
    )


DEFAULT_CACHE_TYPE = 'RedisCache' if environ.get(
    'REDIS_URL') else 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = int(environ.get('CACHE_DEFAULT_TIMEOUT', 300))
ASSISTANT_CACHE_TTL = int(environ.get('ASSISTANT_CACHE_TTL', 600))
ASSISTANT_SNAPSHOT_TTL = int(environ.get('ASSISTANT_SNAPSHOT_TTL', 120))

app = Flask(__name__)
app.config['SECRET_KEY'] = resolve_secret_key()
app.config['FLASK_ADMIN_SWATCH'] = 'cyborg'
app.config['SQLALCHEMY_DATABASE_URI'] = resolve_database_uri()
app.config['UPLOAD_FOLDER'] = str(upload_dir)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # (100 mb)
app.config['CACHE_DEFAULT_TIMEOUT'] = CACHE_DEFAULT_TIMEOUT,
app.config['CACHE_TYPE'] = environ.get('CACHE_TYPE', DEFAULT_CACHE_TYPE),
app.config['CACHE_REDIS_URL'] = environ.get('REDIS_URL',
                                            'redis://redis:6379/0'),
# admin = Admin(app, name='portfolio')
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

cache_config = {
    'CACHE_TYPE': app.config['CACHE_TYPE'],
    'CACHE_DEFAULT_TIMEOUT': CACHE_DEFAULT_TIMEOUT,
}
if cache_config['CACHE_TYPE'].lower() == 'rediscache':
    cache_config['CACHE_REDIS_URL'] = app.config['CACHE_REDIS_URL']

cache = Cache(config=cache_config)
cache.init_app(app)

LOG_LEVEL = environ.get('LOG_LEVEL', 'INFO').upper()

logger = logging.getLogger('jhaptech')
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# formatter
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s [%(funcName)s:%(lineno)d] - \
        %(message)s'
)

# console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logger.addHandler(console_handler)

# file handler
try:
    logs_dir = path.join(path.dirname(__file__), 'logs')

    if not path.exists(logs_dir):
        makedirs(logs_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        path.join(logs_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.addHandler(file_handler)

except Exception:
    logger.exception('Failed to set up file logging handler')

# integrate Flask's app.logger with the logger handlers/level
app.logger.handlers = logger.handlers[:]
app.logger.setLevel(logger.level)
app.logger.propagate = False

# first admin
with app.app_context():
    try:
        if first_admin := db.session.get(User, 1):
            first_admin.is_admin = True
            db.session.commit()

    except Exception:
        # skip when tables does not exist yet (running migrations)
        logger.debug(
            'Skipping first-admin setup: database/tables likely not present'
        )


ASSISTANT_SUGGESTIONS: List[str] = [
    'How do I explore your projects?',
    'How can I contact the team?',
    'What can admins do on this site?',
    'Where do uploads go?',
]

ASSISTANT_PATTERNS: list = [
    (
        compile(r'\b(project|portfolio|case study|case-study)\b'),
        lambda stats: (
            'You can browse the portfolio via **My Projects** in the top menu '
            'or from the homepage. Right now we have '
            f'{stats.get("project_count", 0)} published project(s). '
            'Each entry includes tech stack details, links, and \
                optional assets.'
        ),
    ),
    (
        compile(r'\b(contact|email|reach|message)\b'),
        lambda stats: (
            'We love hearing from visitors! Use the **Contact** page to send '
            'a message or drop us an email at the address configured '
            'in the contact form. There\'s also a WhatsApp shortcut in the\
                footer for quick chats.'
        ),
    ),
    (
        compile(r'\b(admin|dashboard|manage|cms)\b'),
        lambda stats: (
            'Admins can log in to the dashboard to manage projects, clients,'
            ' team members, skills, and experiences.'
            ' Promote users from the **Users** tab and every change is tracked\
                via the database migrations.'
        ),
    ),
    (
        compile(r'\b(upload|resume|file|download)\b'),
        lambda stats: (
            'Uploaded assets are stored under `static/files`. '
            'When you add clients or projects, approved image formats are '
            'validated and stored safely. Visitors can download files through \
                secure endpoints.'
        ),
    ),
]


def _normalise_query(text: str) -> str:
    """Collapse whitespace and lowercase queries to stabilize cache keys."""
    return sub(r'\s', ' ', text.strip().lower())


def _assistant_cache_key(query: str) -> str:
    """Build a deterministic cache key for an assistant answer."""

    digest: str = sha256(_normalise_query(
        query).encode('utf-8')).hexdigest()

    return f'assistant:response:{digest}'


def get_site_snapshot() -> Dict[str, int]:
    """Return cached aggregate stats used for contextual assistant prompts."""

    cache_key = 'assistant:site_snapshot'
    cached_snapshot = cache.get(cache_key)

    if cached_snapshot is not None:
        return cached_snapshot

    snapshot = {
        'project_count': 0,
        'client_count': 0,
        'team_count': 0,
    }

    try:
        snapshot['project_count'] = db.session.scalar(
            select(func.count()).select_from(Projects)
        ) or 0
        snapshot['client_count'] = db.session.scalar(
            select(func.count()).select_from(Clients)
        ) or 0
        snapshot['team_count'] = db.session.scalar(
            select(func.count()).select_from(Team)
        ) or 0

    except NoSuchTableError as missing_table:
        logger.debug(
            'assistant snapshot skipped (missing table): %s', missing_table)

    except DatabaseError as db_err:
        logger.warning('assistant snapshot DB issue: %s', db_err)

    except Exception:
        logger.exception('assistant snapshot unexpected error')

    cache.set(cache_key, snapshot, timeout=ASSISTANT_SNAPSHOT_TTL)

    return snapshot


def compose_assistant_prompt(stats: Dict[str, int]) -> str:
    """Compose a resilient system prompt grounded in live portfolio stats."""

    prompt_lines: List[str] = [
        'You are JhapsTech\'s helpful AI assistant. Answer with concise '
        'markdown (≤150 words) and always ground replies in the portfolio \
            context below.',
        f'- Published projects: {stats.get("project_count", 0)}',
        f'- Featured clients: {stats.get("client_count", 0)}',
        f'- Active team members: {stats.get("team_count", 0)}',

        'Encourage users to explore the site \
            (Home, My Projects, Services, Skills, Contact, About) and remind \
                admins they must log in for dashboard actions when relevant.',
    ]

    for pattern, handler in ASSISTANT_PATTERNS:
        prompt_lines.append(
            f'If a query matches pattern `{pattern.pattern}`, \
                lean on this guidance: {handler(stats)}'
        )

    prompt_lines.append(
        'Never invent data. When unsure, invite the user to explore the \
            Contact page or the portfolio sections.'
    )

    return '\n'.join(prompt_lines)


def heuristic_assistant_reply(stats: Dict[str, int], query: str) -> str:
    """
    Return a deterministic fallback answer when the AI backend is unavailable.
    """

    normalised: str = _normalise_query(query)

    for pattern, handler in ASSISTANT_PATTERNS:
        if pattern.search(normalised):
            return handler(stats)

    return (
        'Here’s how to get around:\n'
        '- **Home** lists current team  client highlights '
        f'({stats.get("team_count", 0)} member(s), \
            {stats.get("client_count", 0)} client story/stories).\n'
        '- **My Projects** has detailed case studies.\n'
        '- **Contact** lets you reach me (email, WhatsApp, socials).\n'
        '- Admins can log in for dashboard controls.\n\n'
        'Ask about projects, uploads, admin tools, or how to get in touch!'
    )


@app.route('/assistant/query-replies', methods=['POST'])
def build_assistant_reply() -> Response | tuple:
    try:
        stats: Dict[str, int] = get_site_snapshot()
        system_prompt: str = compose_assistant_prompt(stats)
        user_query: Optional[Any] = request.json.get('query', '')

        response: str = jhaptech_assistant_client.generate(system_prompt,
                                                           user_query)
        return jsonify({'response': response})

    except AssistantClientError:
        # fallback to heuristic response
        fallback_response: str = heuristic_assistant_reply(stats, user_query)
        return jsonify({'response': fallback_response})

    except Exception as e:
        logger.error('Assistant query failed: %s', e)
        return jsonify({'error': 'Assistant service unavailable!'}), 503


def admins_only(func):
    """
    Decorator: allow only admin users.

    Checks the database for users with `is_admin==True`. If no admins exist
    or current_user is not among them, flashes and aborts(403).

    Side effects: reads the User table. Returns decorated view or aborts.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        try:
            admins_list: Sequence[User] = db.session.scalars(
                select(User).where(User.is_admin.is_(True))
            ).all()

        except (NoSuchTableError, DatabaseError) as db_err:
            logger.warning('admins_only: DB table error: %s', db_err)
            admins_list = []

        except Exception:
            logger.exception('admins_only: unexpected error')
            admins_list = []

        if not admins_list:
            flash('Admins only!', category='danger')
            return abort(403)

        if current_user not in admins_list:
            flash('Admins only!', category='danger')
            return abort(403)

        return func(*args, **kwargs)

    return wrapper


def admins() -> Sequence[User]:
    """
    Return a list of admin users.

    Safe: on DB/table errors returns an empty list. Use this to pass admin
    context into templates.
    """

    try:
        return db.session.scalars(
            select(User).where(User.is_admin.is_(True))
        ).all()

    except (NoSuchTableError, DatabaseError) as db_err:
        logger.warning("admins(): DB error: %s", db_err)
        return []

    except Exception:
        logger.exception('admins(): unexpected error')
        return []


@login_manager.user_loader
def load_user(user_id) -> Optional[User]:
    """
    Flask-Login user loader.

    Args:
        user_id (str|int): user id stored in session.

    Returns:
        User | None: the loaded User model instance or None.
    """

    try:
        return db.session.get(User, int(user_id))

    except (TypeError, ValueError):
        logger.warning('Invalid user_id supplied to load_user: %s', user_id)
        return None


@app.route('/health', methods=['GET'])
def health() -> tuple:
    """
    Lightweight JSON health check endpoint for container orchestration.
    """

    return jsonify(
        status='ok',
        timestamp=datetime.now(timezone.utc).isoformat() + 'Z'
    ), 200


@app.route('/assistant/chat', methods=['GET'])
def jhaptech_assistant_chat():
    """Render the AI assistant chat UI and surface prompt suggestions."""

    return render_template(
        'assistant_chat.html',
        admins=admins(),
        assistant_enabled=jhaptech_assistant_client.is_enabled(),
        suggestions=ASSISTANT_SUGGESTIONS,
        year=datetime.now().year,
    )


@app.route('/sign-up', methods=['POST', 'GET'])
def signup() -> Response | str:
    """
    Create a new user account and log them in.

    Methods:
      - GET: Render signup form.
      - POST: Validate form, create User, hash password, commit to DB
              and log user in.

    Returns:
      - On GET or validation failure: render signup template
      - On success: redirect to next_url (string)
      - On DB errors: renders signup with appropriate flash messages
    """

    next_url: str = request.args.get('next') or url_for('home')

    if current_user.is_authenticated:
        return redirect(next_url)

    form = SignUp()

    if form.validate_on_submit():
        try:
            user: User = User(
                name=form.name.data,
                username=form.username.data,
                email=form.email.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('New account registered!', category='success')

        except IntegrityError as ie:
            logger.warning('signup IntegrityError: %s', ie)
            flash('Username or Email already used — \
                choose a different one.', category='warning')
            db.session.rollback()

        except (OperationalError, DatabaseError) as db_err:
            logger.error("signup DB error: %s", db_err)
            flash('Database not ready.', category='error')
            db.session.rollback()

            return render_template('signup.html', form=form, admins=admins(),
                                   year=datetime.now().year,)

        except Exception:
            logger.exception('signup unexpected error')
            flash(
                'Failed to register account! \
                    Try again or check the server logs.',
                category='danger')
            db.session.rollback()

            return render_template('signup.html', form=form, admins=admins(),
                                   year=datetime.now().year,)

        else:
            login_user(user, remember=True)
            flash('Account created and logged in!', category='success')

            return redirect(next_url)

    return render_template('signup.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/login', methods=['POST', 'GET'])
def login() -> Response | str:
    """
    Authenticate user by username or email and password.

    Methods:
      - GET: Render login form.
      - POST: Validate form, lookup user (username then email),
              verify password and log in.

    Returns:
      - On GET or failed auth: render_template('login.html', form=form, ...)
      - On success: redirect to next_url (string)
      - On DB errors: render_template with error flash
    """

    next_url: str = request.args.get('next') or url_for('home')

    if current_user.is_authenticated:
        return redirect(next_url)

    form = Login()

    if form.validate_on_submit():
        try:
            # try username first, then email
            user: Optional[User] = db.session.scalar(
                select(User).where(User.username == form.name_or_email.data)
            )
            if not user:
                user: Optional[User] = db.session.scalar(
                    select(User).where(User.email == form.name_or_email.data)
                )

        except (NoSuchTableError, DatabaseError) as db_err:
            logger.error('DB exception (login): %s', db_err)
            flash('Database not ready!', category='error')

            return render_template('login.html', form=form, admins=admins())

        except Exception:
            logger.exception('login unexpected error')
            flash('An unexpected error occurred. Try again later!',
                  category='error')

            return render_template('login.html', form=form, admins=admins())

        if not user:
            flash('Username or Email does not exist. Consider signing up.',
                  'error')
            return render_template('login.html', form=form, admins=admins(),
                                   year=datetime.now().year,)

        # check password and login
        try:
            if not user.affirm_password(form.password.data):
                flash('Invalid Password', category='danger')
                return render_template(
                    'login.html', form=form, admins=admins())

            login_user(user, remember=True)
            flash('Logged in successfully!', category='success')
            return redirect(next_url)

        except Exception:
            logger.exception("exception during login/affirm_password")
            flash('Login failed. Try again!', category='error')

            return render_template('login.html', form=form, admins=admins(),
                                   year=datetime.now().year,)

    return render_template('login.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/admin-dashboard')
@login_required
@admins_only
def dashboard() -> Response | str:
    """
    Render admin dashboard with aggregated resources.

    Methods:
      - GET: Query Projects, Clients, Team, Skills, Experience and render
             dashboard.

    Returns:
      - render_template('admin_dashboard.html', projects=..., clients=..., ...)
      - If not authenticated: redirect to login with next parameter
    """

    if not current_user.is_authenticated:
        return redirect(login_url(
            login_view=login_manager.login_view,
            next_url=request.args.get('next') or request.url,
            next_field='redirect'
        ))

    try:
        projects: Sequence[Projects] = db.session.scalars(
            select(Projects).order_by(Projects.created_at.desc())).all()

        clients: Sequence[Clients] = db.session.scalars(
            select(Clients).order_by(Clients.client_name.desc())
        ).all()

        team_members: Sequence[Team] = db.session.scalars(
            select(Team).order_by(Team.member_name.desc())).all()

        skills: Sequence[Skills] = db.session.scalars(
            select(Skills).order_by(Skills.proficiency.desc())).all()

        experiences: Sequence[Experience] = db.session.scalars(
            select(Experience).order_by(Experience.category.desc())).all()

    except NoSuchTableError as nste:
        logger.warning('dashboard DB table missing: %s', nste)

    except Exception:
        logger.exception('admin_dashboard(): unexpected error')

    return render_template('admin_dashboard.html',
                           admins=admins(),
                           projects=projects,
                           clients=clients,
                           team_members=team_members,
                           skills=skills,
                           experiences=experiences,
                           year=datetime.now().year,
                           )


@app.route('/admin-dashboard/users')
@login_required
@admins_only
def manage_users() -> str:
    """
    List all users for admin management.

    Methods:
      - GET: Query User table and render admin users page.

    Returns:
      - render_template('admin_users.html', users=all_users, ...)
    """

    try:
        all_users: Sequence[User] = db.session.scalars(
            select(User).order_by(User.username)).all()

    except (NoSuchTableError, DatabaseError) as db_err:
        logger.error('manage_users DB error: %s', db_err)
        flash('Database not ready!',
              category='error')
        all_users = []

    except Exception:
        logger.exception('manage_users unexpected error')
        all_users = []

    return render_template('admin_users.html',
                           admins=admins(),
                           users=all_users,
                           year=datetime.now().year)


@app.route('/admin-dashboard/promote-user/<int:user_id>', methods=['POST'])
@login_required
@admins_only
def promote_user(user_id: int) -> Response:
    """
    Promote a user to admin (set is_admin=True).

    Methods:
      - POST: Update user.is_admin and commit.

    Returns:
      - Redirect back to referring page or manage_users.
      - Flashes success or error messages on DB failure.
    """

    try:
        user: Optional[User] = db.session.get(User, user_id)
        if not user:
            flash('User not found!', category='danger')
            return redirect(request.referrer or url_for('manage_users'))

        if user.is_admin:
            flash('User is already an admin', category='info')
            return redirect(request.referrer or url_for('manage_users'))

        user.is_admin = True
        db.session.commit()
        flash(f'User {user.username} promoted to admin', category='success')

    except (OperationalError, DatabaseError) as db_err:
        logger.error('promote_user DB error: %s', db_err)
        flash('Database error while promoting user', category='error')
        db.session.rollback()

    except Exception:
        logger.exception('promote_user unexpected error')
        flash('Failed to promote user', category='error')
        db.session.rollback()

    return redirect(request.referrer or url_for('manage_users'))


@app.route('/')
def home() -> str:
    """
    Home page: load team members and clients.

    Methods:
      - GET: Query Team and Clients and render public index.

    Returns:
      - render_template('index.html', team_members=..., clients=..., ...)
    """
    team_members = []
    clients = []
    try:
        team_members: Sequence[Team] = db.session.scalars(
            select(Team).order_by(Team.member_name.desc())).all()

        clients: Sequence[Clients] = db.session.scalars(
            select(Clients).order_by(Clients.client_name.desc())
        ).all()

    except NoSuchTableError as nste:
        logger.warning('home: DB table missing: %s', nste)
        team_members = []
        clients = []

    except Exception:
        logger.exception('home unexpected exception')
        team_members = []
        clients = []

    return render_template('index.html',
                           whatsapp=environ.get('WHATSAPP'),
                           team_members=team_members,
                           admins=admins(),
                           clients=clients,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/add-member', methods=['POST', 'GET'])
@login_required
@admins_only
def add_member() -> Response | str:
    """
    Add a team member (admin only).

    Methods:
      - GET: Render add-member form.
      - POST: Validate form and create Team entry.

    Returns:
      - On GET or validation failure: render add-member template.
    """

    form = TeamForm()

    if form.validate_on_submit():
        try:
            team_member: Team = Team(
                member_name=form.member_name.data,
                role=form.role.data,
                portfolio_link=form.portfolio_link.data,
                github_link=form.github_link.data
            )
            db.session.add(team_member)
            db.session.commit()
            flash('New member added!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('add_member IntegrityError: %s', ie)
            flash('Portfolio link or github account link already exist! \
            ...Verify if you\'re not using someone\'s link as yours',
                  category='warning')
            db.session.rollback()

        except Exception:
            logger.exception('add_member unexpected error')
            flash('Failed to add new member!', category='error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-member.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/admin-dashboard/update-member-profile/<int:member_id>',
           methods=['POST', 'GET'])
@login_required
@admins_only
def update_member_profile(member_id: int) -> Response | str:
    """
    Update an existing team member (admin only).

    Methods:
      - GET: Populate form with current member data and render form.
      - POST: Validate and update member via update() call.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On failure: render add-member.html with form and flash messages
    """

    form = TeamForm()

    member_to_update_profile: Optional[Team] = db.session.get(Team, member_id)

    if not member_to_update_profile:
        flash('member does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or url_for('dashboard'))

    # populate fields correctly
    form.member_name.data = member_to_update_profile.member_name
    form.role.data = member_to_update_profile.role
    form.portfolio_link.data = member_to_update_profile.portfolio_link
    form.github_link.data = member_to_update_profile.github_link

    if form.validate_on_submit():
        try:
            db.session.execute(
                update(Team).where(Team.id == member_id).values(
                    role=form.role.data,
                    portfolio_link=form.portfolio_link.data,
                    github_link=form.github_link.data)
            )
            db.session.commit()

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('update_member_profile IntegrityError: %s', ie)
            flash('The updated portfolio link or github account link seems \
                to exist already!',
                  category='warning')
            db.session.rollback()

        except Exception:
            logger.exception('update_member_profile unexpected error')
            flash('Failed to update member!', category='error')

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-member.html',
                           admins=admins(),
                           form=form,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/delete-member/<int:member_id>')
@login_required
@admins_only
def delete_member(member_id: int) -> Response:
    """
    Delete a team member by id (admin only).

    Methods:
      - GET: Delete the member and redirect.

    Returns:
      - Redirect to dashboard (or next param) with flash indicating result.
    """

    member_to_delete: Optional[Team] = db.session.get(Team, member_id)

    if not member_to_delete:
        flash('member does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    db.session.delete(member_to_delete)
    db.session.commit()
    flash('member deleted!', category='success')
    next_url = request.args.get('next') or url_for('dashboard')

    return redirect(next_url)


@app.route('/admin-dashboard/add-client', methods=['POST', 'GET'])
@login_required
@admins_only
def add_client() -> Response | str:
    """
    Add a client with optional image upload (admin only).

    Methods:
      - GET: Render add-client form.
      - POST: Validate ClientForm; save uploaded image to UPLOAD_FOLDER using
              secure_filename; set client.client_img and commit.

    Returns:
      - On GET/validation failure: render add-client template.
      - On success: redirect to dashboard (or next param)
      - On error: redirect back with flash
    """

    form = ClientForm()

    if form.validate_on_submit():
        try:
            new_client: Clients = Clients(
                client_name=form.client_name.data,
                profession=form.profession.data,
                testimonial=form.testimonial.data
            )

            image = form.client_img.data
            if image.filename == '':
                flash('No image selected!', category='danger')
                # return redirect(request.url)

            if image and form.allowed_img_files(image.filename):
                img_name: str = secure_filename(image.filename)
                image.save(path.join(app.config['UPLOAD_FOLDER'], img_name))

            # add project img str path to db
            default_img = 'default_client_pic.jpg'
            new_client.client_img = img_name or default_img

            db.session.add(new_client)
            db.session.commit()
            flash('Client added!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('add_client IntegrityError: %s', ie)
            flash('Kindly rename the image...Current name already exist!')
            db.session.rollback()

        except Exception:
            logger.exception('add_client unexpected error')
            flash('Failed to add client!', category='error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template(
        'add-client.html',
        form=form,
        admins=admins(),
        year=datetime.now().year,
    )


@app.route('/admin-dashboard/delete-client/<int:client_id>')
@login_required
@admins_only
def delete_client(client_id: int) -> Response:
    """
    Delete a client by id (admin only).

    Methods:
      - GET: Delete client and commit.

    Returns:
      - Redirect to dashboard (or next param) with flash indicating
        success/error.
    """

    client_to_delete: Optional[Clients] = db.session.get(Clients, client_id)

    if not client_to_delete:
        flash('client does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    db.session.delete(client_to_delete)
    db.session.commit()
    flash('client deleted!', category='success')
    next_url = request.args.get('next') or url_for('dashboard')

    return redirect(next_url)


@app.route('/admin-dashboard/update-client-profile/<int:client_id>',
           methods=['POST', 'GET'])
@login_required
@admins_only
def update_client_profile(client_id: int) -> Response | str:
    """
    Update a client's profile and image (admin only).

    Methods:
      - GET: Populate form with client's current data and render form.
      - POST: Accept optional image replacement, validate inputs, and update
            DB.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On validation or DB error: render add-client.html or redirect with
        flash
    """

    form = ClientForm()

    client_to_update_profile: Optional[Clients] = db.session.get(Clients,
                                                                 client_id)

    if not client_to_update_profile:
        flash('Project does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or url_for('dashboard'))

    form.client_name.data = client_to_update_profile.client_name
    form.testimonial.data = client_to_update_profile.testimonial
    form.profession.data = client_to_update_profile.profession

    if form.validate_on_submit():
        img_name = None
        image = form.client_img.data

        if image and getattr(image, 'filename', '') == '':
            flash('No image selected!', category='danger')

        if image and form.allowed_img_files(image.filename):
            img_name: str = secure_filename(image.filename)
            image.save(path.join(app.config['UPLOAD_FOLDER'], img_name))

        updated_image = img_name

        try:
            db.session.execute(
                update(Clients).where(
                    Clients.id == client_id
                ).values(
                    client_name=form.client_name.data,
                    profession=form.profession.data,
                    testimonial=form.testimonial.data,
                    client_img=updated_image or
                    client_to_update_profile.client_img
                ))
            db.session.commit()
            flash('Updated successfully!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('update_client_profile IntegrityError: %s', ie)
            flash('Kindly rename the image...Current name already exist!',
                  category='danger')
            db.session.rollback()

        except Exception:
            flash('Failed to update client\'s profile!', 'error')
            logger.exception('update_client_profile unexpected error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-client.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/skills')
def skills() -> str:
    """
    Skills page: returns skills and experience ordered for display.

    Methods:
      - GET: Query Skills and Experience and render skills page.

    Returns:
      - render_template('skills.html', skills=..., experience=..., ...)
    """

    try:
        skills: Sequence[Skills] = db.session.scalars(
            select(Skills).order_by(Skills.proficiency.desc())
        ).all()

        experience: Sequence[Experience] = db.session.scalars(
            select(Experience).order_by(Experience.end_year.desc())
        ).all()

    except NoSuchTableError as nste:
        logger.warning('skills NoSuchTableError: %s', nste)

    except Exception:
        logger.exception('skills unexpected error')

    return render_template('skills.html',
                           skills=skills,
                           experience=experience,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/admin-dashboard/add-skill', methods=['POST', 'GET'])
@login_required
@admins_only
def add_skill() -> Response | str:
    """
    Add a skill (admin only).

    Methods:
      - GET: Render add-skill form.
      - POST: Validate form and add Skills record.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On failure: render add-skill.html with flash
    """

    form = SkillsForm()

    if form.validate_on_submit():
        try:
            new_skill: Skills = Skills(
                name=form.skill_name.data,
                proficiency=form.proficiency.data if form.proficiency.data < 100 else int(
                    form.proficiency.data),
                suipjhaps=current_user
            )
            db.session.add(new_skill)
            db.session.commit()
            flash('Skill added!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('add_skill IntegrityError: %s', ie)
            flash(f'{form.skill_name.data} already exist!', category='warning')
            db.session.rollback()

        except Exception:
            logger.exception('add_skill unexpected error')
            flash('Failed to add new skill!...try again', category='error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-skill.html',
                           admins=admins(),
                           form=form,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/update-skill/<int:skill_id>',
           methods=['POST', 'GET'])
@login_required
@admins_only
def update_skill(skill_id: int) -> Response | str:
    """
    Update a skill's proficiency (admin only).

    Methods:
      - GET: Populate form with current skill data.
      - POST: Validate and update proficiency.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On error: redirect back with flash
    """

    form = SkillsForm()

    skill_to_update: Optional[Skills] = db.session.get(Skills, skill_id)

    if not skill_to_update:
        flash('Skill does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or url_for('dashboard'))

    form.skill_name.data = skill_to_update.name

    if form.validate_on_submit():
        try:
            db.session.execute(
                update(Skills).where(Skills.id == skill_id).values(
                    proficiency=form.proficiency.data)
            )
            db.session.commit()

            return redirect(request.args.get('next') or url_for('dashboard'))

        except Exception:
            logger.exception('update_skill unexpected error')
            flash('Failed to update skill!', category='error')
            return redirect(request.url or url_for('dashboard'))

    return render_template('add-skill.html',
                           admins=admins(),
                           form=form,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/delete-skills/<int:skill_id>')
@login_required
@admins_only
def delete_skill(skill_id: int) -> Response:
    """
    Delete a skill by id (admin only).

    Methods:
      - GET: Delete and commit.

    Returns:
      - Redirect to dashboard with flash indicating result.
    """
    skill_to_delete: Optional[Skills] = db.session.get(Skills, skill_id)

    if not skill_to_delete:
        flash('Skill does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    db.session.delete(skill_to_delete)
    db.session.commit()
    flash('Skill deleted!', category='success')
    next_url = request.args.get('next') or url_for('dashboard')

    return redirect(next_url)


@app.route('/admin-dashboard/add-new-experience', methods=['POST', 'GET'])
@login_required
@admins_only
def add_experience() -> Response | str:
    """
    Add an experience record (admin only).

    Methods:
      - GET: Render experience form.
      - POST: Validate and create Experience entry.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On failure: redirect back with flash
    """

    form = ExperienceForm()

    if form.validate_on_submit():
        try:
            new_experience: Experience = Experience(
                category=form.category.data,
                role=form.role.data,
                start_year=form.start_year.data,
                end_year=form.end_year.data,
                experience_field=form.experience_field.data,
                suipjhaps=current_user
            )
            db.session.add(new_experience)
            db.session.commit()
            flash('New Experience added!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except Exception:
            logger.exception('add_experience unexpected error')
            flash('Failed to add new experience!...try again',
                  category='error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-experience.html',
                           admins=admins(),
                           form=form,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/delete-experience/<int:experience_id>')
@login_required
@admins_only
def delete_experience(experience_id: int) -> Response:
    """
    Delete an experience record (admin only).

    Methods:
      - GET: Delete and commit.

    Returns:
      - Redirect to dashboard with flash indicating result.
    """
    experience_to_delete: Optional[Experience] = db.session.get(Experience,
                                                                experience_id)

    if not experience_to_delete:
        flash('No such experience!', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    db.session.delete(experience_to_delete)
    db.session.commit()
    flash('Experience deleted!', category='success')
    next_url = request.args.get('next') or url_for('dashboard')

    return redirect(next_url)


@app.route('/my-projects')
def projects() -> str:
    """
    Render read-only projects listing for public visitors.

    Methods:
      - GET: Query Projects and render projects.html.

    Returns:
      - render_template('projects.html', all_projects=all_projects, ...)
    """

    try:
        all_projects: Sequence[Projects] = db.session.scalars(
            select(Projects).order_by(Projects.created_at)
        ).all()

    except (NoSuchTableError, DatabaseError) as db_err:
        logger.warning('DB exception (all_projects): %s', db_err)

    except Exception:
        logger.exception('all_projects(): unexpected error')

    return render_template('projects.html',
                           admins=admins(),
                           all_projects=all_projects,
                           year=datetime.now().year,)


@app.route('/admin-dashboard/add-project', methods=['POST', 'GET'])
@login_required
@admins_only
def add_project() -> Response | str:
    """
    Create a new project (admin only).

    Methods:
      - GET: Render add-project form.
      - POST: Validate form; save image and file uploads to UPLOAD_FOLDER and
              create Projects record with filenames stored in DB.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On failure: render add-project.html or redirect with flash
    """

    form = Project()

    if form.validate_on_submit():
        try:
            project = Projects(
                title=form.title.data,
                category=form.category.data,
                description=form.description.data,
                demo_url=form.demo_url.data,
                github_url=form.github_url.data,
                apk_size=str(form.apk_size.data),
                platform=form.platform.data,
                tech_stack=form.tech_stack.data,
                figma_canva_url=form.figma_url.data,
                version=form.current_version.data,
                suipjhaps=current_user
            )

            if form.created_at.data:
                project.created_at = form.created_at.data

            if form.github_stars:
                project.github_stars = form.github_stars.data

            if form.responsive.data:
                project.responsive = form.responsive.data

            if form.is_live:
                project.is_live = form.is_live

            image = form.image.data
            if image and form.allowed_img_files(image.filename):
                img_name: str = secure_filename(image.filename)
                image.save(path.join(app.config['UPLOAD_FOLDER'], img_name))

            # add project img str path to db
            project.image = img_name

            if 'file_name' not in request.files or \
                    not isinstance(
                        request.files.get('file_name'), FileStorage
                    ):
                flash('No file part!', category='danger')
                return redirect(request.url)

            file = request.files.get('file_name') or form.file_name.data

            if file.filename == '':
                flash('No file selected!', category='danger')
                # return redirect(request.url)

            if file and form.allowed_img_files(file.filename):
                filename: str = secure_filename(file.filename)
                file.save(path.join(app.config['UPLOAD_FOLDER'], filename))

            # add project file str path to db
            project.file_name = filename or None

            db.session.add(project)
            db.session.commit()
            flash('Project added!', category='success')
            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('add_project IntegrityError: %s', ie)
            flash('Project URL or Github URL or Demo URL exist already',
                  category='error')
            db.session.rollback()

        except Exception:
            logger.exception('add_project unexpected error')
            flash('Failed to add project...', 'error')
            db.session.rollback()

            return redirect(request.url or url_for('dashboard'))

    return render_template('add-project.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/admin-dashboard/delete-project/<int:project_id>')
@login_required
@admins_only
def delete_project(project_id: int) -> Response:
    """
    Delete a project by id (admin only).

    Methods:
      - GET: Delete project and commit.

    Returns:
      - Redirect to dashboard with flash indicating result.
    """

    project_to_delete: Optional[Projects] = db.session.get(Projects,
                                                           project_id)

    if not project_to_delete:
        flash('Project does not exist', category='danger')
        next_url = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    db.session.delete(project_to_delete)
    db.session.commit()
    flash('Project deleted!', category='success')
    next_url: str = request.args.get('next') or url_for('dashboard')

    return redirect(next_url)


@app.route('/admin-dashboard/update-project/<int:project_id>',
           methods=['POST', 'GET'])
@login_required
@admins_only
def update_project(project_id: int) -> Response | str:
    """
    Update an existing project and optionally replace files (admin only).

    Methods:
      - GET: Populate form with existing project data.
      - POST: Save optional new image/file and update DB fields.

    Returns:
      - On success: redirect to dashboard (or next param)
      - On error: render add-project.html or redirect with flash
    """

    form = Project()

    project_to_update: Optional[Projects] = db.session.get(Projects,
                                                           project_id)

    if not project_to_update:
        flash('Project does not exist', category='danger')
        next_url: Optional[str] = request.args.get('next')

        return redirect(next_url or request.url or url_for('dashboard'))

    # populating with existing db details using .data
    form.title.data = project_to_update.title
    form.description.data = project_to_update.description
    form.demo_url.data = project_to_update.demo_url
    form.github_url.data = project_to_update.github_url
    form.current_version.data = project_to_update.version
    form.tech_stack.data = project_to_update.tech_stack
    form.apk_size.data = project_to_update.apk_size
    form.platform.data = project_to_update.platform
    form.github_stars.data = project_to_update.github_stars
    form.figma_url.data = project_to_update.figma_canva_url

    if form.validate_on_submit():
        img_name = None
        filename = None
        image = form.image.data

        if image and form.allowed_img_files(image.filename):
            img_name: str = secure_filename(image.filename)
            image.save(path.join(app.config['UPLOAD_FOLDER'], img_name))

        updated_image = img_name

        if 'file_name' not in request.files or \
            not isinstance(
                request.files.get('file_name'), FileStorage):
            flash('No file part!', category='danger')
            return redirect(request.url)

        file = request.files.get('file_name') or form.file_name.data

        if getattr(file, 'filename', '') == '':
            flash('No file selected!', category='danger')

        if file and form.allowed_img_files(file.filename):
            filename: str = secure_filename(file.filename)
            file.save(path.join(app.config['UPLOAD_FOLDER'], filename))

        updated_file_name = filename

        try:
            db.session.execute(
                update(Projects).where(
                    Projects.id == project_id
                ).values(
                    title=form.title.data,
                    category=form.category.data or project_to_update.category,
                    description=form.description.data or
                    project_to_update.description,
                    demo_url=form.demo_url.data,
                    github_url=form.github_url.data,
                    current_version=form.current_version.data,
                    tech_stack=form.tech_stack.data,
                    image=updated_image or project_to_update.image,
                    file_name=updated_file_name or project_to_update.file_name,
                    responsive=form.responsive.data or
                    project_to_update.responsive,
                    github_stars=form.github_stars.data,
                    platform=form.platform.data,
                    is_live=form.is_live.data or project_to_update.is_live,
                    figma_canva_url=form.figma_url.data,
                    apk_size=str(
                        form.apk_size.data) or project_to_update.apk_size,
                )
            )
            db.session.commit()
            flash('Updated successfully!', category='success')

            return redirect(request.args.get('next') or url_for('dashboard'))

        except IntegrityError as ie:
            logger.warning('update_project IntegrityError: %s', ie)
            flash('Project URL or Github URL or Demo URL exist already',
                  category='error')
            db.session.rollback()

        except Exception:
            logger.exception('update_project unexpected error')
            flash('Failed to update project!', 'error')
            db.session.rollback()
            return redirect(request.url or url_for('dashboard'))

    return render_template('add-project.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/services')
def services() -> str:
    """
    Render services page (public).

    Methods:
      - GET: Render services.html.

    Returns:
      - render_template('services.html', ...)
    """

    return render_template('services.html',
                           whatsapp=environ.get('WHATSAPP'),
                           admins=admins(),
                           year=datetime.now().year,)


@app.route('/about')
def about() -> str:
    """
    About page: compute project & client counts and render about.html.

    Methods:
      - GET: Query Projects and Clients, compute counts and render page.

    Returns:
      - render_template('about.html', projects_num=int, clients_num=int, ...)
    """

    number_of_projects: int = 0
    number_of_clients: int = 0

    try:
        all_projects: Sequence[Projects] = db.session.scalars(
            select(Projects)).all()

        clients: Sequence[Clients] = db.session.scalars(
            select(Clients)).all()

    except (NoSuchTableError, DatabaseError) as db_err:
        logger.warning('DB exception (no_of_projects): %s', db_err)

    except Exception:
        logger.exception('no_of_projects(): unexpected error')

    else:
        if all_projects:
            for _ in all_projects:
                number_of_projects += 1

        if clients:
            for _ in clients:
                number_of_clients += 1

    return render_template('about.html',
                           admins=admins(),
                           year=datetime.now().year,
                           projects_num=number_of_projects,
                           clients_num=number_of_clients,)


@app.route('/contact-form', methods=['POST', 'GET'])
def contact_form() -> Response | str:
    """
    Contact form: send email using SMTP_SSL (Gmail).

    Methods:
      - GET: Render contact form.
      - POST: Validate ContactForm and send email using MAIL & PASSWORD env
      vars.

    Returns:
      - On GET or failure: render_template('contact.html', form=form, ...)
      - On success: render_template('contact.html', is_sent=True, ...)
    """

    form = ContactForm()

    if form.validate_on_submit():
        email: str = form.email.data
        name: str = form.name.data
        subject: Optional[str] = form.subject.data
        message: str = form.message.data

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com') as mail_server:
                mail_server.login(user=environ.get('MAIL'),
                                  password=environ.get('PASSWORD'))

                mail = EmailMessage()
                mail['From'] = environ.get('MAIL')
                mail['To'] = email
                mail['Subject'] = subject or f'{name}'
                mail.set_content(message)

                mail_server.send_message(mail)

        except ConnectionError:
            logger.warning('contact_form(): ConnectionError')
            flash('Could not connect to email servers! Try resending', 'error')

        except Exception:
            logger.exception('contact_form(): unexpected error')
            flash('Failed to send message!', 'error')
            return redirect(url_for('contact_form'))

        else:
            return render_template('contact.html',
                                   form=form,
                                   is_sent=True,
                                   admins=admins(),
                                   year=datetime.now().year,
                                   github=environ.get('GITHUB'),
                                   tiktok=environ.get('TIKTOK'),
                                   youtube=environ.get('YOUTUBE'),
                                   linked_in=environ.get('LINKED_IN'),)

    return render_template('contact.html',
                           form=form,
                           admins=admins(),
                           year=datetime.now().year,
                           github=environ.get('GITHUB'),
                           tiktok=environ.get('TIKTOK'),
                           youtube=environ.get('YOUTUBE'),
                           linked_in=environ.get('LINKED_IN'),)


@app.route('/about/read-more')
def read_more() -> str:
    """
    Render a detailed 'read more about me' page.

    Methods:
      - GET: Render read-more.html. (No POST)

    Returns:
      - render_template('read-more.html', ...)
    """

    return render_template('read-more.html',
                           admins=admins(),
                           year=datetime.now().year,
                           github=environ.get('GITHUB'),
                           youtube=environ.get('YOUTUBE'),
                           linked_in=environ.get('LINKED_IN'),)


@app.route('/download-file/<path:cv>')
def download_cv(cv) -> Response:
    """
    Serve a file from UPLOAD_FOLDER as attachment.

    Methods:
      - GET: Serve file at given relative path (cv) from UPLOAD_FOLDER.

    Args:
      - cv (str): file name relative to UPLOAD_FOLDER.

    Returns:
      - send_from_directory(..., as_attachment=True) on success.
      - abort(404) if file not found.
    """

    try:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], cv, as_attachment=True
        )

    except FileNotFoundError:
        logger.warning('download_cv(): FileNotFoundError for %s', cv)
        abort(404)


@app.route('/logging-out')
def logout() -> Response:
    """
    Log out the current user and redirect to home (or next).

    Methods:
      - GET: Log out authenticated user.

    Returns:
      - Redirect to home or next parameter.
    """

    if current_user.is_authenticated:
        logout_user()
        return redirect(request.args.get('next') or url_for('home'))


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(environ.get('PORT', 5000)),
        debug=True
    )
