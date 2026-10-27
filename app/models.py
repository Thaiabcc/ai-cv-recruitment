from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT, MEDIUMBLOB, TIMESTAMP
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


class RecruitmentSource(Base):
    __tablename__ = 'recruitment_sources'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    domain: Mapped[str] = mapped_column(String(253), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ID, ForeignKey('recruitment_sources.id'))
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    salary_text: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SearchRun(Base):
    __tablename__ = 'search_runs'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'))
    cv_id: Mapped[int] = mapped_column(ID, ForeignKey('cvs.id'))
    status: Mapped[str] = mapped_column(String(20), default='queued')
    query_snapshot: Mapped[dict] = mapped_column(JSON)
    source_errors: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class SearchRunJob(Base):
    __tablename__ = 'search_run_jobs'
    search_run_id: Mapped[int] = mapped_column(ID, ForeignKey('search_runs.id'), primary_key=True)
    job_id: Mapped[int] = mapped_column(ID, ForeignKey('jobs.id'), primary_key=True)
    snapshot: Mapped[dict] = mapped_column(JSON)


class EvaluationBatch(Base):
    __tablename__ = 'evaluation_batches'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('users.id'), index=True)
    search_run_id: Mapped[int] = mapped_column(ID, ForeignKey('search_runs.id'), index=True)
    status: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    model: Mapped[str] = mapped_column(String(200))
    rubric_version: Mapped[str] = mapped_column(String(50))
    total_jobs: Mapped[int] = mapped_column(Integer)
    worker_token: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(TIMESTAMP(), 'mysql'), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class Evaluation(Base):
    __tablename__ = 'evaluations'
    __table_args__ = (UniqueConstraint('batch_id', 'job_id', name='uq_evaluation_batch_job'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    batch_id: Mapped[int | None] = mapped_column(ID, ForeignKey('evaluation_batches.id'), index=True)
    search_run_id: Mapped[int] = mapped_column(ID, ForeignKey('search_runs.id'))
    job_id: Mapped[int] = mapped_column(ID, ForeignKey('jobs.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    information_coverage: Mapped[float | None] = mapped_column(Numeric(5, 2))
    rubric_version: Mapped[str] = mapped_column(String(50))
    matched: Mapped[list] = mapped_column(JSON, default=list)
    missing: Mapped[list] = mapped_column(JSON, default=list)
    unknown_criteria: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default='')
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict | None] = mapped_column(JSON)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
