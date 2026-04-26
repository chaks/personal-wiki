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
from src.pipeline.runner import PipelineRunner


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


# ============================================================================
# Pipeline Runner Tests
# ============================================================================

class TestPipelineRunner:
    """Test PipelineRunner execution engine."""

    def test_runner_created_empty(self):
        """PipelineRunner can be created with no stages."""
        runner = PipelineRunner()
        assert runner.stages == []

    def test_runner_add_stage(self):
        """PipelineRunner.add_stage() adds a stage to the list."""
        runner = PipelineRunner()

        class MockStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                return context

        stage = MockStage()
        runner.add_stage(stage)

        assert len(runner.stages) == 1
        assert runner.stages[0] is stage

    def test_runner_executes_stages_sequentially(self):
        """PipelineRunner.run() executes stages in order."""
        execution_order = []

        class Stage1(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_order.append(1)
                return context

        class Stage2(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_order.append(2)
                return context

        class Stage3(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_order.append(3)
                return context

        runner = PipelineRunner()
        runner.add_stage(Stage1())
        runner.add_stage(Stage2())
        runner.add_stage(Stage3())

        ctx = PipelineContext()
        runner.run(ctx)

        assert execution_order == [1, 2, 3]

    def test_runner_passes_context_between_stages(self):
        """PipelineRunner.run() passes modified context between stages."""
        class Stage1(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                context.content = "modified by stage1"
                return context

        class Stage2(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                context.content = context.content + " and stage2"
                return context

        runner = PipelineRunner()
        runner.add_stage(Stage1())
        runner.add_stage(Stage2())

        ctx = PipelineContext()
        result = runner.run(ctx)

        assert result.content == "modified by stage1 and stage2"

    def test_runner_stops_on_error(self):
        """PipelineRunner.run() stops executing stages on error."""
        execution_count = [0]

        class Stage1(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_count[0] += 1
                return context

        class FailingStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                raise ValueError("Stage failed")

        class Stage3(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                execution_count[0] += 1
                return context

        runner = PipelineRunner()
        runner.add_stage(Stage1())
        runner.add_stage(FailingStage())
        runner.add_stage(Stage3())

        ctx = PipelineContext()

        with pytest.raises(ValueError, match="Stage failed"):
            runner.run(ctx)

        assert execution_count[0] == 1

    def test_runner_sets_error_on_context(self):
        """PipelineRunner.run() sets error on context when stage fails."""
        class FailingStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                raise ValueError("Stage failed")

        runner = PipelineRunner()
        runner.add_stage(FailingStage())

        ctx = PipelineContext()

        try:
            runner.run(ctx)
        except ValueError:
            pass

        assert ctx.error is not None
        assert "Stage failed" in str(ctx.error)


# ============================================================================
# Concrete Stage Tests
# ============================================================================

class TestConvertStage:
    """Test ConvertStage for Docling conversion."""

    def test_convert_stage_created(self):
        """ConvertStage can be instantiated."""
        stage = ConvertStage()
        assert stage is not None

    @patch("src.pipeline.stages.DocumentConverter")
    def test_convert_stage_executes(self, mock_converter, tmp_path):
        """ConvertStage converts source to markdown."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_instance = Mock()
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Converted\n\nMarkdown content"
        mock_instance.convert.return_value = mock_result
        mock_converter.return_value = mock_instance

        stage = ConvertStage()
        ctx = PipelineContext(
            source_path=Path("/test/source.md"),
            output_dir=output_dir,
        )

        result = stage.execute(ctx)

        assert result.content == "# Converted\n\nMarkdown content"
        assert result.output_path == output_dir / "source.md"
        mock_converter.return_value.convert.assert_called_once_with(str(Path("/test/source.md")))


class TestExtractStage:
    """Test ExtractStage for entity/concept extraction."""

    def test_extract_stage_created(self):
        """ExtractStage can be instantiated."""
        stage = ExtractStage(
            model="gemma4:e2b",
            schema_path=Path("/test/schema.yaml"),
        )
        assert stage is not None

    @patch("src.pipeline.stages.EntityExtractor")
    def test_extract_stage_executes(self, mock_extractor_class):
        """ExtractStage extracts entities and concepts from content."""
        from src.extractor import Entity, Concept

        mock_extractor = Mock()
        mock_extractor.extract.return_value = [
            Entity(name="Test Entity", entity_type="test", description="A test entity")
        ]
        mock_extractor.extract_concepts.return_value = [
            Concept(name="Test Concept", definition="A test concept")
        ]
        mock_extractor_class.return_value = mock_extractor

        stage = ExtractStage(
            model="gemma4:e2b",
            schema_path=Path("/test/schema.yaml"),
        )
        ctx = PipelineContext(
            content="# Test content",
            source_doc="test.md",
        )

        result = stage.execute(ctx)

        assert len(result.entities) == 1
        assert len(result.concepts) == 1
        assert result.entities[0].name == "Test Entity"
        assert result.concepts[0].name == "Test Concept"


class TestWriteStage:
    """Test WriteStage for writing wiki pages."""

    def test_write_stage_created(self):
        """WriteStage can be instantiated."""
        stage = WriteStage()
        assert stage is not None

    @patch("src.pipeline.stages.WikiPageWriter")
    def test_write_stage_executes(self, mock_writer_class):
        """WriteStage writes entity and concept pages."""
        from src.extractor import Entity, Concept

        mock_writer = Mock()
        mock_writer.write_entity.return_value = Path("/test/wiki/entities/test-entity.md")
        mock_writer.write_concept.return_value = Path("/test/wiki/concepts/test-concept.md")
        mock_writer_class.return_value = mock_writer

        stage = WriteStage()
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            entities=[Entity(name="Test Entity", entity_type="test", description="Test")],
            concepts=[Concept(name="Test Concept", definition="Test")],
        )

        result = stage.execute(ctx)

        assert len(result.entity_pages) == 1
        assert len(result.concept_pages) == 1
        mock_writer_class.assert_called_once_with(Path("/test/wiki"))


class TestResolveStage:
    """Test ResolveStage for link resolution."""

    def test_resolve_stage_created(self):
        """ResolveStage can be instantiated."""
        stage = ResolveStage()
        assert stage is not None

    @patch("src.pipeline.stages.LinkResolver")
    def test_resolve_stage_executes(self, mock_resolver_class):
        """ResolveStage resolves wiki links."""
        mock_resolver = Mock()
        mock_resolver.resolve_all.return_value = []
        mock_resolver_class.return_value = mock_resolver

        stage = ResolveStage()
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            output_path=Path("/test/output/doc.md"),
            content="# Test content with [[wikilink]]",
        )

        result = stage.execute(ctx)

        mock_resolver_class.assert_called_once_with(Path("/test/wiki"))
        mock_resolver.resolve_all.assert_called_once()


class TestIndexStage:
    """Test IndexStage for indexing pages."""

    def test_index_stage_created(self):
        """IndexStage can be instantiated."""
        stage = IndexStage()
        assert stage is not None

    @patch("src.pipeline.stages.WikiIndexer")
    def test_index_stage_executes(self, mock_indexer_class):
        """IndexStage indexes pages in Qdrant."""
        mock_indexer = Mock()
        mock_indexer.index_page.return_value = None
        mock_indexer_class.return_value = mock_indexer

        stage = IndexStage()
        ctx = PipelineContext(
            wiki_dir=Path("/test/wiki"),
            output_path=Path("/test/output/doc.md"),
            entity_pages=[Path("/test/wiki/entities/entity.md")],
            concept_pages=[Path("/test/wiki/concepts/concept.md")],
        )

        result = stage.execute(ctx)

        mock_indexer_class.assert_called_once()
        call_kwargs = mock_indexer_class.call_args
        assert call_kwargs[0][0] == Path("/test/wiki")
        assert "embedding_provider" in call_kwargs[1]
        assert mock_indexer.index_page.call_count >= 1


# ============================================================================
# DoclingIngestPipeline Integration Tests
# ============================================================================

class TestDoclingIngestPipeline:
    """Test full DoclingIngestPipeline integration."""

    def test_pipeline_created(self):
        from src.docling_ingestor import DoclingIngestPipeline
        pipeline = DoclingIngestPipeline(
            source_path=Path("/test/source.md"),
            output_dir=Path("/test/output"),
            wiki_dir=Path("/test/wiki"),
        )
        assert pipeline is not None

    @patch("src.pipeline.stages.WikiIndexer")
    @patch("src.pipeline.stages.LinkResolver")
    @patch("src.pipeline.stages.WikiPageWriter")
    @patch("src.pipeline.stages.EntityExtractor")
    @patch("src.pipeline.stages.DocumentConverter")
    def test_pipeline_runs_all_stages(
        self, mock_converter, mock_extractor_class, mock_writer_class,
        mock_resolver_class, mock_indexer_class, tmp_path
    ):
        """DoclingIngestPipeline runs all pipeline stages."""
        from src.docling_ingestor import DoclingIngestPipeline
        from src.extractor import Entity, Concept

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        wiki_dir = tmp_path / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "entities").mkdir()
        (wiki_dir / "concepts").mkdir()

        mock_instance = Mock()
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Converted\n\nContent"
        mock_instance.convert.return_value = mock_result
        mock_converter.return_value = mock_instance

        mock_extractor = Mock()
        mock_extractor.extract.return_value = [
            Entity(name="Test Entity", entity_type="test", description="Test")
        ]
        mock_extractor.extract_concepts.return_value = [
            Concept(name="Test Concept", definition="Test")
        ]
        mock_extractor_class.return_value = mock_extractor

        mock_writer = Mock()
        mock_writer.write_entity.return_value = wiki_dir / "entities" / "test-entity.md"
        mock_writer.write_concept.return_value = wiki_dir / "concepts" / "test-concept.md"
        mock_writer_class.return_value = mock_writer

        mock_resolver = Mock()
        mock_resolver.resolve_all.return_value = []
        mock_resolver_class.return_value = mock_resolver

        mock_indexer = Mock()
        mock_indexer.index_page.return_value = None
        mock_indexer_class.return_value = mock_indexer

        pipeline = DoclingIngestPipeline(
            source_path=Path("/test/source.md"),
            output_dir=output_dir,
            wiki_dir=wiki_dir,
        )

        result = pipeline.ingest()

        assert result.success is True
        assert result.output_path is not None
        mock_converter.return_value.convert.assert_called_once()
        mock_extractor.extract.assert_called_once()
        mock_extractor.extract_concepts.assert_called_once()
        mock_writer.write_entity.assert_called()
        mock_writer.write_concept.assert_called()
        mock_resolver.resolve_all.assert_called_once()
        mock_indexer.index_page.assert_called()

    def test_pipeline_handles_errors(self):
        from src.docling_ingestor import DoclingIngestPipeline
        pipeline = DoclingIngestPipeline(
            source_path=Path("/nonexistent/source.md"),
            output_dir=Path("/test/output"),
            wiki_dir=Path("/test/wiki"),
        )

        result = pipeline.ingest()

        assert result.success is False
        assert result.error is not None
