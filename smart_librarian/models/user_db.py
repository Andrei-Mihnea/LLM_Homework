# smart_librarian/models/user_db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
import time
import bcrypt

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://smartlib:smartlib@db:5432/smartlib"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,          # drops dead connections gracefully
    future=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_user_username"),
        UniqueConstraint("email", name="uq_user_email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)  # bcrypt hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @staticmethod
    def exists_password_and_user(username: str, password: str) -> bool:
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return False
            return bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8"))
        finally:
            session.close()



def init_db(max_retries: int = 30, delay_seconds: float = 1.0):
    # wait for DB to be truly reachable
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError as e:
            if attempt == max_retries:
                raise
            time.sleep(delay_seconds)

