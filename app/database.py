from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

database_url = URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password.get_secret_value(),
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)
engine = create_engine(database_url, pool_pre_ping=True,
                       connect_args={'init_command': "SET time_zone = '+00:00'"})
SessionLocal = sessionmaker(bind=engine)


def get_db():
    with SessionLocal() as session:
        yield session
