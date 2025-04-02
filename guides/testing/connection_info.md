# Database Connection Information

## Neo4j Connection Details

- **Username**: neo4j
- **Password**: password
- **HTTP Port**: 7474 (Browser interface)
- **Bolt Port**: 7687 (Application connection)
- **Database**: neo4j (default)

To access the Neo4j Browser:
- Open http://localhost:7474 in your web browser
- Log in with neo4j/password

## Qdrant Connection Details

- **Host**: localhost
- **HTTP Port**: 6333 (REST API)
- **gRPC Port**: 6334
- **Collection Name**: document_chunks

## Environment Variables

Add these to your `.env` file:

```
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=document_chunks
```

## Connection Testing

The `test_connections.py` script will verify that both databases are accessible and working correctly. If you encounter any issues, refer to the troubleshooting section in the main documentation.

## Verified Connection Information

Our connection test script has confirmed the following connection details:

### Neo4j Database
- **HTTP Port**: 7474 (Browser interface)
- **Bolt Port**: 7687 (Application connection)
- **Authentication**: neo4j/password
- **Status**: Connected successfully ✅
- **Database Contents**: 
  - 162 Document nodes
  - 2785 Content nodes
  - 3652 Total nodes

### Qdrant Vector Database
- **HTTP Port**: 6333 (REST API)
- **Collection**: document_chunks
- **Vector Count**: 2785 vectors
- **Vector Dimension**: 384
- **Status**: Connected successfully ✅

## Connection Configuration for MCP

Add the following to your MCP server's `.env` file:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

## Implementation Note

Be aware that your Qdrant client version (1.13.3) is newer than your Qdrant server version (1.5.1), which may cause some compatibility issues with certain API features. The test successfully connected and performed a basic search, but you might need to adjust some code if using advanced features.

## Next Steps

1. Update your MCP server configuration with these verified connection details
2. Test basic query functionality
3. Implement error handling for version compatibility issues 