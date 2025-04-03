# GraphRAG: Hybrid Neo4j and Qdrant Retrieval System

A powerful retrieval augmentation generation (RAG) system that combines Neo4j graph database and Qdrant vector database for advanced document retrieval. This system provides a hybrid approach that leverages both document relationships and vector similarity for enhanced search capabilities.

> **AI Agents**: If you're an AI agent exploring this repository, start with [AI_ENTRY.md](AI_ENTRY.md) for a comprehensive overview.

## System Overview

GraphRAG uses two complementary databases:

1. **Neo4j Graph Database**: Stores document relationships, categories, and metadata
2. **Qdrant Vector Database**: Stores document chunk embeddings for semantic search

## Verified Database Connection Information

| Database | Service | Port | Authentication |
|----------|---------|------|---------------|
| Neo4j    | HTTP    | 7474 | neo4j/password |
| Neo4j    | Bolt    | 7687 | neo4j/password |
| Qdrant   | HTTP    | 6333 | None (default) |

### Connection Parameters

For use in applications:

```
# Neo4j Configuration
NEO4J_HTTP_URI=http://localhost:7474
NEO4J_BOLT_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=document_chunks
```

## Features

- **Document Processing**: Parse and chunk Markdown documents with YAML frontmatter
- **Semantic Search**: Vector-based similarity search using transformer models
- **Graph-based Navigation**: Explore document relationships using Neo4j graph database
- **Hybrid Search**: Combine semantic and graph-based approaches for better results
- **External Integration**: Ready-to-use tools for integration with external systems

## Project Structure

```
graphrag/
├── src/                          # Source code
│   ├── config.py                 # Configuration management
│   ├── query_engine.py           # Hybrid query engine
│   ├── database/                 # Database managers
│   │   ├── neo4j_manager.py      # Neo4j database manager
│   │   └── qdrant_manager.py     # Qdrant vector database manager
│   └── processors/               # Data processors
│       ├── document_processor.py # Document parsing and chunking
│       └── embedding_processor.py # Text embedding generation
├── scripts/                      # Utility scripts
│   ├── import_docs.py            # Document import script
│   └── query_demo.py             # Query demonstration script
├── your_docs_here/               # Add your markdown documents here
├── data/                         # Data storage directory
├── guides/                       # User guides and documentation
├── test_db_connection/           # Database connection testing
├── docker-compose.yml            # Docker-compose for Neo4j and Qdrant
├── requirements.txt              # Python dependencies
└── .env.example                  # Example environment variables
```

## Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Neo4j 5.x
- Qdrant 1.5.0+

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/graphrag.git
cd graphrag
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create configuration file:

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start Neo4j and Qdrant using Docker:

```bash
docker-compose up -d
```

### Importing Documents

To import documents into the system:

```bash
python scripts/import_docs.py --docs-dir ./your_docs_here --recursive
```

This will:
- Process all Markdown files in the directory
- Extract metadata from YAML frontmatter
- Chunk the documents into manageable pieces
- Store document metadata and relationships in Neo4j
- Generate embeddings and store them in Qdrant

## Usage

### Running Queries

Use the query demo script to explore the system:

```bash
# Hybrid search
python scripts/query_demo.py --query "What is GraphRAG?" --type hybrid --limit 5

# Category search
python scripts/query_demo.py --query "documentation" --type category --category "user-guide"

# Get document by ID
python scripts/query_demo.py --document "doc_123456"

# List all categories
python scripts/query_demo.py --list-categories

# Show system statistics
python scripts/query_demo.py --stats
```

### External Integration

To integrate with external systems, use the provided Python modules in the `src` directory. See the guides in the `guides/mcp` directory for detailed integration instructions.

## Document Format Requirements

The system processes Markdown files with YAML frontmatter. For optimal results, follow this format:

### Required Front Matter Format

```markdown
---
title: Analytics and Monitoring              # Document title (required)
category: frontend/ux                        # Category path (required)
updated: '2023-04-01'                        # Last updated date (optional)
related:                                     # Related documents (optional)
- ui/DATA_FETCHING.md
- ui/STATE_MANAGEMENT.md
- ux/USER_FLOWS.md
key_concepts:                                # Key concepts for indexing (optional)
- analytics_integration
- user_behavior_tracking
- performance_monitoring
---

# Analytics and Monitoring

This document outlines the approach to analytics and monitoring within the application.

## Analytics Strategy

### Core Principles

The analytics implementation adheres to these principles:

- **Purpose-Driven**: Collection tied to specific business or UX questions
- **Privacy-First**: Minimal data collection with clear user consent

## Performance Monitoring

Code examples should use language identifiers:

```javascript
function trackEvent(eventName, properties) {
  analytics.track(eventName, {
    timestamp: new Date().toISOString(),
    ...properties
  });
}
```
```

### Document Structure Best Practices

- Start with a single `# Title` (H1) heading after the front matter
- Use proper heading hierarchy (`##`, `###`, etc.)
- Include code blocks with language identifiers
- Use lists, tables, and other markdown features as needed
- Link to related documents where appropriate
- Include key concepts that might be important for retrieval

The system will process these documents by:
1. Parsing the front matter metadata
2. Extracting hierarchical structure from headings
3. Splitting content into appropriate chunks
4. Creating relationships based on the "related" field
5. Indexing key concepts for enhanced retrieval

## Configuration

Configure the system by setting environment variables or using a `.env` file:

- **Neo4j Configuration**: 
  - `NEO4J_URI=bolt://localhost:7687`
  - `NEO4J_HTTP_URI=http://localhost:7474`
  - `NEO4J_USERNAME=neo4j`
  - `NEO4J_PASSWORD=password`

- **Qdrant Configuration**: 
  - `QDRANT_HOST=localhost`
  - `QDRANT_PORT=6333`
  - `QDRANT_COLLECTION=document_chunks`

- **Embedding Configuration**: Model settings for text embeddings
- **Chunking Configuration**: Document chunking parameters

## Verification

After setup, verify database connections:

```bash
python test_db_connection/test_connections.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Neo4j](https://neo4j.com/) for graph database
- [Qdrant](https://qdrant.tech/) for vector similarity search
- [HuggingFace](https://huggingface.co/) for transformer models 