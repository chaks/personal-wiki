# Ubiquitous Language

## Source Ingestion

| Term             | Definition                                                            | Aliases to avoid                |
| ---------------- | --------------------------------------------------------------------- | ------------------------------- |
| **Source**       | A document to be ingested into the wiki (PDF, URL, markdown, code)    | Input, document, file           |
| **Registry**     | Persistent tracking of all ingested sources with content hashes       | Database, index, catalog        |
| **Content Hash** | SHA256 fingerprint of a source file used for change detection         | Checksum, digest, signature     |
| **Ingestion**    | The pipeline that converts sources to markdown and extracts knowledge | Processing, parsing, conversion |

## Wiki Content

| Term            | Definition                                                                            | Aliases to avoid             |
| --------------- | ------------------------------------------------------------------------------------- | ---------------------------- |
| **Entity**      | A concrete thing extracted from documents (person, organization, product, technology) | Object, item, noun           |
| **Concept**     | An abstract idea extracted from documents (theory, pattern, methodology)              | Idea, topic, theme           |
| **Wiki Page**   | A markdown file with frontmatter in the wiki hierarchy                                | Document, article, note      |
| **Frontmatter** | YAML metadata at the top of a wiki page (title, category, timestamps)                 | Header, metadata block       |
| **Wikilink**    | A link to another wiki page using `[[title]]` syntax                                  | Internal link, reference     |
| **Placeholder** | An auto-generated empty page created for a wikilink with no target                    | Stub, skeleton page          |
| **Orphan**      | A wiki page with no incoming wikilinks from other pages                               | Unlinked page, isolated page |

## Knowledge Extraction

| Term                   | Definition                                                            | Aliases to avoid              |
| ---------------------- | --------------------------------------------------------------------- | ----------------------------- |
| **Entity Extraction**  | LLM-powered identification of concrete entities from document text    | NER, entity recognition       |
| **Concept Extraction** | LLM-powered identification of abstract concepts from document text    | Idea extraction, topic mining |
| **Source Document**    | The original document being processed (referenced in extracted items) | Parent document, origin       |

## Semantic Search

| Term           | Definition                                                            | Aliases to avoid            |
| -------------- | --------------------------------------------------------------------- | --------------------------- |
| **Indexer**    | Component that embeds wiki pages into Qdrant for semantic search      | Search engine, vector store |
| **Embedding**  | A 768-dimensional vector representation of text for similarity search | Vector, encoding            |
| **Collection** | A Qdrant index containing all wiki page embeddings                    | Index, vector space         |
| **Top-k**      | The number of most relevant results returned from a semantic search   | Result count, k results     |

## Wiki Maintenance

| Term                | Definition                                                                        | Aliases to avoid                 |
| ------------------- | --------------------------------------------------------------------------------- | -------------------------------- |
| **Link Resolver**   | Component that finds and creates placeholder pages for missing wikilinks          | Link checker, reference resolver |
| **Linter**          | Component that detects wiki health issues (orphans, contradictions, stale claims) | Health checker, validator        |
| **Wiki Maintainer** | Component that creates and updates wiki pages with LLM-generated content          | Page writer, content manager     |

## Query & Response

| Term              | Definition                                                       | Aliases to avoid             |
| ----------------- | ---------------------------------------------------------------- | ---------------------------- |
| **Chat Engine**   | Component that handles user queries with RAG over the wiki       | Query handler, assistant     |
| **Context Pages** | Wiki pages retrieved as relevant context for answering a query   | Results, retrieved documents |
| **RAG**           | Retrieval-augmented generation: search wiki then generate answer | Retrieval-based QA           |

## People & Actors

| Term        | Definition                                                          | Aliases to avoid     |
| ----------- | ------------------------------------------------------------------- | -------------------- |
| **Curator** | The human user who adds sources and reviews wiki output             | User, admin, owner   |
| **LLM**     | The language model (gemma4:e2b) that extracts entities and concepts | Model, extractor, AI |

## Relationships

- A **Source** produces one or more **Entities** and **Concepts** via **Ingestion**
- An **Entity** or **Concept** is stored as a **Wiki Page** with **Frontmatter**
- A **Wiki Page** may contain zero or more **Wikilinks** to other pages
- A **Placeholder** is created when a **Wikilink** has no target page
- An **Orphan** is a **Wiki Page** with no incoming **Wikilinks**
- The **Chat Engine** retrieves **Context Pages** from the **Indexer** to answer queries
- The **Registry** tracks each **Source** by its **Content Hash** to detect changes

## Example dialogue

> **Dev:** "When I add a new **Source** to `sources.yaml`, what happens during **Ingestion**?"
>
> **Domain expert:** "The **Ingestion** pipeline computes the **Content Hash** and checks the **Registry**. If unchanged, it skips. If new or changed, it converts to markdown, runs **Entity Extraction** and **Concept Extraction**, writes **Wiki Pages**, and indexes them in Qdrant."
>
> **Dev:** "So if I link to `[[Machine Learning]]` but no such **Entity** exists yet?"
>
> **Domain expert:** "The **Link Resolver** detects the missing page and creates a **Placeholder**. The **Linter** will later flag it as an **Orphan** if no other page links to it."
>
> **Dev:** "And when the **Curator** asks a question via the **Chat Engine**?"
>
> **Domain expert:** "The **Chat Engine** uses the **Indexer** to find **Context Pages** via semantic search, then the **LLM** generates an answer using RAG."

## Flagged ambiguities

- **"Document"** was used to mean both a **Source** (input file) and a **Wiki Page** (output). Recommendation: use **Source** for inputs, **Wiki Page** for outputs, **Source Document** only when referencing the origin of an extracted item in frontmatter.

- **"Index"** was used for both the **Registry** (source tracking) and the **Indexer** (Qdrant vector search). These are distinct: the **Registry** tracks what has been ingested; the **Indexer** enables semantic search over wiki content.

- **"Link"** was used for both a **Wikilink** (internal wiki reference) and a URL **Source**. Use **Wikilink** for `[[internal]]` references, **URL** for web sources.
