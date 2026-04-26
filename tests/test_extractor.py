# tests/test_extractor.py
"""Tests for LLM-based entity and concept extraction."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.extractor import Entity, Concept, EntityExtractor
from src.services.llm_provider import OllamaProvider, LLMProvider


@pytest.fixture
def sample_document():
    """Sample document for testing extraction."""
    return """
    Andrej Karpathy is a computer scientist who worked at OpenAI and Tesla.
    He contributed to deep learning research and autonomous driving technology.
    The transformer architecture enables large language models like GPT-4.
    """


@pytest.fixture
def extractor():
    """Create an EntityExtractor instance."""
    return EntityExtractor()


class TestEntityDataclass:
    """Tests for Entity dataclass."""

    def test_entity_creation(self):
        """Entity can be created with required fields."""
        entity = Entity(
            name="Andrej Karpathy",
            entity_type="person",
            description="Computer scientist"
        )
        assert entity.name == "Andrej Karpathy"
        assert entity.entity_type == "person"
        assert entity.description == "Computer scientist"
        assert entity.source_doc is None

    def test_entity_with_source_doc(self):
        """Entity can include source document reference."""
        entity = Entity(
            name="Tesla",
            entity_type="organization",
            description="Electric vehicle company",
            source_doc="karpathy_bio.md"
        )
        assert entity.source_doc == "karpathy_bio.md"


class TestConceptDataclass:
    """Tests for Concept dataclass."""

    def test_concept_creation(self):
        """Concept can be created with required fields."""
        concept = Concept(
            name="Deep Learning",
            definition="A subset of machine learning using neural networks"
        )
        assert concept.name == "Deep Learning"
        assert concept.definition == "A subset of machine learning using neural networks"
        assert concept.related_entities == []
        assert concept.source_doc is None

    def test_concept_with_related_entities(self):
        """Concept can include related entities."""
        concept = Concept(
            name="Transformer Architecture",
            definition="Neural network architecture using attention mechanisms",
            related_entities=["OpenAI", "Google"],
            source_doc="llm_research.md"
        )
        assert len(concept.related_entities) == 2
        assert "OpenAI" in concept.related_entities


class TestEntityExtractor:
    """Tests for EntityExtractor class."""

    def test_extractor_initializes_with_defaults(self):
        """EntityExtractor initializes with default model."""
        extractor = EntityExtractor()
        assert extractor.llm_provider is not None
        assert isinstance(extractor.llm_provider, OllamaProvider)

    def test_extractor_custom_model(self):
        """EntityExtractor accepts custom model."""
        extractor = EntityExtractor(model="llama3")
        assert extractor.llm_provider is not None
        assert extractor.llm_provider.model == "llama3"

    @patch("src.extractor.Path")
    def test_extractor_loads_prompts_from_schema(self, mock_path):
        """EntityExtractor loads prompts from schema file."""
        mock_schema = Mock()
        mock_schema.exists.return_value = True
        mock_schema.read_text.return_value = """
ingestion:
  prompts:
    extract_entities: "Custom entity prompt"
    extract_concepts: "Custom concept prompt"
"""
        extractor = EntityExtractor(schema_path=mock_schema)
        # Prompts should be loaded from schema
        assert extractor.entity_prompt == "Custom entity prompt"
        assert extractor.concept_prompt == "Custom concept prompt"

    def test_extractor_uses_default_prompts(self):
        """EntityExtractor uses default prompts when no schema."""
        extractor = EntityExtractor(schema_path=None)
        assert extractor.entity_prompt is not None
        assert extractor.concept_prompt is not None
        assert len(extractor.entity_prompt) > 0
        assert len(extractor.concept_prompt) > 0


class MockLLMProvider(LLMProvider):
    """Test double for LLM provider."""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.call_count += 1
        return self.response

    def generate_stream(self, prompt: str, system: str | None = None):
        yield self.response

    def health_check(self) -> bool:
        return True

    async def generate_async(self, prompt: str, system: str | None = None) -> str:
        return self.response

    async def generate_stream_async(self, prompt: str, system: str | None = None):
        yield self.response


class TestEntityExtraction:
    """Tests for entity extraction functionality."""

    def test_extract_entities_from_document(self, sample_document):
        """Extract entities from a document using LLM."""
        mock_provider = MockLLMProvider(response="""
        ENTITY: Andrej Karpathy | person | Computer scientist at OpenAI and Tesla
        ENTITY: OpenAI | organization | AI research organization
        ENTITY: Tesla | organization | Electric vehicle and autonomous driving company
        ENTITY: GPT-4 | product | Large language model
        ENTITY: Transformer | technology | Neural network architecture
        """)

        extractor = EntityExtractor(llm_provider=mock_provider)
        entities = extractor.extract(sample_document, source_doc="test.md")

        assert len(entities) == 5
        assert entities[0].name == "Andrej Karpathy"
        assert entities[0].entity_type == "person"
        assert "Computer scientist" in entities[0].description

    def test_extract_entities_handles_empty_response(self, sample_document):
        """Extract returns empty list when LLM returns empty response."""
        mock_provider = MockLLMProvider(response="")

        extractor = EntityExtractor(llm_provider=mock_provider)
        entities = extractor.extract(sample_document)

        assert entities == []

    def test_extract_entities_handles_malformed_response(self, sample_document):
        """Extract returns empty list when LLM returns malformed response."""
        mock_provider = MockLLMProvider(response="This is not properly formatted")

        extractor = EntityExtractor(llm_provider=mock_provider)
        entities = extractor.extract(sample_document)

        assert entities == []

    def test_extract_entities_handles_api_error(self, sample_document):
        """Extract returns empty list when LLM API fails."""
        class ErrorProvider(LLMProvider):
            def generate(self, prompt: str, system: str | None = None) -> str:
                raise Exception("API error")
            def generate_stream(self, prompt: str, system: str | None = None):
                raise Exception("API error")
            def health_check(self) -> bool:
                return True
            async def generate_async(self, prompt: str, system: str | None = None) -> str:
                raise Exception("API error")
            async def generate_stream_async(self, prompt: str, system: str | None = None):
                raise Exception("API error")

        extractor = EntityExtractor(llm_provider=ErrorProvider())
        entities = extractor.extract(sample_document)

        assert entities == []

    def test_parse_entities_single_line(self):
        """Parse single entity from LLM response."""
        raw_text = "ENTITY: Andrej Karpathy | person | Computer scientist"
        extractor = EntityExtractor()
        entities = extractor._parse_entities(raw_text)

        assert len(entities) == 1
        assert entities[0].name == "Andrej Karpathy"
        assert entities[0].entity_type == "person"
        assert entities[0].description == "Computer scientist"

    def test_parse_entities_multiple_lines(self):
        """Parse multiple entities from LLM response."""
        raw_text = """
        ENTITY: Andrej Karpathy | person | Computer scientist
        ENTITY: OpenAI | organization | AI research lab
        ENTITY: Tesla | company | Electric vehicle manufacturer
        """
        extractor = EntityExtractor()
        entities = extractor._parse_entities(raw_text)

        assert len(entities) == 3
        assert entities[0].name == "Andrej Karpathy"
        assert entities[1].name == "OpenAI"
        assert entities[2].name == "Tesla"

    def test_parse_entities_handles_malformed_lines(self):
        """Parser skips malformed lines."""
        raw_text = """
        ENTITY: Andrej Karpathy | person | Computer scientist
        This is not a valid entity line
        ENTITY: OpenAI | organization | AI research lab
        """
        extractor = EntityExtractor()
        entities = extractor._parse_entities(raw_text)

        assert len(entities) == 2
        assert entities[0].name == "Andrej Karpathy"
        assert entities[1].name == "OpenAI"


class TestConceptExtraction:
    """Tests for concept extraction functionality."""

    def test_extract_concepts_from_document(self, sample_document):
        """Extract concepts from a document using LLM."""
        mock_provider = MockLLMProvider(response="""
        CONCEPT: Deep Learning | Subset of ML using neural networks | Andrej Karpathy, OpenAI
        CONCEPT: Transformer Architecture | Attention-based neural network | Google, OpenAI
        CONCEPT: Autonomous Driving | Self-driving vehicle technology | Tesla
        """)

        extractor = EntityExtractor(llm_provider=mock_provider)
        concepts = extractor.extract_concepts(sample_document, source_doc="test.md")

        assert len(concepts) == 3
        assert concepts[0].name == "Deep Learning"
        assert "neural networks" in concepts[0].definition
        assert "Andrej Karpathy" in concepts[0].related_entities

    def test_extract_concepts_handles_empty_response(self, sample_document):
        """Extract concepts returns empty list when LLM returns empty response."""
        mock_provider = MockLLMProvider(response="")

        extractor = EntityExtractor(llm_provider=mock_provider)
        concepts = extractor.extract_concepts(sample_document)

        assert concepts == []

    def test_extract_concepts_handles_api_error(self, sample_document):
        """Extract concepts returns empty list when LLM API fails."""
        class ErrorProvider(LLMProvider):
            def generate(self, prompt: str, system: str | None = None) -> str:
                raise Exception("API error")
            def generate_stream(self, prompt: str, system: str | None = None):
                raise Exception("API error")
            def health_check(self) -> bool:
                return True
            async def generate_async(self, prompt: str, system: str | None = None) -> str:
                raise Exception("API error")
            async def generate_stream_async(self, prompt: str, system: str | None = None):
                raise Exception("API error")

        extractor = EntityExtractor(llm_provider=ErrorProvider())
        concepts = extractor.extract_concepts(sample_document)

        assert concepts == []

    def test_parse_concepts_single_line(self):
        """Parse single concept from LLM response."""
        raw_text = "CONCEPT: Deep Learning | ML subset using neural networks | OpenAI, Karpathy"
        extractor = EntityExtractor()
        concepts = extractor._parse_concepts(raw_text)

        assert len(concepts) == 1
        assert concepts[0].name == "Deep Learning"
        assert "neural networks" in concepts[0].definition
        assert "OpenAI" in concepts[0].related_entities
        assert "Karpathy" in concepts[0].related_entities

    def test_parse_concepts_multiple_lines(self):
        """Parse multiple concepts from LLM response."""
        raw_text = """
        CONCEPT: Deep Learning | ML subset | Karpathy
        CONCEPT: Transformers | Attention mechanism | Google, OpenAI
        CONCEPT: RLHF | Reinforcement learning from feedback | OpenAI
        """
        extractor = EntityExtractor()
        concepts = extractor._parse_concepts(raw_text)

        assert len(concepts) == 3
        assert concepts[0].name == "Deep Learning"
        assert concepts[1].name == "Transformers"
        assert concepts[2].name == "RLHF"

    def test_parse_concepts_no_related_entities(self):
        """Parser handles concepts with no related entities."""
        raw_text = "CONCEPT: Attention Mechanism | Way to weight inputs |"
        extractor = EntityExtractor()
        concepts = extractor._parse_concepts(raw_text)

        assert len(concepts) == 1
        assert concepts[0].name == "Attention Mechanism"
        assert concepts[0].related_entities == []

    def test_parse_concepts_handles_malformed_lines(self):
        """Parser skips malformed concept lines."""
        raw_text = """
        CONCEPT: Deep Learning | ML subset | Karpathy
        Invalid line without CONCEPT prefix
        CONCEPT: Transformers | Attention | Google
        """
        extractor = EntityExtractor()
        concepts = extractor._parse_concepts(raw_text)

        assert len(concepts) == 2


class TestLogging:
    """Tests for logging behavior."""

    def test_extraction_logs_success(self, caplog, sample_document):
        """Extraction logs info message on success."""
        import logging
        mock_provider = MockLLMProvider(response="ENTITY: Test | person | Description")

        extractor = EntityExtractor(llm_provider=mock_provider)
        with caplog.at_level(logging.INFO):
            extractor.extract(sample_document)

        assert "Extracted 1 unique entities" in caplog.text

    def test_extraction_logs_error(self, caplog, sample_document):
        """Extraction logs error on failure."""
        import logging

        class ErrorProvider(LLMProvider):
            def generate(self, prompt: str, system: str | None = None) -> str:
                raise Exception("Test error")
            def generate_stream(self, prompt: str, system: str | None = None):
                raise Exception("Test error")
            def health_check(self) -> bool:
                return True
            async def generate_async(self, prompt: str, system: str | None = None) -> str:
                raise Exception("Test error")
            async def generate_stream_async(self, prompt: str, system: str | None = None):
                raise Exception("Test error")

        extractor = EntityExtractor(llm_provider=ErrorProvider())
        with caplog.at_level(logging.ERROR):
            extractor.extract(sample_document)

        assert "entity extraction failed" in caplog.text.lower()
