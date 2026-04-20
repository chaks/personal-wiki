# src/__main__.py
"""CLI entry point for Personal Wiki Chat."""
import argparse
import logging
from pathlib import Path

from src.logging_config import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Personal Wiki Chat Server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run wiki lint checks",
    )
    args = parser.parse_args()

    # Handle --lint mode
    if args.lint:
        from src.lint import WikiLinter
        linter = WikiLinter(Path(__file__).parent.parent / "wiki")
        results = linter.run_all_checks()
        print(f"Orphan pages: {len(results['orphans'])}")
        for orphan in results['orphans']:
            print(f"  - {orphan}")
        return

    root = Path(__file__).parent.parent

    # Initialize logging before anything else
    log_level = getattr(logging, args.log_level)
    setup_logging(log_dir=root / "logs", level=log_level)

    logger = logging.getLogger("src")
    logger.info(f"Starting Personal Wiki Chat server on {args.host}:{args.port}")

    from src.server import run_server

    run_server(
        wiki_dir=root / "wiki",
        state_dir=root / "state",
        static_dir=root / "static",
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
