"""Tests for ChatHistory persistence."""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.history import ChatHistory


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    # Initialize the chat_history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON chat_history(session_id)")
    conn.commit()
    yield conn
    conn.close()
    db_path.unlink()


class TestChatHistory:
    """Tests for ChatHistory class."""

    def test_save_history(self, temp_db):
        """Test saving a history entry and retrieving it via get_session."""
        history = ChatHistory(temp_db)

        # Save a history entry
        question = "What is FastAPI?"
        answer = "FastAPI is a modern web framework for Python."
        sources = ["docs/fastapi.md", "wiki/api.md"]

        history.save(
            session_id="test-session-1",
            question=question,
            answer=answer,
            sources=sources,
        )

        # Retrieve the session
        session = history.get_session("test-session-1")

        # Verify the entry was saved correctly
        assert len(session) == 1
        entry = session[0]
        assert entry["question"] == question
        assert entry["answer"] == answer
        assert entry["sources"] == sources
        assert entry["session_id"] == "test-session-1"

    def test_get_recent_history(self, temp_db):
        """Test that get_recent returns the most recent entries with limit."""
        history = ChatHistory(temp_db)

        # Save multiple history entries
        for i in range(5):
            history.save(
                session_id="test-session-2",
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[f"source{i}.md"],
            )

        # Get recent with limit=1
        recent = history.get_recent("test-session-2", limit=1)

        # Should return only the most recent entry
        assert len(recent) == 1
        assert recent[0]["question"] == "Question 4"
        assert recent[0]["answer"] == "Answer 4"

        # Get recent with limit=3
        recent = history.get_recent("test-session-2", limit=3)

        # Should return the 3 most recent entries in order
        assert len(recent) == 3
        assert recent[0]["question"] == "Question 4"
        assert recent[1]["question"] == "Question 3"
        assert recent[2]["question"] == "Question 2"

    def test_clear_session(self, temp_db):
        """Test that clear_session deletes all history entries for a session."""
        history = ChatHistory(temp_db)

        # Save multiple history entries for different sessions
        for i in range(3):
            history.save(
                session_id="test-session-clear",
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[f"source{i}.md"],
            )

        history.save(
            session_id="test-session-keep",
            question="Question to keep",
            answer="Answer to keep",
            sources=["source-keep.md"],
        )

        # Verify entries exist before clearing
        session_before = history.get_session("test-session-clear")
        assert len(session_before) == 3

        # Clear the session
        history.clear_session("test-session-clear")

        # Verify entries for the cleared session are deleted
        session_after = history.get_session("test-session-clear")
        assert len(session_after) == 0

        # Verify other sessions are not affected
        other_session = history.get_session("test-session-keep")
        assert len(other_session) == 1
        assert other_session[0]["question"] == "Question to keep"
