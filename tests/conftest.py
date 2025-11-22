from os import environ
from shutil import rmtree
from typing import Any, Generator

import pytest
from _pytest.tmpdir import TempPathFactory
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner

from app import app as flask_app
from app import cache as app_cache
from app import db as _db

# force simple cache + disable redis before the app module imports.
environ.setdefault('CACHE_TYPE', 'SimpleCache')
environ.setdefault('REDIS_URL', '')


@pytest.fixture(autouse=True)
def clear_cache():
    app_cache.clear()
    app.config['TESTING'] = True
    yield
    app_cache.clear()


@pytest.fixture(scope='session')
def temp_upload_dir(
    tmp_path_factory: TempPathFactory
) -> Generator[str, Any, None]:
    """Create a temporary upload folder for test run and cleanup afterwards."""

    a_dir = tmp_path_factory.mktemp('uploads')
    yield str(a_dir)
    rmtree(str(a_dir), ignore_errors=True)


@pytest.fixture(scope='session')
def app(
    temp_upload_dir: Generator[str, Any, None]
) -> Generator[Flask, Any, None]:
    """
    Configure the app for testing and create an in-memory database.

    - TESTING enabled
    - SQLite in-memory DB used for speed/isolation
    - CSRF disabled for form posts in tests
    - UPLOAD_FOLDER redirected to a temporary dir
    """

    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        UPLOAD_FOLDER=temp_upload_dir,
    )

    # create db tables
    with flask_app.app_context():
        _db.drop_all()
        _db.create_all()

        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app: Generator[Flask, Any, None]) -> FlaskClient:
    """Flask test client bound to the testing app."""
    return app.test_client()


@pytest.fixture
def runner(app: Generator[Flask, Any, None]) -> FlaskCliRunner:
    """CLI runner for invoking flask CLI commands in tests."""
    return app.test_cli_runner()
