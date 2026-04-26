"""Chat history persistence with SQLite."""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChatHistory:
    """Manages chat history persistence in SQLite."""

    def __init__(self, db_path: Path):
        """Initialize ChatHistory with a database path.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()
        logger.debug(f"ChatHistory initialized with db={self.db_path}")

    def _init_db(self) -> None:
        """Initialize the chat_history table and index."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON chat_history(session_id)"
        )
        self.conn.commit()

    def save(
        self,
        session_id: str,
        question: str,
        answer: str,
        sources: list[str],
    ) -> None:
        """Save a chat exchange to history.

        Args:
            session_id: Unique identifier for the chat session
            question: The user's question
            answer: The assistant's answer
            sources: List of source paths used for the answer
        """
        sources_json = json.dumps(sources)
        self.conn.execute(
            """
            INSERT INTO chat_history (session_id, question, answer, sources, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (session_id, question, answer, sources_json),
        )
        self.conn.commit()
        logger.debug(f"Saved chat history for session {session_id}")

    def get_session(self, session_id: str) -> list[dict]:
        """Retrieve all history entries for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            List of history entries as dictionaries, ordered by creation time
        """
        cursor = self.conn.execute(
            """
            SELECT id, session_id, question, answer, sources, created_at
            FROM chat_history
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            sources_str = row[4]
            try:
                sources = json.loads(sources_str) if sources_str else []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse sources for entry {row[0]}, using empty list")
                sources = []
            results.append({
                "id": row[0],
                "session_id": row[1],
                "question": row[2],
                "answer": row[3],
                "sources": sources,
                "created_at": row[5],
            })
        logger.debug(f"Retrieved {len(results)} entries for session {session_id}")
        return results

    def get_recent(
        self,
        session_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """Retrieve the most recent history entries for a session.

        Args:
            session_id: Unique identifier for the chat session
            limit: Maximum number of entries to return (default 5)

        Returns:
            List of most recent history entries as dictionaries,
            ordered by creation time descending (most recent first)
        """
        cursor = self.conn.execute(
            """
            SELECT id, session_id, question, answer, sources, created_at
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            sources_str = row[4]
            try:
                sources = json.loads(sources_str) if sources_str else []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse sources for entry {row[0]}, using empty list")
                sources = []
            results.append({
                "id": row[0],
                "session_id": row[1],
                "question": row[2],
                "answer": row[3],
                "sources": sources,
                "created_at": row[5],
            })
        logger.debug(f"Retrieved {len(results)} recent entries for session {session_id}")
        return results

    def clear_session(self, session_id: str) -> None:
        """Delete all history entries for a session.

        Args:
            session_id: Unique identifier for the chat session
        """
        self.conn.execute(
            "DELETE FROM chat_history WHERE session_id = ?",
            (session_id,),
        )
        self.conn.commit()
        logger.info(f"Cleared chat history for session {session_id}")
