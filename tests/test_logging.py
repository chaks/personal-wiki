# tests/test_logging.py
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.logging_config import setup_logging


def test_setup_logging_creates_handlers():
    """Verify setup_logging creates console and file handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        setup_logging(log_dir=log_dir, level=logging.DEBUG)

        root_logger = logging.getLogger()
        # Root logger should have the configured level
        assert root_logger.level == logging.DEBUG
        # Root logger should have at least 2 handlers (console + file)
        assert len(root_logger.handlers) >= 2


def test_log_file_rotation():
    """Verify log files are created in the correct location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        setup_logging(log_dir=log_dir)

        log_file = log_dir / "personal-wiki.log"
        assert log_file.exists()


def test_main_initializes_logging():
    """Verify main() initializes logging before running server."""
    with patch("src.logging_config.setup_logging") as mock_setup:
        with patch("src.server.run_server"):
            from src.__main__ import main
            import sys

            # Mock argv to avoid actual arg parsing
            with patch.object(sys, "argv", ["wiki-chat"]):
                main()

            mock_setup.assert_called_once()
            call_args = mock_setup.call_args
            assert call_args.kwargs.get("log_dir") is not None
