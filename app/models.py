from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT, MEDIUMBLOB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


ID = BigInteger().with_variant(Integer, 'sqlite').with_variant(BIGINT(unsigned=True), 'mysql')


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='candidate')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    contact: Mapped[dict] = mapped_column(JSON, nullable=True)
    education: Mapped[str] = mapped_column(JSON, nullable=True)
    skills: Mapped[str] = mapped_column(JSON, nullable=True)
    experience: Mapped[str] = mapped_column(JSON, nullable=True)
    projects: Mapped[str] = mapped_column(JSON, nullable=True)
    preferences: Mapped[dict] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LoginSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class CV(Base):
    __tablename__ = 'cvs'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'), index=True)
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CVPhoto(Base):
    __tablename__ = 'cv_photos'
    __table_args__ = (UniqueConstraint('user_id', 'sha256', name='uq_cv_photo_owner_hash'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'), index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary().with_variant(MEDIUMBLOB, 'mysql'), deferred=True)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
