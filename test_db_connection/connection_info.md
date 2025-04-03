# Database Connection Information

This document summarizes the connection parameters and database content for the GraphRAG system.

## Connection Parameters

### Neo4j

- **HTTP Port**: 7474 (Browser interface)
- **Bolt Port**: 7687 (Application connections)
- **Authentication**: Username: `neo4j`, Password: `password`
- **Connection URI**: `bolt://localhost:7687`
- **Browser Access**: Open http://localhost:7474 in your web browser

### Qdrant

- **HTTP Port**: 6333
- **Collection Name**: `document_chunks`
- **Authentication**: None (default)
- **Connection URL**: `http://localhost:6333`
- **Dashboard**: Open http://localhost:6333/dashboard in your web browser

## Database Content

### Neo4j Content

- **Total Documents**: 162
- **Total Chunks**: 20,112
- **Relationship Types**:
  - `HAS_CHUNK`: 20,112 relationships (connects documents to their chunks)
  - `RELATED_TO`: 1,310 relationships (connects related documents)

### Qdrant Content

- **Collection**: `document_chunks`
- **Vector Count**: 20,112
- **Vector Dimension**: 384
- **Distance Metric**: Cosine
- **Indexed Fields**:
  - `doc_id`: Keyword type (20,112 points)
  - `category`: Keyword type (20,112 points)

## Alignment Status

✅ **Perfect Alignment Confirmed**: All 162 document IDs present in Neo4j have corresponding vectors in Qdrant, and all document IDs in Qdrant exist in Neo4j.

## Search Functionality

Semantic search is working correctly, with proper alignment between Neo4j documents and Qdrant vectors. A test query for "how to connect to Neo4j" returned relevant results from the Troubleshooting Guide and Neo4j Implementation Guide.

## Verification Commands

To verify the database connections:

```bash
# Run the connection test script
python test_db_connection/test_connections.py

# Run the detailed database checker
python check_databases.py
``` 