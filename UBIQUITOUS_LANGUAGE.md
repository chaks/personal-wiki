# Ubiquitous Language

## Source Management

| Term              | Definition                                                                 | Aliases to avoid                   |
|-------------------|----------------------------------------------------------------------------|------------------------------------|
| **Source**        | A configured input to be ingested into the wiki (PDF, URL, markdown, code) | Input, document, file, data source |
| **Source Type**   | The format of a source: pdf, url, markdown, or code                        | Kind, format, category             |
| **Registry**      | Persistent JSON tracking of all sources with content hashes and status     | Database, index, catalog           |
| **Source Entry**  | A single record in the registry representing one source                    | Source record, entry               |
| **Source Status** | Lifecycle state of a source: pending, processing, processed, or failed     | State, phase                       |
| **Content Hash**  | SHA256 fingerprint of a source file used for change detection              | Checksum, digest, signature        |

## Wiki Content

| Term              | Definition                                                                                   | Aliases to avoid             |
|-------------------|----------------------------------------------------------------------------------------------|------------------------------|
| **Entity**        | A concrete thing extracted from documents (person, organization, product, technology)        | Object, item, noun           |
| **Concept**       | An abstract idea extracted from documents (theory, pattern, methodology)                     | Idea, topic, theme           |
| **Wiki Page**     | A markdown file with frontmatter in the wiki hierarchy                                       | Document, article, note      |
| **Wiki Category** | A subdirectory in the wiki (entities, concepts, events, documents)                           | Namespace, folder, section   |
| **Frontmatter**   | YAML metadata at the top of a wiki page (title, category, timestamps)                        | Header, metadata block       |
| **Slug**          | A URL-safe filename derived from a page title (e.g. "Machine Learning" → "machine-learning") | Filename, key, name          |
| **Placeholder**   | An auto-generated empty page created for a wikilink with no target                           | Stub, skeleton page          |
| **Orphan**        | A wiki page with no incoming wikilinks from other pages                                      | Unlinked page, isolated page |

## Link System

| Term              | Definition                                                           | Aliases to avoid                 |
|-------------------|----------------------------------------------------------------------|----------------------------------|
| **Wikilink**      | An internal reference to another wiki page using `[[title]]` syntax  | Internal link, reference         |
| **Broken Link**   | A wikilink whose target page was deleted or never existed            | Dead link, dangling link         |
| **Link Resolver** | Component that finds missing wikilinks and creates placeholder pages | Link checker, reference resolver |

## Ingestion Pipeline

| Term                   | Definition                                                                                 | Aliases to avoid                |
|------------------------|--------------------------------------------------------------------------------------------|---------------------------------|
| **Ingestion**          | The pipeline that converts sources to markdown and extracts knowledge                      | Processing, parsing, conversion |
| **Docling**            | Document conversion engine that transforms PDFs and other formats to markdown              | Converter, Docling ingestor     |
| **Full Pipeline**      | Mode where markdown sources go through LLM entity/concept extraction (not just copy+index) | Full mode, full pipeline flag   |
| **Simple Index**       | Mode where markdown sources are copied and indexed without LLM extraction                  | Copy and index, light pipeline  |
| **Source Document**    | The original document being processed (referenced in extracted items)                      | Parent document, origin         |
| **Entity Extraction**  | LLM-powered identification of concrete entities from document text                         | NER, entity recognition         |
| **Concept Extraction** | LLM-powered identification of abstract concepts from document text                         | Idea extraction, topic mining   |

## Semantic Search

| Term           | Definition                                                                                  | Aliases to avoid            |
|----------------|---------------------------------------------------------------------------------------------|-----------------------------|
| **Indexer**    | Component that embeds wiki pages into Qdrant for semantic search                            | Search engine, vector store |
| **Chunk**      | A segment of wiki page content (split by headings or fixed size, ~3000 chars) for embedding | Section, fragment, block    |
| **Embedding**  | A 768-dimensional vector representation of text for similarity search                       | Vector, encoding            |
| **Collection** | A Qdrant index containing all wiki page embeddings                                          | Index, vector space         |
| **Top-k**      | The number of most relevant results returned from a semantic search                         | Result count, k results     |

## Wiki Quality

| Term              | Definition                                                                                                  | Aliases to avoid                |
|-------------------|-------------------------------------------------------------------------------------------------------------|---------------------------------|
| **Wiki Linter**   | Component that detects wiki health issues (orphans, broken links, duplicates, contradictions, stale claims) | Health checker, validator       |
| **Duplicate**     | Two or more wiki pages with near-identical content (detected by Jaccard similarity)                         | Near-duplicate, similar content |
| **Stale Claim**   | A claim in a wiki page whose content has not been updated within a configurable age threshold               | Outdated claim, old content     |
| **Contradiction** | Conflicting statements between two wiki pages on the same topic                                             | Conflict, inconsistency         |

## Query & Response

| Term               | Definition                                                                                     | Aliases to avoid                   |
|--------------------|------------------------------------------------------------------------------------------------|------------------------------------|
| **Chat Engine**    | Component that handles user queries with RAG over the wiki, including semantic search fallback | Query handler, assistant           |
| **Chat Service**   | Wrapper that adds session-based history persistence on top of the chat engine                  | Chat handler, conversation service |
| **Chat History**   | SQLite-backed persistence of question-answer pairs grouped by session                          | Conversation log, message log      |
| **Session**        | A named sequence of chat exchanges representing one user interaction                           | Conversation, thread               |
| **Context Pages**  | Wiki pages retrieved as relevant context for answering a query                                 | Results, retrieved documents       |
| **Keyword Search** | Fallback search that matches query text against wiki files directly                            | Local search, file search          |

## Relationships

- A **Source** is tracked by a **Source Entry** in the **Registry** with a **Source Status**
- A **Source Entry** produces one or more **Wiki Pages** via **Ingestion**
- A **Wiki Page** lives in a **Wiki Category** and has a **Slug** derived from its title
- A **Wiki Page** may contain zero or more **Wikilinks** to other pages
- A **Placeholder** is created when a **Wikilink** has no target page
- An **Orphan** is a **Wiki Page** with no incoming **Wikilinks**
- A **Broken Link** is a **Wikilink** whose target page was deleted
- The **Link Resolver** finds **Broken Links** and missing targets, creating **Placeholders**
- A **Wiki Page** is split into one or more **Chunks** by the **Indexer** for embedding
- The **Chat Engine** retrieves **Context Pages** from the **Indexer** to answer queries
- The **Chat Service** persists question-answer pairs in **Chat History** by **Session**
- The **Registry** tracks each **Source** by its **Content Hash** to detect changes
- A **Source** with **Full Pipeline** enabled undergoes **Entity Extraction** and **Concept Extraction**

## Example dialogue

> **Dev:** "When I add a new **Source** to `sources.yaml`, what happens during **Ingestion**?"
>
> **Domain expert:** "The **Ingestion** pipeline computes the **Content Hash** and checks the **Registry**. If
> unchanged, it skips. If new or changed, it converts to markdown via **Docling**, then either runs the **Full Pipeline
** (entity and concept extraction, wiki page creation) or does a **Simple Index** (copy and embed only), depending on
> the source config."

> **Dev:** "So if I link to `[[Machine Learning]]` but no such page exists yet?"
>
> **Domain expert:** "The **Link Resolver** detects the missing page and creates a **Placeholder** with a slug of
`machine-learning.md` in the entities category. The **Wiki Linter** will flag it as an **Orphan** if no other page links
> to it, or as a **Broken Link** if the target was deleted."

> **Dev:** "And when the **Curator** asks a question via chat?"
>
> **Domain expert:** "The **Chat Engine** uses the **Indexer** to find **Context Pages** via semantic search — falling
> back to **Keyword Search** if Qdrant is unavailable. The **Chat Service** wraps that and persists the exchange in **Chat
History** under the current **Session**."

> **Dev:** "What about wiki page content that gets too long?"
>
> **Domain expert:** "The **Indexer** splits each **Wiki Page** into **Chunks** of about 3000 characters, respecting
> heading boundaries. Each chunk gets its own embedding, so semantic search can retrieve the most relevant section."

## Flagged ambiguities

- **"Document"** was used to mean both a **Source** (input file) and a **Wiki Page** (output). Recommendation: use *
  *Source** for inputs, **Wiki Page** for outputs, **Source Document** only when referencing the origin of an extracted
  item in frontmatter.

- **"Index"** was used for both the **Registry** (source tracking) and the **Indexer** (Qdrant vector search). These are
  distinct: the **Registry** tracks what has been ingested; the **Indexer** enables semantic search over wiki content.

- **"Link"** was used for both a **Wikilink** (internal wiki reference) and a URL **Source**. Use **Wikilink** for
  `[[internal]]` references, **URL** for web sources.

- **"Category"** was used for both a **Wiki Category** (directory like `entities/`) and the `category` field in
  frontmatter. These are the same concept — the frontmatter value determines which directory the page lives in.

- **"Full Pipeline"** vs **"Simple Index"** — both apply to markdown sources. **Full Pipeline** runs LLM extraction; *
  *Simple Index** just copies and embeds. Don't use "pipeline" generically — it refers specifically to the LLM
  extraction stage.
