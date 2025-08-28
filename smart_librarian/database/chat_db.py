# smart_librarian/models/chat_db.py
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
import os

# --- SQLAlchemy wiring (use the same DATABASE_URL you already set) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://smartlib:smartlib@db:5432/smartlib")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()


class ConversationORM(Base):
    __tablename__ = "conversations"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    username    = Column(String, index=True, nullable=False)  # or user_id if you prefer
    title       = Column(String, nullable=False, default="New chat")
    # ✅ Mutable JSONB so appends are tracked and committed
    messages    = Column(MutableList.as_mutable(JSONB), nullable=False, default=text("'[]'::jsonb"))
    created_at  = Column(DateTime, nullable=False, server_default=func.now())
    updated_at  = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


def init_chat_db():
    Base.metadata.create_all(bind=engine)


# -------- Public API your controller calls --------

class Conversation:
    """Convenience wrapper returning plain dicts for Jinja."""
    @staticmethod
    def list_conversations(username: str) -> List[Dict[str, Any]]:
        with SessionLocal() as s:
            rows = (
                s.query(ConversationORM)
                .filter(ConversationORM.username == username)
                .order_by(ConversationORM.updated_at.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "updated_at": r.updated_at,
                }
                for r in rows
            ]

    @staticmethod
    def get_conversation(username: str, conv_id: int) -> Optional[Dict[str, Any]]:
        with SessionLocal() as s:
            r = (
                s.query(ConversationORM)
                .filter(ConversationORM.id == conv_id, ConversationORM.username == username)
                .one_or_none()
            )
            if not r:
                return None
            # ✅ r.messages is a PY list (thanks to JSONB + MutableList)
            return {
                "id": r.id,
                "title": r.title,
                "messages": r.messages or [],
                "updated_at": r.updated_at,
                "created_at": r.created_at,
            }

    @staticmethod
    def create_conversation(username: str, title: str) -> int:
        with SessionLocal() as s:
            obj = ConversationORM(username=username, title=title, messages=[])
            s.add(obj)
            s.commit()
            return obj.id

    @staticmethod
    def set_title(username: str, conv_id: int, title: str) -> None:
        with SessionLocal() as s:
            r = (
                s.query(ConversationORM)
                .filter(ConversationORM.id == conv_id, ConversationORM.username == username)
                .one_or_none()
            )
            if not r:
                return
            r.title = title
            s.commit()

    @staticmethod
    def add_message(username: str, conv_id: int, role: str, content: str) -> None:
        with SessionLocal() as s:
            r = (
                s.query(ConversationORM)
                .filter(ConversationORM.id == conv_id, ConversationORM.username == username)
                .one_or_none()
            )
            if not r:
                return
            # ✅ Append to the Python list; MutableList marks it dirty
            msgs = r.messages or []
            msgs.append({"role": role, "content": content})
            r.messages = msgs   # (re-assign is optional w/ MutableList, but safe)
            s.commit()

    @staticmethod
    def delete_conversation(username: str, conv_id: int) -> None:
        with SessionLocal() as s:
            s.query(ConversationORM).filter(
                ConversationORM.id == conv_id, ConversationORM.username == username
            ).delete()
            s.commit()
