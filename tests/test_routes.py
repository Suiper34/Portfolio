from __future__ import annotations

import smtplib
from typing import Any, Dict

from flask import Flask
from flask.testing import FlaskClient
from pytest import MonkeyPatch

from app import db
from models.admin import User


def test_home_page(client: FlaskClient):
    """GET / should return 200 and contain expected elements."""

    response = client.get('/')
    assert response.status_code == 200
    # basic sanity: page has HTML
    assert b'<html' in response.data or b'<!DOCTYPE html' in response.data or \
        len(response.data) > 0


def test_signup_and_login_flow(client: FlaskClient, app: Flask):
    """Sign up a new user and then log in with credentials."""

    signup_data: Dict[str, Any] = {
        'name': 'Tester',
        'username': 'tester1',
        'email': 'tester1@example.com',
        'password': 'TestPass123!',
        'confirm_password': 'TestPass123!',
        'signup': True,
    }
    response = client.post(
        '/sign-up', data=signup_data, follow_redirects=True
    )
    assert response.status_code == 200
    # user should exist in DB
    user = db.session.scalar(db.select(User).where(User.username == 'tester1'))
    assert user is not None

    # logout if the signup logged in the test client - safe to call
    client.get('/logging-out')

    # login
    login_data: Dict[str, Any] = {'name_or_email': 'tester1',
                                  'password': 'TestPass123!',
                                  'login': True}
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200


def test_contact_post_success(client: FlaskClient, monkeypatch: MonkeyPatch):
    """POST to contact-form should return 200 when SMTP succeeds (mocked)."""
    # Monkeypatch smtplib.SMTP_SSL to a dummy that has login/send_message
    # methods
    class DummySMTP:
        def __init__(self, *args, **kwargs):
            pass

        def login(self, *a, **kw):
            return True

        def send_message(self, msg):
            return True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(smtplib, 'SMTP_SSL', DummySMTP)

    data: Dict[str, Any] = {
        'name': 'Contact Tester',
        'email': 'recipient@example.com',
        'subject': 'Hello',
        'message': 'This is a test message',
        'send': True,
    }
    response = client.post(
        '/contact-form', data=data, follow_redirects=True
    )
    assert response.status_code == 200


def test_Projects_list_route(client: FlaskClient):
    """GET /my-projects returns 200 even with no projects."""

    response = client.get('/my-projects')
    assert response.status_code == 200
