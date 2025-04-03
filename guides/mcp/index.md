# GraphRAG MCP Integration Guide

This directory contains guides and examples for integrating the GraphRAG system with MCP (Multi-Channel Platform). The guides cover both Neo4j and Qdrant database connections and querying.

## Contents

1. [Connection Setup](connection.md) - How to configure and establish connections to Neo4j and Qdrant
2. [Query Implementation](query.md) - Implementing query functionality in your MCP tools
3. [Error Handling](error_handling.md) - Common errors and how to handle them
4. [Examples](examples.md) - Example implementations and usage patterns

## Quick Start

The GraphRAG system uses the following connection parameters:

### Neo4j Connection
- HTTP Port: 7474 (standard port)
- Bolt Port: 7687 (standard port)
- Authentication: neo4j/password
- Protocol: bolt

### Qdrant Connection
- HTTP Port: 6333 (standard port)
- gRPC Port: 6334
- Collection Name: document_chunks
- Vector Size: 384
- Distance Metric: Cosine

## Implementation Overview

The GraphRAG system combines Neo4j for document relationships and Qdrant for vector embeddings. Your MCP implementation will need to:

1. Connect to both databases
2. Generate embeddings for queries
3. Search Qdrant for relevant vectors
4. Query Neo4j for related documents
5. Combine and rank results

See the individual guides for detailed implementation instructions.

## Key Documentation Topics

- **[Testing](testing.md)**: Methods for testing your MCP integration
- **Document Structure**: Documents in GraphRAG consist of Document nodes in Neo4j and vector embeddings in Qdrant
- **Query Types**: Support for semantic search (Qdrant), category search (Neo4j), and hybrid approaches
- **Error Handling**: Implement retry logic and version compatibility checks for robust operation

## Sample Code

Basic implementation for querying the GraphRAG databases:

```python
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import sentence_transformers
import warnings

# Suppress Qdrant version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

# Neo4j connection
neo4j_driver = GraphDatabase.driver(
    "bolt://localhost:7687", 
    auth=("neo4j", "password")
)

# Qdrant connection
qdrant_client = QdrantClient(
    host="localhost",
    port=6333
)

# Load embedding model
model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
```

## Additional Resources

- The `src/database` directory contains comprehensive Neo4j and Qdrant managers
- The `src/graphrag_mcp_tool.py` provides a reference implementation for MCP integration
- See the [Database Setup Guide](../database_setup.md) for detailed database configuration instructions
- Refer to [Connection Testing](../testing/index.md) for troubleshooting connection issues

## Troubleshooting

If you encounter issues with the integration, check:

1. **Docker Status**: Ensure both containers are running with `docker ps`
2. **Port Mapping**: Verify ports are correctly mapped in `docker-compose.yml`
3. **Model Compatibility**: Ensure the embedding model matches the vector size (384)
4. **Version Compatibility**: 
   - Handle Qdrant client/server version differences
   - Use try/except blocks for different API versions
5. **Health Checks**: Use the provided health check utilities to verify connections
