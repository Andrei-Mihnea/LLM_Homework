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

    @staticmethod
    def list_conversations(user_id):
        with SessionLocal() as db:
            return db.query(Conversation).filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
    @staticmethod
    def create_conversation(user_id, title):
        with SessionLocal() as db:
            conv = Conversation(user_id=user_id, title=title.strip() or "New chat", messages=[])
            db.add(conv)
            db.commit()
            db.refresh(conv)
            return conv.id
        
    @staticmethod
    def get_conversation(user_id, conv_id):
        with SessionLocal() as db:
            return db.query(Conversation).filter_by(user_id=user_id, id=conv_id).first()

    @staticmethod
    def add_message(user_id, conv_id, role, content):
        with SessionLocal() as db:
            conv = db.query(Conversation).filter_by(user_id=user_id, id=conv_id).first()
            if not conv:
                return None
            conv.messages.append({"role": role, "content": content})
            conv.updated_at = func.now()
            db.commit()
            db.refresh(conv)
            return conv
        
    @staticmethod
    def delete_conversation(user_id, conv_id):
        with SessionLocal() as db:
            conv = db.query(Conversation).filter_by(user_id=user_id, id=conv_id).first()
            if conv:
                db.delete(conv)
                db.commit()
                return True
            return False

def init_chat_db():
    Base.metadata.create_all(bind=engine)
