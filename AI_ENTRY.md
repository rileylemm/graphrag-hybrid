# GraphRAG: Entry Point for AI Agents

Welcome, AI agent! This document provides a comprehensive overview of the GraphRAG system to help you understand and navigate this repository effectively.

## System Overview

GraphRAG is a hybrid retrieval augmentation generation (RAG) system that leverages both Neo4j (graph database) and Qdrant (vector database) to provide enhanced document retrieval capabilities. The system processes Markdown documents with YAML frontmatter, establishing relationships between documents while enabling semantic search capabilities.

## Core Components

### Document Processing
- **Location**: `src/processors/document_processor.py`
- **Purpose**: Parses and chunks Markdown documents, extracts metadata from YAML frontmatter
- **Key Functions**: `process_document()`, `chunk_document()`, `extract_metadata()`

### Database Integration
- **Neo4j Manager**: `src/database/neo4j_manager.py` - Handles graph database operations
- **Qdrant Manager**: `src/database/qdrant_manager.py` - Manages vector database operations
- **Key Functions**: `store_document()`, `create_relationship()`, `search_vectors()`

### Query Engine
- **Location**: `src/query_engine.py`
- **Purpose**: Combines graph-based and vector-based search for enhanced retrieval
- **Key Functions**: `hybrid_search()`, `category_search()`, `expand_context()`

## Database Connection Parameters

**Neo4j**
- HTTP Port: 7474
- Bolt Port: 7687
- Authentication: neo4j/password
- Environment Variables:
  ```
  NEO4J_URI=bolt://localhost:7687
  NEO4J_HTTP_URI=http://localhost:7474
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=password
  ```

**Qdrant**
- HTTP Port: 6333
- Collection: document_chunks
- Environment Variables:
  ```
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  QDRANT_COLLECTION=document_chunks
  ```

## Directory Structure

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
├── your_docs_here/               # Add markdown documents here
├── data/                         # Data storage directory
├── guides/                       # User guides and documentation
│   └── mcp/                      # MCP integration guides
├── test_db_connection/           # Database connection testing
├── docker-compose.yml            # Docker-compose for Neo4j and Qdrant
├── requirements.txt              # Python dependencies
└── .env.example                  # Example environment variables
```

## Key Files to Examine

1. **Configuration**: `src/config.py` - Contains system configuration
2. **Query Engine**: `src/query_engine.py` - Core query logic
3. **Import Script**: `scripts/import_docs.py` - Document import process
4. **Testing**: `test_db_connection/test_connections.py` - Database connection verification

## Database Schema

### Neo4j Schema
- **Document Nodes**: Represent entire documents
- **Chunk Nodes**: Represent document chunks
- **Relationships**:
  - `CONTAINS`: Document to chunk relationship
  - `RELATED_TO`: Document to document relationship
  - `NEXT`: Chunk to chunk sequential relationship
  - `CHILD_OF`: Hierarchical relationship based on document structure

### Qdrant Collection
- **Collection**: document_chunks
- **Vector Dimension**: 384 (using all-MiniLM-L6-v2 embeddings)
- **Payload**: Contains metadata like document_id, chunk_id, content, category

## Integration Guidelines

For MCP integration, refer to the guides in `guides/mcp/` directory. These provide detailed instructions on:
- Connecting to both databases
- Querying documents using hybrid approach
- Processing query results
- Error handling and troubleshooting

## Document Processing Flow

1. **Document Parsing**: Extract YAML frontmatter and content
2. **Chunking**: Split content into manageable chunks
3. **Embedding Generation**: Create vector embeddings for chunks
4. **Storage**: Store document metadata in Neo4j and embeddings in Qdrant
5. **Relationship Creation**: Establish connections between documents and chunks

## Query Flow

1. **Query Processing**: Parse and understand user query
2. **Vector Search**: Find semantically similar chunks in Qdrant
3. **Graph Expansion**: Use Neo4j to expand context around matching chunks
4. **Result Combination**: Merge and rank results from both sources
5. **Response Generation**: Format results for presentation

## Testing Resources

- **Connection Testing**: `test_db_connection/test_connections.py`
- **Query Testing**: `scripts/query_demo.py`

## Additional Resources

- Index files in each directory provide more specific information
- The `guides` directory contains detailed documentation on system components
- For MCP integration specifics, refer to `guides/mcp/index.md` 