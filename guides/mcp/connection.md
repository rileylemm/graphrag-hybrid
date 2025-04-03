# GraphRAG Connection Setup

This guide explains how to establish connections to both Neo4j and Qdrant databases in your MCP implementation.

## Environment Configuration

First, set up your environment variables:

```python
# Neo4j Configuration
NEO4J_URI = "bolt://localhost:7687"  # Standard bolt port
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Qdrant Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333  # Standard HTTP port
QDRANT_GRPC_PORT = 6334  # gRPC port
QDRANT_COLLECTION = "document_chunks"
```

## Docker Configuration

The databases are configured in `docker-compose.yml`:

```yaml
services:
  neo4j:
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt

  qdrant:
    ports:
      - "6333:6333"  # HTTP
      - "6334:6334"  # gRPC
```

## Neo4j Connection

Use the official Neo4j Python driver:

```python
from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def verify_connection(self):
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"Connected to Neo4j. Found {count} nodes.")
                return True
        except Exception as e:
            print(f"Failed to connect to Neo4j: {str(e)}")
            return False
            
    def close(self):
        self.driver.close()
```

## Qdrant Connection

Use the Qdrant client with version compatibility handling:

```python
import warnings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

class QdrantConnection:
    def __init__(self, host, port):
        # Suppress version compatibility warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")
        self.client = QdrantClient(host=host, port=port)
        
    def verify_connection(self, collection_name):
        try:
            # Check collection info
            collection_info = self.client.get_collection(collection_name)
            
            # Handle different Qdrant client versions
            try:
                vectors_count = collection_info.vectors_count
            except AttributeError:
                try:
                    vectors_count = collection_info.points_count
                except AttributeError:
                    vectors_count = 0
                
            print(f"Connected to Qdrant. Collection '{collection_name}' has {vectors_count} vectors.")
            return True
        except Exception as e:
            print(f"Failed to connect to Qdrant: {str(e)}")
            return False
```

## Combined Database Manager

Create a manager class to handle both connections:

```python
class GraphRAGManager:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, 
                 qdrant_host, qdrant_port, collection_name):
        self.neo4j = Neo4jConnection(neo4j_uri, neo4j_user, neo4j_password)
        self.qdrant = QdrantConnection(qdrant_host, qdrant_port)
        self.collection_name = collection_name
        
    def verify_connections(self):
        neo4j_ok = self.neo4j.verify_connection()
        qdrant_ok = self.qdrant.verify_connection(self.collection_name)
        return neo4j_ok and qdrant_ok
        
    def close(self):
        self.neo4j.close()
```

## Usage Example

Here's how to use the connection manager:

```python
# Initialize the manager
manager = GraphRAGManager(
    neo4j_uri=NEO4J_URI,
    neo4j_user=NEO4J_USER,
    neo4j_password=NEO4J_PASSWORD,
    qdrant_host=QDRANT_HOST,
    qdrant_port=QDRANT_PORT,
    collection_name=QDRANT_COLLECTION
)

# Verify connections
if manager.verify_connections():
    print("Successfully connected to both databases")
else:
    print("Failed to connect to one or both databases")

# Clean up
manager.close()
```

## Health Checks

It's recommended to implement regular health checks:

```python
async def check_database_health():
    """Check the health of both databases."""
    try:
        # Check Neo4j
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
            print("Neo4j: Connected")
            
        # Check Qdrant
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        print(f"Qdrant: Connected (Collection: {QDRANT_COLLECTION})")
        
        return True
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return False
```

## Error Handling

Common connection errors and their solutions:

1. **Neo4j Connection Refused**
   - Check if Neo4j container is running
   - Verify port mapping in docker-compose.yml
   - Ensure credentials are correct

2. **Qdrant Connection Failed**
   - Check if Qdrant container is running
   - Verify port mapping in docker-compose.yml
   - Check collection exists

3. **Version Compatibility Warnings**
   - Use try/except blocks for different attribute names
   - Suppress warnings if needed using `warnings.filterwarnings()`
   - Consider pinning client version to match server

See [Error Handling](error_handling.md) for more detailed troubleshooting. 