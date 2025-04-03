# Neo4j and Qdrant Database Setup Guide

This guide provides instructions for setting up and configuring Neo4j (graph database) and Qdrant (vector database) for use with the GraphRAG MCP server.

## Table of Contents

- [Neo4j and Qdrant Database Setup Guide](#neo4j-and-qdrant-database-setup-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Docker Compose Setup](#docker-compose-setup)
  - [Neo4j Setup](#neo4j-setup)
    - [Manual Installation](#manual-installation)
    - [Configuration](#configuration)
    - [Database Schema Design](#database-schema-design)
    - [Basic Operations](#basic-operations)
  - [Qdrant Setup](#qdrant-setup)
    - [Manual Installation](#manual-installation-1)
    - [Configuration](#configuration-1)
    - [Collection Setup](#collection-setup)
    - [Basic Operations](#basic-operations-1)
  - [Security Considerations](#security-considerations)
  - [Testing the Setup](#testing-the-setup)
  - [Troubleshooting](#troubleshooting)

## Overview

This project uses a hybrid approach combining:
- **Neo4j**: A graph database for storing structured relationships between entities
- **Qdrant**: A vector database for semantic similarity search

Both databases should be set up as separate services that the MCP server will connect to.

## Docker Compose Setup

The easiest way to set up both databases for development is using Docker Compose. Create a `docker-compose.yml` file:

```yaml
version: '3'

services:
  neo4j:
    image: neo4j:5.13.0
    container_name: graphrag_neo4j
    ports:
      - "7474:7474"  
      - "7687:7687"  
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_apoc_export_file_enabled=true
      - NEO4J_apoc_import_file_enabled=true
      - NEO4J_apoc_import_file_use__neo4j__config=true
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    networks:
      - graphrag_network

  qdrant:
    image: qdrant/qdrant:v1.5.1
    container_name: graphrag_qdrant
    ports:
      - "6335:6333"  # HTTP (mapped to non-standard port)
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT_ALLOW_CORS=true
    networks:
      - graphrag_network

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
  qdrant_data:

networks:
  graphrag_network:
    driver: bridge
```

To start the services:

```bash
docker-compose up -d
```

To stop the services:

```bash
docker-compose down
```

## Neo4j Setup

### Manual Installation

If you prefer not to use Docker, you can install Neo4j directly:

1. Download Neo4j Community Edition from the [official website](https://neo4j.com/download/)
2. Install according to your operating system's instructions
3. Start the Neo4j server and set an initial password
4. Configure the server to use ports 7474 (HTTP) and 7687 (Bolt)

### Configuration

Key configuration parameters for Neo4j:

- **Connection URL**: `bolt://localhost:7687`
- **Default credentials**: username `neo4j`, password `password` (change in production)
- **Web interface**: Available at http://localhost:7474 after startup

### Database Schema Design

For this GraphRAG project, we'll use the following schema:

```cypher
// Node labels
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Content) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// Indexes for faster lookups
CREATE INDEX IF NOT EXISTS FOR (c:Content) ON (c.text);
CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.title);
CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.category);
CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.path);
```

### Basic Operations

Connect to Neo4j using the Cypher shell or web interface and try these commands:

```cypher
// Create a document node
CREATE (d:Document {id: "doc1", title: "GraphRAG Architecture", path: "/docs/architecture.md"})

// Create content chunks for the document
CREATE (c1:Content {id: "chunk1", text: "This document describes the GraphRAG architecture combining Neo4j and Qdrant."})
CREATE (c2:Content {id: "chunk2", text: "The system uses a hybrid approach with vector similarity and graph relationships."})

// Create relationships
MATCH (d:Document {id: "doc1"})
MATCH (c1:Content {id: "chunk1"})
MATCH (c2:Content {id: "chunk2"})
CREATE (d)-[:CONTAINS]->(c1)
CREATE (d)-[:CONTAINS]->(c2)
CREATE (c1)-[:NEXT]->(c2)

// Query related content
MATCH (c:Content {id: "chunk1"})-[r:NEXT]->(related)
RETURN c.text AS source, related.text AS related_content
```

## Qdrant Setup

### Manual Installation

If not using Docker:

1. Download the latest Qdrant release from [GitHub](https://github.com/qdrant/qdrant/releases)
2. Extract and run according to your OS instructions
3. Configure the server to use ports 6333 for HTTP and 6334 for gRPC
4. Verify installation by accessing the API endpoint

### Configuration

Key configuration for Qdrant:

- **HTTP URL**: http://localhost:6333
- **gRPC URL**: http://localhost:6334
- **Web dashboard**: Available at http://localhost:6335/dashboard

### Collection Setup

Initialize a collection for document chunks with appropriate settings:

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models
import warnings

# Suppress version compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

# Connect to Qdrant
client = QdrantClient("localhost", port=6333)

# Create a collection for document embeddings
# Using 384 dimensions for all-MiniLM-L6-v2 embeddings
client.create_collection(
    collection_name="document_chunks",
    vectors_config=models.VectorParams(
        size=384,  # Dimension size for the embedding model
        distance=models.Distance.COSINE
    ),
)

# Create a payload index for efficient filtering
client.create_payload_index(
    collection_name="document_chunks",
    field_name="metadata.doc_id",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

# Create payload index for chunk sequence
client.create_payload_index(
    collection_name="document_chunks",
    field_name="metadata.sequence",
    field_schema=models.PayloadSchemaType.INTEGER,
)
```

### Basic Operations

Here are common operations you might need:

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import warnings

# Suppress version compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

# Initialize clients
qdrant = QdrantClient(host="localhost", port=6333)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Insert a document
text = "This document describes the GraphRAG architecture."
embedding = model.encode(text).tolist()
qdrant.upsert(
    collection_name="document_chunks",
    points=[
        {
            "id": "chunk1",
            "vector": embedding,
            "payload": {
                "text": text,
                "metadata": {
                    "doc_id": "doc1",
                    "chunk_id": "chunk1",
                    "sequence": 1
                }
            }
        }
    ]
)

# Search for similar documents
query = "Tell me about the GraphRAG architecture"
query_vector = model.encode(query).tolist()

# Handle different Qdrant versions with compatible search approach
try:
    # Newer Qdrant versions
    search_result = qdrant.search(
        collection_name="document_chunks",
        query_vector=query_vector,
        limit=5
    )
except Exception as e:
    # Fallback for compatibility issues
    print(f"Using fallback search due to: {str(e)}")
    search_result = qdrant.search(
        collection_name="document_chunks",
        query_vector=query_vector,
        limit=5
    )

for result in search_result:
    print(f"ID: {result.id}, Score: {result.score}")
    print(f"Text: {result.payload['text']}")
    print("---")
```

## Security Considerations

For production environments:

1. **Neo4j**:
   - Change default credentials
   - Enable SSL for bolt connections
   - Set up role-based access control
   - Consider network isolation

2. **Qdrant**:
   - Set up API keys for authentication
   - Use HTTPS in production
   - Consider network isolation
   - Implement proper backup strategies

## Testing the Setup

Verify your setup is working with these checks:

1. **Neo4j**:
   - Access the web interface at http://localhost:7474
   - Run a simple Cypher query: `MATCH (n) RETURN n LIMIT 5`
   - Verify connection via Bolt protocol: `bolt://localhost:7687`

2. **Qdrant**:
   - Check service status: http://localhost:6335/dashboard
   - Use the collections API: http://localhost:6335/collections

3. **Connectivity from MCP**:
   - Test Neo4j connection using the python driver
   - Test Qdrant connection using the python client
   - Verify both connections using the test script in `test_db_connection/test_connections.py`

## Troubleshooting

Common issues and solutions:

- **Neo4j won't start**: Check logs at `./neo4j_logs` when using Docker
- **Qdrant connection refused**: Verify ports are properly exposed (6333 for HTTP, 6334 for gRPC)
- **Authentication errors**: Ensure credentials match in both config and code
- **Slow Neo4j queries**: Check your index usage with `EXPLAIN` and `PROFILE`
- **Vector dimension mismatch**: Ensure embedding dimensions match your Qdrant collection (384 for all-MiniLM-L6-v2)
- **Version compatibility issues**: Use the warning suppression shown in the examples or update client libraries to match server versions 