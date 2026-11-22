from datetime import datetime
from typing import Any
from app.config import DATABASE_URL
from app.services.conversation_service import add_message as memory_add, get_history as memory_get_history

def database_enabled()-> bool:
    return bool(DATABASE_URL)

def _connect():
    import psycopg
    return psycopg.connect(DATABASE_URL,connect_timeout=8) #8s wait to connec database

def initialize_database()-> None:
    if not database_enabled():
        return
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS conversations(
  id UUID PRIMARY KEY ,
  title TEXT NOT NULL DEFAULT 'New chat',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages(
  id BIGSERIAL PRIMARY KEY ,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('system','user','assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")

def ensure_conversation(session_id:str,title:str="New Chat")->None:
    if not database_enabled():
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations(id,title) VALUES (%s,%s) "
            "ON CONFLICT (id) DO NOTHING",
            (session_id, title),
        )

def add_chat_message(session_id:str,role:str,content:str)->None:
    if not database_enabled():
        memory_add(session_id,role,content)
        return
    ensure_conversation(session_id, content[:70] if role == "user" else "New Chat")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages(conversation_id,role,content) VALUES (%s,%s,%s)",
            (session_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = NOW(), "
            "title = CASE WHEN title = 'New Chat' AND %s = 'user' "
            "THEN %s ELSE title END WHERE id = %s",
            (role, content[:70], session_id),
        )

def get_chat_history(session_id:str)->list[dict[str,str]]:
    if not database_enabled():
        return memory_get_history(session_id)
    ensure_conversation(session_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE conversation_id=%s ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    return [{"role":role,"content":content} for role, content in rows]


def list_conversations(limit:int=30)->list[dict[str,Any]]:
    if not database_enabled():
        return []
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "ORDER BY updated_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [
        {
            "id": str(conversation_id),
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        for conversation_id, title, created_at, updated_at in rows
    ]
