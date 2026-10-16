import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import LoginSession, Profile, User

router = APIRouter(prefix='/api', tags=['Accounts and profile'])
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
COOKIE = 'cv_session'


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(default='', max_length=50)
    address: str = Field(default='', max_length=500)
    education: str = Field(default='', max_length=10000)
    skills: str = Field(default='', max_length=10000)
    experience: str = Field(default='', max_length=10000)
    projects: str = Field(default='', max_length=10000)
    desired_position: str = Field(default='', max_length=200)
    location: str = Field(default='', max_length=200)
    salary: str = Field(default='', max_length=200)
    wishes: str = Field(default='', max_length=10000)


def mutation_guard(request: Request):
    # A cross-origin HTML form cannot send this header. No CORS is enabled.
    if request.headers.get('x-requested-with') != 'cv-app':
        raise HTTPException(403, 'Yêu cầu không hợp lệ. Hãy tải lại trang.')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Nguồn yêu cầu không hợp lệ.')


def token_hash(request: Request):
    token = request.cookies.get(COOKIE, '')
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request, db: Session = Depends(get_db)):
    session = db.get(LoginSession, token_hash(request))
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, 'Vui lòng đăng nhập để tiếp tục.')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Phiên đăng nhập không còn hợp lệ.')
    return user


def public_user(user):
    return {'id': user.id, 'email': user.email}


def start_session(user, request, response, db):
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request)))
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        user_id=user.id, expires_at=utcnow() + timedelta(hours=settings.session_hours)))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure,
                        samesite='strict', max_age=settings.session_hours * 3600, path='/')
    return public_user(user)


@router.post('/auth/register', status_code=201, dependencies=[Depends(mutation_guard)])
def register(data: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    user = User(email=str(data.email), password_hash=hasher.hash(data.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Email này đã được đăng ký.')
    return start_session(user, request, response, db)


@router.post('/auth/login', dependencies=[Depends(mutation_guard)])
def login(data: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email)))
    try:
        hasher.verify(user.password_hash if user else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, 'Email hoặc mật khẩu không đúng.')
    if not user:
        raise HTTPException(401, 'Email hoặc mật khẩu không đúng.')
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(data.password)
    return start_session(user, request, response, db)


@router.post('/auth/logout', status_code=204, dependencies=[Depends(mutation_guard)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request)))
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=settings.cookie_secure, httponly=True, samesite='strict')


@router.get('/auth/me')
def me(user: User = Depends(current_user)):
    return public_user(user)


def profile_output(profile):
    if not profile:
        return None
    return {'full_name': profile.full_name, **(profile.contact or {}),
            **{key: getattr(profile, key) or '' for key in ('education', 'skills', 'experience', 'projects')},
            **(profile.preferences or {}), 'updated_at': profile.updated_at.isoformat()}


@router.get('/profile')
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return profile_output(db.scalar(select(Profile).where(Profile.user_id == user.id)))


@router.put('/profile', dependencies=[Depends(mutation_guard)])
def save_profile(data: ProfileInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
    profile.full_name = data.full_name
    profile.contact = {'phone': data.phone, 'address': data.address}
    for key in ('education', 'skills', 'experience', 'projects'):
        setattr(profile, key, getattr(data, key))
    profile.preferences = {key: getattr(data, key) for key in ('desired_position', 'location', 'salary', 'wishes')}
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Hồ sơ vừa thay đổi ở cửa sổ khác. Hãy tải lại trang.')
    db.refresh(profile)
    return profile_output(profile)
