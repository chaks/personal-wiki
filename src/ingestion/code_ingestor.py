"""Code ingestion pipeline - converts source code to documentation markdown."""
import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of ingesting a source."""
    success: bool
    output_path: Optional[Path]
    error: Optional[str] = None
    entity_pages: list[Path] = field(default_factory=list)
    concept_pages: list[Path] = field(default_factory=list)


class CodeIngestor:
    """Processes code repositories and generates documentation."""

    # File extensions to process per language
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "kotlin": [".kt", ".kts"],
        "go": [".go"],
        "rust": [".rs"],
    }

    def __init__(
        self,
        code_dir: Path,
        wiki_dir: Path,
        language: str = "python",
        output_dir: Optional[Path] = None,
    ):
        """Initialize code ingestor.

        Args:
            code_dir: Path to code directory
            wiki_dir: Wiki directory for output
            language: Programming language (python, javascript, typescript, etc.)
            output_dir: Optional specific output directory (default: wiki_dir/code)
        """
        self.code_dir = Path(code_dir)
        self.wiki_dir = Path(wiki_dir)
        self.language = language.lower()
        self.output_dir = Path(output_dir) if output_dir else self.wiki_dir / "code"
        self.extensions = self.LANGUAGE_EXTENSIONS.get(self.language, [])
        logger.debug(f"CodeIngestor initialized: {code_dir} ({language}) -> {self.output_dir}")

    def _ensure_dirs(self):
        """Ensure output directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _find_code_files(self) -> list[Path]:
        """Find all code files in the directory."""
        if not self.extensions:
            logger.warning(f"No extensions configured for language: {self.language}")
            return []

        files = []
        for ext in self.extensions:
            files.extend(self.code_dir.rglob(f"*{ext}"))

        # Filter out common non-source directories
        filtered = [
            f for f in files
            if ".venv" not in str(f)
            and "node_modules" not in str(f)
            and "__pycache__" not in str(f)
            and ".git" not in str(f)
        ]
        logger.info(f"Found {len(filtered)} {self.language} files")
        return filtered

    def _extract_docstring(self, file_path: Path) -> str:
        """Extract module docstring from a Python file."""
        content = file_path.read_text()

        if self.language == "python":
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if docstring:
                    return docstring
            except SyntaxError:
                logger.warning(f"Syntax error in {file_path}")

        return ""

    def _generate_markdown(self, file_path: Path) -> str:
        """Generate markdown documentation for a code file."""
        rel_path = file_path.relative_to(self.code_dir)
        content = file_path.read_text()
        docstring = self._extract_docstring(file_path)

        md_lines = [
            f"# {rel_path}",
            "",
            f"**Source:** `{rel_path}`",
            "",
        ]

        if docstring:
            md_lines.extend([
                "## Summary",
                "",
                docstring,
                "",
            ])

        md_lines.extend([
            "## Code",
            "",
            f"```{self.language}",
            content,
            "```",
            "",
        ])

        return "\n".join(md_lines)

    def ingest(self) -> IngestionResult:
        """Process code files and generate documentation."""
        logger.info(f"Starting code ingestion: {self.code_dir} ({self.language})")

        try:
            self._ensure_dirs()

            # Step 1: Find all code files
            code_files = self._find_code_files()

            if not code_files:
                logger.info("No code files found")
                return IngestionResult(
                    success=True,
                    output_path=None,
                )

            # Step 2: Generate combined markdown
            all_docs = []
            for file_path in code_files:
                logger.debug(f"Processing: {file_path}")
                doc = self._generate_markdown(file_path)
                all_docs.append(doc)

            # Step 3: Write combined output
            output_name = self.code_dir.name.replace(" ", "_").lower()
            output_path = self.output_dir / f"{output_name}.md"
            output_path.write_text("\n\n---\n\n".join(all_docs))

            logger.info(f"Wrote code documentation to {output_path}")

            return IngestionResult(
                success=True,
                output_path=output_path,
            )

        except Exception as e:
            logger.error(f"Code ingestion failed for {self.code_dir}: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )
