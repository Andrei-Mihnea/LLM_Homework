# smart_librarian/models/chat_db.py
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://smartlib:smartlib@db:5432/smartlib")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    messages = Column(JSONB, nullable=False, default=list)  # stores entire history
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), default=func.now())

def init_chat_db():
    Base.metadata.create_all(bind=engine)
