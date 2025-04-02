# GraphRAG Source Code

This directory contains the core source code for the GraphRAG hybrid retrieval system.

## Module Structure

- `__init__.py` - Package initialization
- `config.py` - Configuration management and environment loading

### Subdirectories

- `processors/` - Document processing components
  - `markdown_processor.py` - Processing and chunking markdown documents
  
- `utils/` - Utility functions and helpers
  - `neo4j_utils.py` - Neo4j database utilities
  - `qdrant_utils.py` - Qdrant vector database utilities
  - `query_utils.py` - Query interface for the hybrid system
  - `text_utils.py` - Text processing utilities

## Core Components

### Document Processing

The document processing pipeline handles:
- Reading and parsing markdown files
- Chunking text into semantic units
- Extracting metadata and relationships
- Topic identification

### Database Utilities

The database utilities provide:
- Connection management for Neo4j and Qdrant
- Schema setup and validation
- Query builders and result processors
- Transaction management

### Query Engine

The query interface supports:
- Hybrid semantic and graph-based search
- Context expansion for richer results
- Topic and category filtering
- Document relationship traversal

## Using the Code

Import the modules as needed:

```python
from src.config import load_config
from src.utils.neo4j_utils import Neo4jHelper
from src.utils.qdrant_utils import QdrantHelper
from src.utils.query_utils import QueryEngine
from src.processors.markdown_processor import MarkdownProcessor

# Example usage
config = load_config()
neo4j = Neo4jHelper(config)
qdrant = QdrantHelper(config)
query_engine = QueryEngine(neo4j, qdrant)
``` 