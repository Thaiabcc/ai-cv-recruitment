import hashlib
import os
import unittest
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.accounts import COOKIE, hasher, utcnow
from app.database import engine as mysql_engine, get_db
from app.main import app
from app.models import Base, LoginSession, Profile, User

HEADERS = {'X-Requested-With': 'cv-app'}


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.mysql = os.environ.get('TEST_MYSQL') == '1'
        self.engine = mysql_engine if self.mysql else create_engine(
            'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        if not self.mysql:
            Base.metadata.create_all(self.engine)
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()

        def test_db():
            with Session(bind=self.connection, join_transaction_mode='create_savepoint') as db:
                yield db
        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app, headers=HEADERS)
        self.other = TestClient(app, headers=HEADERS)
        self.email = f'test-{uuid.uuid4().hex}@example.com'
        self.credentials = {'email': self.email, 'password': 'Test-password-123'}

    def tearDown(self):
        self.client.close()
        self.other.close()
        app.dependency_overrides.clear()
        self.transaction.rollback()
        self.connection.close()
        if not self.mysql:
            self.engine.dispose()

    def register(self, client=None, credentials=None):
        response = (client or self.client).post('/api/auth/register', json=credentials or self.credentials)
        self.assertEqual(response.status_code, 201, response.text)
        return response

    def test_register_hash_and_cookie(self):
        response = self.register()
        self.assertNotIn('password', response.text)
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        with Session(self.connection) as db:
            user = db.scalar(select(User).where(User.email == self.email))
            self.assertTrue(hasher.verify(user.password_hash, self.credentials['password']))
            self.assertNotEqual(user.password_hash, self.credentials['password'])
            session = db.scalar(select(LoginSession).where(LoginSession.user_id == user.id))
            self.assertEqual(session.token_hash, hashlib.sha256(self.client.cookies[COOKIE].encode()).hexdigest())

    def test_duplicate_and_validation(self):
        self.register()
        self.assertEqual(self.other.post('/api/auth/register', json=self.credentials).status_code, 409)
        for data in [dict(self.credentials, password='123'), dict(self.credentials, email='invalid')]:
            self.assertEqual(self.other.post('/api/auth/register', json=data).status_code, 422)

    def test_login_logout_and_revocation(self):
        self.register()
        old_token = self.client.cookies[COOKIE]
        self.assertEqual(self.client.post('/api/auth/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.other.cookies.set(COOKIE, old_token)
        self.assertEqual(self.other.get('/api/profile').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json=dict(self.credentials, password='wrong-password')).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json=self.credentials).status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me').json()['email'], self.email)

    def test_anonymous_and_csrf(self):
        self.assertEqual(self.client.get('/api/profile').status_code, 401)
        self.assertEqual(self.client.put('/api/profile', json={'full_name': 'X'}).status_code, 401)
        self.assertEqual(self.client.get('/api/demo/recommendations').status_code, 401)
        with TestClient(app) as guest:
            self.assertEqual(guest.post('/api/auth/register', json=self.credentials).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/register', json=self.credentials, headers={'Origin': 'https://evil.example'}).status_code, 403)

    def test_profile_persistence_and_isolation(self):
        self.register()
        self.assertIsNone(self.client.get('/api/profile').json())
        payload = {'full_name': 'Nguyễn Văn A', 'phone': '0901234567', 'address': 'Hà Nội',
                   'education': 'Đại học', 'skills': 'Python, SQL', 'experience': 'Thực tập',
                   'projects': '<script>alert(1)</script>', 'desired_position': 'Backend',
                   'location': 'Hà Nội', 'salary': 'Thỏa thuận', 'wishes': 'Từ xa'}
        self.assertEqual(self.client.put('/api/profile', json=payload).status_code, 200)
        for key, value in payload.items():
            self.assertEqual(self.client.get('/api/profile').json()[key], value)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json=self.credentials)
        self.assertEqual(self.client.get('/api/profile').json()['skills'], 'Python, SQL')
        self.register(self.other, dict(self.credentials, email=f'other-{uuid.uuid4().hex}@example.com'))
        self.assertIsNone(self.other.get('/api/profile').json())
        self.other.put('/api/profile', json={'full_name': 'Other user'})
        self.assertEqual(self.client.get('/api/profile').json()['full_name'], payload['full_name'])
        self.assertEqual(self.other.get('/api/profile/1').status_code, 404)
        self.assertEqual(self.other.put('/api/profile', json=dict(payload, user_id=1)).status_code, 422)
        self.assertEqual(self.client.put('/api/profile', json=dict(payload, full_name='Updated')).status_code, 200)
        self.assertEqual(self.client.get('/api/profile').json()['full_name'], 'Updated')
        self.assertEqual(self.other.get('/api/profile').json()['full_name'], 'Other user')

    def test_expiry_and_invalid_token(self):
        self.register()
        with Session(bind=self.connection, join_transaction_mode='create_savepoint') as db:
            session = db.get(LoginSession, hashlib.sha256(self.client.cookies[COOKIE].encode()).hexdigest())
            session.expires_at = utcnow() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.client.get('/api/profile').status_code, 401)
        self.client.cookies.clear()
        self.client.cookies.set(COOKIE, 'forged-token')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_empty_and_oversized_profile(self):
        self.register()
        for payload in [{'full_name': '   '}, {'full_name': 'A', 'skills': 'a' * 10001}]:
            self.assertEqual(self.client.put('/api/profile', json=payload).status_code, 422)
        self.assertIn('no-store', self.client.get('/api/profile').headers['cache-control'])


if __name__ == '__main__':
    unittest.main()
