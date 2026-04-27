"""Tests for pipeline stage abstractions and runner."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.pipeline.stages import (
    PipelineContext,
    PipelineStage,
    ConvertStage,
    ExtractStage,
    WriteStage,
    ResolveStage,
    IndexStage,
)


# ============================================================================
# Stage Interface Tests
# ============================================================================

class TestPipelineContext:
    """Test PipelineContext dataclass."""

    def test_context_created_empty(self):
        """PipelineContext can be created with defaults."""
        ctx = PipelineContext()
        assert ctx.source_path is None
        assert ctx.output_path is None
        assert ctx.wiki_dir is None
        assert ctx.content == ""
        assert ctx.entities == []
        assert ctx.concepts == []
        assert ctx.error is None

    def test_context_with_values(self):
        """PipelineContext carries data through pipeline."""
        ctx = PipelineContext(
            source_path=Path("/test/source.md"),
            output_dir=Path("/test/output"),
            wiki_dir=Path("/test/wiki"),
            content="# Test content",
        )
        assert ctx.source_path == Path("/test/source.md")
        assert ctx.output_dir == Path("/test/output")
        assert ctx.wiki_dir == Path("/test/wiki")
        assert ctx.content == "# Test content"


# ============================================================================
# Pipeline Execution Tests
# ============================================================================

class TestPipelineExecution:
    """Test that stages execute sequentially via the adapter loop."""

    def test_stages_execute_sequentially(self):
        """Multiple stages execute in order and pass context between them."""
        execution_order = []

        class Stage1(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_order.append(1)
                return context

        class Stage2(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_order.append(2)
                return context

        stages = [Stage1(), Stage2()]
        ctx = PipelineContext()
        for stage in stages:
            ctx = stage.execute(ctx)

        assert execution_order == [1, 2]

    def test_context_passes_between_stages(self):
        """Each stage receives the context modified by the previous stage."""
        class AppendStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                context.content = context.content + "stage "
                return context

        stages = [AppendStage(), AppendStage()]
        ctx = PipelineContext()
        for stage in stages:
            ctx = stage.execute(ctx)

        assert ctx.content == "stage stage "

    def test_execution_stops_on_error(self):
        """Subsequent stages are skipped when a stage raises."""
        execution_count = [0]

        class Stage1(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_count[0] += 1
                return context

        class FailingStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                raise ValueError("boom")

        class Stage3(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_count[0] += 1
                return context

        stages = [Stage1(), FailingStage(), Stage3()]
        ctx = PipelineContext()

        with pytest.raises(ValueError, match="boom"):
            for stage in stages:
                ctx = stage.execute(ctx)

        assert execution_count[0] == 1


# ============================================================================
# Concrete Stage Tests
# ============================================================================

class TestConvertStage:
    """Test ConvertStage for Docling conversion."""

    def test_convert_stage_created(self):
        """ConvertStage can be instantiated with converter."""
        mock_converter = Mock()
        stage = ConvertStage(converter=mock_converter)
        assert stage.converter is mock_converter

    @patch("src.ingestion.adapters.DocumentConverter")
    def test_convert_stage_executes(self, mock_converter_class, tmp_path):
        """ConvertStage converts source to markdown using injected converter."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_instance = Mock()
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Converted\n\nMarkdown content"
        mock_instance.convert.return_value = mock_result
        mock_converter_class.return_value = mock_instance

        stage = ConvertStage(converter=mock_instance)
        ctx = PipelineContext(
            source_path=Path("/test/source.md"),
            output_dir=output_dir,
        )

        result = stage.execute(ctx)

        assert result.content == "# Converted\n\nMarkdown content"
        assert result.output_path == output_dir / "source.md"
        mock_instance.convert.assert_called_once_with(str(Path("/test/source.md")))


class TestExtractStage:
    """Test ExtractStage for entity/concept extraction."""

    def test_extract_stage_created(self):
        """ExtractStage can be instantiated with extractor."""
        mock_extractor = Mock()
        stage = ExtractStage(extractor=mock_extractor)
        assert stage.extractor is mock_extractor

    def test_extract_stage_executes(self):
        """ExtractStage extracts entities and concepts using injected extractor."""
        from src.extractor import Entity, Concept

        mock_extractor = Mock()
        mock_extractor.extract.return_value = [
            Entity(name="Test Entity", entity_type="test", description="A test entity")
        ]
        mock_extractor.extract_concepts.return_value = [
            Concept(name="Test Concept", definition="A test concept")
        ]

        stage = ExtractStage(extractor=mock_extractor)
        ctx = PipelineContext(
            content="# Test content",
            source_doc="test.md",
        )

        result = stage.execute(ctx)

        assert len(result.entities) == 1
        assert len(result.concepts) == 1
        assert result.entities[0].name == "Test Entity"
        assert result.concepts[0].name == "Test Concept"
        mock_extractor.extract.assert_called_once_with("# Test content", source_doc="test.md")
        mock_extractor.extract_concepts.assert_called_once_with("# Test content", source_doc="test.md")


class TestWriteStage:
    """Test WriteStage for writing wiki pages."""

    def test_write_stage_created(self):
        """WriteStage can be instantiated with writer."""
        mock_writer = Mock()
        stage = WriteStage(writer=mock_writer)
        assert stage.writer is mock_writer

    def test_write_stage_executes(self):
        """WriteStage writes entity and concept pages using injected writer."""
        from src.extractor import Entity, Concept

        mock_writer = Mock()
        mock_writer.write_entity.return_value = Path("/test/wiki/entities/test-entity.md")
        mock_writer.write_concept.return_value = Path("/test/wiki/concepts/test-concept.md")

        stage = WriteStage(writer=mock_writer)
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            entities=[Entity(name="Test Entity", entity_type="test", description="Test")],
            concepts=[Concept(name="Test Concept", definition="Test")],
        )

        result = stage.execute(ctx)

        assert len(result.entity_pages) == 1
        assert len(result.concept_pages) == 1
        mock_writer.write_entity.assert_called_once()
        mock_writer.write_concept.assert_called_once()


class TestResolveStage:
    """Test ResolveStage for link resolution."""

    def test_resolve_stage_created(self):
        """ResolveStage can be instantiated with resolver."""
        mock_resolver = Mock()
        stage = ResolveStage(resolver=mock_resolver)
        assert stage.resolver is mock_resolver

    def test_resolve_stage_executes(self):
        """ResolveStage resolves wiki links using injected resolver."""
        mock_resolver = Mock()

        stage = ResolveStage(resolver=mock_resolver)
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            output_path=Path("/test/output/doc.md"),
            content="# Test content with [[wikilink]]",
        )

        result = stage.execute(ctx)

        mock_resolver.resolve_all.assert_called_once_with(Path("/test/output/doc.md"))


class TestIndexStage:
    """Test IndexStage for indexing pages."""

    def test_index_stage_created(self):
        """IndexStage can be instantiated with indexer."""
        mock_indexer = Mock()
        stage = IndexStage(indexer=mock_indexer)
        assert stage.indexer is mock_indexer

    def test_index_stage_executes(self):
        """IndexStage indexes pages using injected indexer."""
        mock_indexer = Mock()
        mock_indexer.index_page.return_value = None

        stage = IndexStage(indexer=mock_indexer)
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            output_path=Path("/test/output/doc.md"),
            entity_pages=[Path("/test/wiki/entities/entity.md")],
            concept_pages=[Path("/test/wiki/concepts/concept.md")],
        )

        result = stage.execute(ctx)

        assert mock_indexer.index_page.call_count == 3


class TestPipelineStage:
    """Test PipelineStage abstract base class."""

    def test_stage_is_abstract(self):
        """PipelineStage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PipelineStage()

    def test_stage_requires_execute_method(self):
        """Concrete stages must implement execute()."""
        class ConcreteStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                return context

        stage = ConcreteStage()
        ctx = PipelineContext()
        result = stage.execute(ctx)
        assert result is ctx
