# GraphRAG MCP Integration

This guide provides essential information for integrating the GraphRAG system with a Multi-Channel Platform (MCP).

## Connection Parameters

For connecting to the GraphRAG databases:

**Neo4j**
- Bolt Port: `7688`
- HTTP Port: `7475`
- Username: `neo4j`
- Password: `password`

**Qdrant**
- HTTP Port: `6335`
- Collection: `document_chunks`

## Integration Steps

1. **Configure Environment**: Set up connection parameters in your MCP environment
2. **Implement Tool**: Create a tool class that connects to both databases
3. **Handle Version Compatibility**: Implement error handling for Qdrant client versions
4. **Test Connections**: Verify connections to both databases using the correct ports

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
    "bolt://localhost:7688", 
    auth=("neo4j", "password")
)

# Qdrant connection
qdrant_client = QdrantClient(
    host="localhost",
    port=6335
)

# Load embedding model
model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
```

## Additional Resources

- The `src/database` directory contains comprehensive Neo4j and Qdrant managers
- The `src/graphrag_mcp_tool.py` provides a reference implementation for MCP integration
- See the [Database Setup Guide](../database_setup.md) for detailed database configuration instructions
- Refer to [Connection Testing](../testing/index.md) for troubleshooting connection issues
