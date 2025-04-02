# GraphRAG AI Entry Point

This document serves as the entry point for AI agents exploring this hybrid Neo4j and Qdrant retrieval system.

## System Overview

This is a hybrid retrieval augmentation generation (RAG) system that combines:
- **Neo4j** graph database for document relationships and metadata
- **Qdrant** vector database for semantic similarity search

The system processes Markdown documents with YAML frontmatter, stores their relationships in Neo4j, and their vector embeddings in Qdrant for hybrid search capabilities.

## Database Connection Parameters

**Neo4j**
- HTTP Port: 7474
- Bolt Port: 7687
- Authentication: neo4j/password

**Qdrant**
- HTTP Port: 6333
- Collection: document_chunks

## Key Components

1. **Document Processing Pipeline**
   - `src/processors/document_processor.py`: Parses and chunks documents
   - `src/processors/embedding_processor.py`: Generates vector embeddings

2. **Database Management**
   - `src/database/neo4j_manager.py`: Handles Neo4j operations
   - `src/database/qdrant_manager.py`: Handles Qdrant operations

3. **Query Engine**
   - `src/query_engine.py`: Implements hybrid search across both databases

## Important Scripts

- `scripts/setup_databases.py`: Sets up both databases
- `scripts/import_docs.py`: Imports documentation
- `scripts/query_demo.py`: Demonstrates querying capabilities
- `test_db_connection/test_connections.py`: Verifies database connections

## Verification and Testing

To verify database connections:
```bash
python test_db_connection/test_connections.py
```

To rebuild the database and import documentation:
```bash
# Setup databases
python scripts/setup_databases.py

# Import documentation
python scripts/import_docs.py --docs-dir ./your_docs_here
```

## Directory Structure

- `src/`: Core source code
- `scripts/`: Utility scripts
- `your_docs_here/`: Add your markdown documents here
- `data/`: Data storage
- `guides/`: User guides and documentation
- `test_db_connection/`: Database connection testing

## Configuration

Environment variables are defined in `.env` (see `.env.example` for template):
- Neo4j connection parameters (port 7687)
- Qdrant connection parameters (port 6333)
- Embedding model configuration
- Chunking parameters

## Integration Notes

This system is designed to be integrated with an external MCP (Multi-Channel Platform) server. It does not implement an MCP server itself. 

For MCP integration details, see the guides in `guides/mcp/` directory.

## Document Format

Documents should be in Markdown format with YAML frontmatter:

```markdown
---
title: Document Title
category: user-guide
updated: '2023-01-01'
related:
- related/document1.md
- related/document2.md
key_concepts:
- concept_one
- concept_two
---

# Document Title

Your document content here...
```

## Further Information

- Project documentation: `guides/index.md`
- Database connection testing: `test_db_connection/index.md`
- MCP integration: `guides/mcp/index.md` 