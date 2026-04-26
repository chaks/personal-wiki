"""Tests for ChatHistory persistence."""
import pytest

from src.history import ChatHistory


@pytest.fixture
def chat_history(tmp_path):
    """Create a ChatHistory with a temporary database."""
    db_path = tmp_path / "chat_history.db"
    return ChatHistory(db_path)


class TestChatHistory:
    """Tests for ChatHistory class."""

    def test_save_history(self, chat_history):
        """Test saving a history entry and retrieving it via get_session."""
        # Save a history entry
        question = "What is FastAPI?"
        answer = "FastAPI is a modern web framework for Python."
        sources = ["docs/fastapi.md", "wiki/api.md"]

        chat_history.save(
            session_id="test-session-1",
            question=question,
            answer=answer,
            sources=sources,
        )

        # Retrieve the session
        session = chat_history.get_session("test-session-1")

        # Verify the entry was saved correctly
        assert len(session) == 1
        entry = session[0]
        assert entry["question"] == question
        assert entry["answer"] == answer
        assert entry["sources"] == sources
        assert entry["session_id"] == "test-session-1"

    def test_get_recent_history(self, chat_history):
        """Test that get_recent returns the most recent entries with limit."""
        # Save multiple history entries
        for i in range(5):
            chat_history.save(
                session_id="test-session-2",
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[f"source{i}.md"],
            )

        # Get recent with limit=1
        recent = chat_history.get_recent("test-session-2", limit=1)

        # Should return only the most recent entry
        assert len(recent) == 1
        assert recent[0]["question"] == "Question 4"
        assert recent[0]["answer"] == "Answer 4"

        # Get recent with limit=3
        recent = chat_history.get_recent("test-session-2", limit=3)

        # Should return the 3 most recent entries in order
        assert len(recent) == 3
        assert recent[0]["question"] == "Question 4"
        assert recent[1]["question"] == "Question 3"
        assert recent[2]["question"] == "Question 2"

    def test_clear_session(self, chat_history):
        """Test that clear_session deletes all history entries for a session."""
        # Save multiple history entries for different sessions
        for i in range(3):
            chat_history.save(
                session_id="test-session-clear",
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[f"source{i}.md"],
            )

        chat_history.save(
            session_id="test-session-keep",
            question="Question to keep",
            answer="Answer to keep",
            sources=["source-keep.md"],
        )

        # Verify entries exist before clearing
        session_before = chat_history.get_session("test-session-clear")
        assert len(session_before) == 3

        # Clear the session
        chat_history.clear_session("test-session-clear")

        # Verify entries for the cleared session are deleted
        session_after = chat_history.get_session("test-session-clear")
        assert len(session_after) == 0

        # Verify other sessions are not affected
        other_session = chat_history.get_session("test-session-keep")
        assert len(other_session) == 1
        assert other_session[0]["question"] == "Question to keep"
