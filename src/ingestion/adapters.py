"""Source adapters — type-specific ingestion wired to the shared pipeline."""
import re
import ast
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from docling.document_converter import DocumentConverter
from src.extractor import EntityExtractor
from src.wiki_writer import WikiPageWriter
from src.link_resolver import LinkResolver
from src.indexer import WikiIndexer
from src.services.embedding_provider import OllamaEmbeddingProvider
from src.pipeline.stages import (
    PipelineContext,
    PipelineStage,
    ConvertStage,
    ExtractStage,
    WriteStage,
    ResolveStage,
    IndexStage,
)
from src.ingestion_result import IngestionResult

logger = logging.getLogger(__name__)


class SourceAdapter(ABC):
    """Interface for type-specific ingestion.

    Each adapter implements `first_stage()` to return a type-specific
    pipeline stage, then shares the post-processing stages
    (Extract -> Write -> Resolve -> Index).
    """

    def __init__(self, wiki_dir: Path, output_dir: Path,
                 model: str = "gemma4:e2b",
                 schema_path: Optional[Path] = None):
        self.wiki_dir = Path(wiki_dir)
        self.output_dir = Path(output_dir)
        self.model = model
        self.schema_path = schema_path

    @abstractmethod
    def first_stage(self) -> PipelineStage:
        """Return the type-specific first pipeline stage."""
        ...

    def _shared_stages(self) -> list[PipelineStage]:
        converter = DocumentConverter()
        extractor = EntityExtractor(model=self.model, schema_path=self.schema_path)
        writer = WikiPageWriter(self.wiki_dir)
        resolver = LinkResolver(self.wiki_dir)
        embedding_provider = OllamaEmbeddingProvider()
        indexer = WikiIndexer(self.wiki_dir, embedding_provider=embedding_provider)

        return [
            ExtractStage(extractor=extractor),
            WriteStage(writer=writer),
            ResolveStage(resolver=resolver),
            IndexStage(indexer=indexer),
        ]

    def run(self) -> IngestionResult:
        logger.info(f"Starting pipeline for adapter: {self.__class__.__name__}")
        try:
            self._ensure_dirs()
            stages = [self.first_stage()] + self._shared_stages()
            context = self._initial_context()

            logger.info(f"Starting pipeline with {len(stages)} stage(s)")
            for i, stage in enumerate(stages):
                logger.debug(f"Executing stage {i + 1}/{len(stages)}: {stage}")
                try:
                    context = stage.execute(context)
                    logger.debug(f"Stage {stage} completed successfully")
                except Exception as e:
                    logger.error(f"Stage {stage} failed: {e}")
                    context.error = e
                    raise

            logger.info("Pipeline completed successfully")
            logger.info(
                f"Pipeline complete: {context.output_path} "
                f"({len(context.entity_pages)} entities, "
                f"{len(context.concept_pages)} concepts)"
            )
            return IngestionResult(
                success=True,
                output_path=context.output_path,
                entity_pages=context.entity_pages,
                concept_pages=context.concept_pages,
            )
        except Exception as e:
            logger.error(f"Pipeline failed for {self.__class__.__name__}: {e}")
            return IngestionResult(
                success=False,
                output_path=None,
                error=str(e),
            )

    @abstractmethod
    def _ensure_dirs(self): ...

    @abstractmethod
    def _initial_context(self) -> PipelineContext: ...


class PDFSourceAdapter(SourceAdapter):
    """Adapts PDF/Markdown files to the shared pipeline."""

    def __init__(self, source_path: Path, wiki_dir: Path,
                 output_dir: Path, model: str = "gemma4:e2b",
                 schema_path: Optional[Path] = None):
        super().__init__(wiki_dir=wiki_dir, output_dir=output_dir,
                         model=model, schema_path=schema_path)
        self.source_path = Path(source_path)

    def first_stage(self) -> PipelineStage:
        return ConvertStage(converter=DocumentConverter())

    def _ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def _initial_context(self) -> PipelineContext:
        return PipelineContext(
            source_path=self.source_path,
            output_dir=self.output_dir,
            wiki_dir=self.wiki_dir,
        )


class URLSourceAdapter(SourceAdapter):
    """Adapts URL sources to the shared pipeline."""

    def __init__(self, url: str, wiki_dir: Path,
                 output_dir: Optional[Path] = None,
                 model: str = "gemma4:e2b",
                 schema_path: Optional[Path] = None,
                 timeout: float = 30.0):
        wiki_dir = Path(wiki_dir)
        if output_dir is None:
            output_dir = wiki_dir / "generated"
        super().__init__(wiki_dir=wiki_dir, output_dir=output_dir,
                         model=model, schema_path=schema_path)
        self.url = url
        self.timeout = timeout

    def first_stage(self) -> PipelineStage:
        return URLFetchStage(url=self.url, output_dir=self.output_dir,
                             timeout=self.timeout)

    def _ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _initial_context(self) -> PipelineContext:
        return PipelineContext(
            output_dir=self.output_dir,
            wiki_dir=self.wiki_dir,
        )


class CodeSourceAdapter(SourceAdapter):
    """Adapts code repository sources to the shared pipeline."""

    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "kotlin": [".kt", ".kts"],
        "go": [".go"],
        "rust": [".rs"],
    }

    def __init__(self, code_dir: Path, wiki_dir: Path,
                 language: str = "python",
                 output_dir: Optional[Path] = None,
                 model: str = "gemma4:e2b",
                 schema_path: Optional[Path] = None):
        wiki_dir = Path(wiki_dir)
        if output_dir is None:
            output_dir = wiki_dir / "code"
        super().__init__(wiki_dir=wiki_dir, output_dir=output_dir,
                         model=model, schema_path=schema_path)
        self.code_dir = Path(code_dir)
        self.language = language.lower()
        self.extensions = self.LANGUAGE_EXTENSIONS.get(self.language, [])

    def first_stage(self) -> PipelineStage:
        return CodeGenerateStage(
            code_dir=self.code_dir,
            output_dir=self.output_dir,
            language=self.language,
            extensions=self.extensions,
        )

    def _ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _initial_context(self) -> PipelineContext:
        return PipelineContext(
            output_dir=self.output_dir,
            wiki_dir=self.wiki_dir,
        )


# ============================================================================
# Type-specific first stages
# ============================================================================

class URLFetchStage(PipelineStage):
    """Fetches URL content and converts to markdown."""

    def __init__(self, url: str, output_dir: Path, timeout: float = 30.0):
        self.url = url
        self.output_dir = output_dir
        self.timeout = timeout

    def execute(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Fetching URL: {self.url}")
        html_content = self._fetch()
        markdown_content = self._html_to_markdown(html_content)
        title = self._extract_title(html_content)
        output_path = self._generate_output_path(title)

        output_path.write_text(markdown_content)
        logger.info(f"Wrote markdown to {output_path}")

        context.content = markdown_content
        context.output_path = output_path
        context.source_doc = self.url
        return context

    def _fetch(self) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(self.url)
            response.raise_for_status()
            return response.text

    def _html_to_markdown(self, html_content: str) -> str:
        converter = DocumentConverter()
        result = converter.convert_string(html_content, mime_type="text/html")
        return result.document.export_to_markdown()

    def _extract_title(self, html_content: str) -> str:
        match = re.search(r"<title[^>]*>([^<]+)</title>", html_content)
        if match:
            return match.group(1).strip()
        return "untitled"

    def _generate_output_path(self, title: str) -> Path:
        slug = title.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c in "-_")
        return self.output_dir / f"{slug}.md"


class CodeGenerateStage(PipelineStage):
    """Scans code files and generates combined markdown documentation."""

    def __init__(self, code_dir: Path, output_dir: Path,
                 language: str, extensions: list[str]):
        self.code_dir = code_dir
        self.output_dir = output_dir
        self.language = language
        self.extensions = extensions

    def execute(self, context: PipelineContext) -> PipelineContext:
        code_files = self._find_files()
        if not code_files:
            logger.info("No code files found")
            context.output_path = None
            return context

        all_docs = []
        for file_path in code_files:
            logger.debug(f"Processing: {file_path}")
            doc = self._generate_markdown(file_path)
            all_docs.append(doc)

        output_name = self.code_dir.name.replace(" ", "_").lower()
        output_path = self.output_dir / f"{output_name}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n\n---\n\n".join(all_docs))
        logger.info(f"Wrote code documentation to {output_path}")

        context.content = output_path.read_text()
        context.output_path = output_path
        context.source_doc = str(self.code_dir)
        return context

    def _find_files(self) -> list[Path]:
        if not self.extensions:
            logger.warning(f"No extensions configured for language: {self.language}")
            return []
        files = []
        for ext in self.extensions:
            files.extend(self.code_dir.rglob(f"*{ext}"))
        return [
            f for f in files
            if ".venv" not in str(f) and "node_modules" not in str(f)
            and "__pycache__" not in str(f) and ".git" not in str(f)
        ]

    def _generate_markdown(self, file_path: Path) -> str:
        rel_path = file_path.relative_to(self.code_dir)
        content = file_path.read_text()
        docstring = ""
        if self.language == "python":
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree) or ""
            except SyntaxError:
                logger.warning(f"Syntax error in {file_path}")

        md_lines = [f"# {rel_path}", "", f"**Source:** `{rel_path}`", ""]
        if docstring:
            md_lines.extend(["## Summary", "", docstring, ""])
        md_lines.extend([
            "## Code",
            "",
            f"```{self.language}",
            content,
            "```",
            "",
        ])
        return "\n".join(md_lines)
