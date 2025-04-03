# GraphRAG Database Connection Guide

This guide provides detailed instructions for establishing connections to the Neo4j graph database and Qdrant vector database used in the GraphRAG system.

## Verified Connection Parameters

Through extensive testing, we've identified the following connection parameters:

| Database | Service | Port | Authentication |
|----------|---------|------|---------------|
| Neo4j    | HTTP    | 7474 | neo4j/password |
| Neo4j    | Bolt    | 7687 | neo4j/password |
| Qdrant   | HTTP    | 6333 | None (default) |

> **Note**: Both databases are configured with their standard default ports. Neo4j uses 7474 for HTTP and 7687 for Bolt, while Qdrant uses 6333 for HTTP.

## Required Dependencies

Install the following Python packages to connect to the databases:

```bash
pip install neo4j==5.9.0 qdrant-client==1.6.0 sentence-transformers==2.2.2
```

## Neo4j Connection Setup

### Connection String Format

The Neo4j connection string follows this format:
```bolt://[hostname]:[port]
```

### Basic Connection Example

```python
from neo4j import GraphDatabase

# Connection parameters
neo4j_uri = "bolt://localhost:7688"  # Note the non-standard port
neo4j_user = "neo4j"
neo4j_password = "password"

# Establish connection
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# Test connection
def test_connection():
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS node_count")
        return result.single()["node_count"]

# Print node count
print(f"Connected to Neo4j database with {test_connection()} nodes")

# Close connection when done
driver.close()
```

### Connection with Error Handling

```python
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

def connect_to_neo4j(uri, user, password, max_retries=3):
    """Connect to Neo4j with retry logic and error handling."""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            
            # Verify connection
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
                
            print(f"✅ Successfully connected to Neo4j at {uri}")
            return driver
            
        except ServiceUnavailable as e:
            retry_count += 1
            wait_time = 2 ** retry_count  # Exponential backoff
            print(f"❌ Neo4j connection failed (attempt {retry_count}/{max_retries}): {e}")
            print(f"   Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            
        except AuthError as e:
            print(f"❌ Neo4j authentication failed: {e}")
            print("   Please check username and password.")
            break
            
        except Exception as e:
            print(f"❌ Unexpected error connecting to Neo4j: {e}")
            break
    
    if retry_count >= max_retries:
        print(f"❌ Failed to connect to Neo4j after {max_retries} attempts")
    
    return None
```

### Testing Multiple Ports

If you're unsure which port Neo4j is using, you can test multiple ports:

```python
def find_neo4j_port(host="localhost", ports=[7687, 7688, 7689]):
    """Try to connect to Neo4j on different ports."""
    for port in ports:
        uri = f"bolt://{host}:{port}"
        try:
            with GraphDatabase.driver(uri, auth=("neo4j", "password")) as driver:
                with driver.session() as session:
                    session.run("RETURN 1").single()
                    print(f"✅ Neo4j found on port {port}")
                    return port
        except Exception as e:
            print(f"❌ Neo4j not available on port {port}: {e}")
    
    print("❌ Could not connect to Neo4j on any of the specified ports")
    return None
```

## Qdrant Connection Setup

### Basic Connection

```python
from qdrant_client import QdrantClient

# Connection parameters
qdrant_host = "localhost"
qdrant_port = 6335  # Note the non-standard port
qdrant_collection = "document_chunks"

# Connect to Qdrant
client = QdrantClient(host=qdrant_host, port=qdrant_port)

# Test connection
def test_collection():
    try:
        collection_info = client.get_collection(qdrant_collection)
        
        # Handle different API versions
        vectors_count = None
        if hasattr(collection_info, 'vectors_count'):
            vectors_count = collection_info.vectors_count
        elif hasattr(collection_info, 'points_count'):
            vectors_count = collection_info.points_count
        
        return vectors_count
    except Exception as e:
        print(f"Error getting collection info: {e}")
        return None

# Print collection size
vector_count = test_collection()
if vector_count is not None:
    print(f"Connected to Qdrant collection '{qdrant_collection}' with {vector_count} vectors")
```

### Connection with Version Compatibility

Qdrant client versions may have different API methods. Here's how to handle different versions:

```python
import warnings
from qdrant_client import QdrantClient

# Suppress version compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

def connect_to_qdrant(host, port, collection_name, max_retries=3):
    """Connect to Qdrant with error handling and version compatibility."""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Connect to Qdrant
            client = QdrantClient(host=host, port=port)
            
            # Verify connection by checking collection
            collection_info = client.get_collection(collection_name)
            
            # Try to get vector count using different API versions
            vectors_count = None
            
            # Try approach for newer versions
            if hasattr(collection_info, 'vectors_count'):
                vectors_count = collection_info.vectors_count
            # Try approach for other versions
            elif hasattr(collection_info, 'points_count'):
                vectors_count = collection_info.points_count
            # Try to navigate the potentially nested structure
            else:
                try:
                    if hasattr(collection_info.config, 'params'):
                        if hasattr(collection_info.config.params, 'vectors'):
                            vectors_count = collection_info.config.params.vectors.size
                except:
                    pass
            
            if vectors_count is not None:
                print(f"✅ Connected to Qdrant collection '{collection_name}' with {vectors_count} vectors")
            else:
                print(f"✅ Connected to Qdrant collection '{collection_name}', but couldn't determine vector count")
                
            return client
            
        except ConnectionError as e:
            retry_count += 1
            wait_time = 2 ** retry_count  # Exponential backoff
            print(f"❌ Qdrant connection failed (attempt {retry_count}/{max_retries}): {e}")
            print(f"   Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"❌ Error connecting to Qdrant: {e}")
            break
    
    if retry_count >= max_retries:
        print(f"❌ Failed to connect to Qdrant after {max_retries} attempts")
    
    return None
```

### Testing Multiple Ports

Similar to Neo4j, you can test multiple ports for Qdrant:

```python
def find_qdrant_port(host="localhost", ports=[6333, 6334, 6335]):
    """Try to connect to Qdrant on different ports."""
    for port in ports:
        try:
            client = QdrantClient(host=host, port=port)
            collections = client.get_collections().collections
            print(f"✅ Qdrant found on port {port} with {len(collections)} collections")
            return port
        except Exception as e:
            print(f"❌ Qdrant not available on port {port}: {e}")
    
    print("❌ Could not connect to Qdrant on any of the specified ports")
    return None
```

## Setting Up the Embedding Model

To query the vector database effectively, you'll need to use the same embedding model that was used to create the vector embeddings:

```python
from sentence_transformers import SentenceTransformer

def load_embedding_model(model_name="all-MiniLM-L6-v2"):
    """Load the sentence transformer model for creating embeddings."""
    try:
        model = SentenceTransformer(model_name)
        print(f"✅ Loaded embedding model: {model_name}")
        return model
    except Exception as e:
        print(f"❌ Error loading embedding model: {e}")
        return None

# Load the model
model = load_embedding_model()

# Generate an embedding for a query
def generate_embedding(text, model):
    if model is None:
        return None
    
    try:
        embedding = model.encode(text)
        return embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None
```

## Complete Connection Manager Example

Here's a complete connection manager that handles connections to both databases:

```python
import os
import time
import warnings
from typing import Dict, List, Optional, Any, Union

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Suppress Qdrant version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

class GraphRAGConnectionManager:
    """Manager for connections to Neo4j and Qdrant databases."""
    
    def __init__(self):
        # Neo4j connection parameters
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.neo4j_driver = None
        
        # Qdrant connection parameters
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6335"))
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "document_chunks")
        self.qdrant_client = None
        
        # Embedding model
        self.model_name = "all-MiniLM-L6-v2"
        self.model = None
    
    def connect(self, max_retries=3):
        """Connect to both databases and load the embedding model."""
        success = True
        
        # Connect to Neo4j
        if not self._connect_neo4j(max_retries):
            success = False
        
        # Connect to Qdrant
        if not self._connect_qdrant(max_retries):
            success = False
        
        # Load embedding model
        if not self._load_model():
            success = False
        
        return success
    
    def _connect_neo4j(self, max_retries=3):
        """Connect to Neo4j with retry logic."""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    self.neo4j_uri, 
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                
                # Verify connection
                with self.neo4j_driver.session() as session:
                    result = session.run("MATCH (d:Document) RETURN count(d) AS count")
                    record = result.single()
                    print(f"✅ Connected to Neo4j with {record['count']} documents")
                
                return True
                
            except ServiceUnavailable as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"❌ Neo4j connection failed (attempt {retry_count}/{max_retries}): {e}")
                print(f"   Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except AuthError as e:
                print(f"❌ Neo4j authentication failed: {e}")
                print("   Please check username and password.")
                break
                
            except Exception as e:
                print(f"❌ Unexpected error connecting to Neo4j: {e}")
                break
        
        if retry_count >= max_retries:
            print(f"❌ Failed to connect to Neo4j after {max_retries} attempts")
        
        return False
    
    def _connect_qdrant(self, max_retries=3):
        """Connect to Qdrant with retry logic."""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.qdrant_client = QdrantClient(
                    host=self.qdrant_host, 
                    port=self.qdrant_port
                )
                
                # Verify connection
                collection_info = self.qdrant_client.get_collection(self.qdrant_collection)
                
                # Try to get vector count using different API versions
                vectors_count = None
                
                # Try approach for newer versions
                if hasattr(collection_info, 'vectors_count'):
                    vectors_count = collection_info.vectors_count
                # Try approach for other versions
                elif hasattr(collection_info, 'points_count'):
                    vectors_count = collection_info.points_count
                # Try to navigate the potentially nested structure
                else:
                    try:
                        if hasattr(collection_info.config, 'params'):
                            if hasattr(collection_info.config.params, 'vectors'):
                                vectors_count = collection_info.config.params.vectors.size
                    except:
                        pass
                
                if vectors_count is not None:
                    print(f"✅ Connected to Qdrant collection '{self.qdrant_collection}' with {vectors_count} vectors")
                else:
                    print(f"✅ Connected to Qdrant collection '{self.qdrant_collection}', but couldn't determine vector count")
                    
                return True
                
            except ConnectionError as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"❌ Qdrant connection failed (attempt {retry_count}/{max_retries}): {e}")
                print(f"   Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"❌ Error connecting to Qdrant: {e}")
                break
        
        if retry_count >= max_retries:
            print(f"❌ Failed to connect to Qdrant after {max_retries} attempts")
        
        return False
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Loaded embedding model: {self.model_name}")
            return True
        except Exception as e:
            print(f"❌ Error loading embedding model: {e}")
            return False
    
    def close(self):
        """Close all connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            print("✅ Neo4j connection closed")
        
        # Qdrant client doesn't require explicit closure
        
        print("✅ All connections closed")
```

## Usage Example

Here's how to use the connection manager:

```python
# Create the connection manager
manager = GraphRAGConnectionManager()

# Connect to databases
if manager.connect():
    print("All connections established successfully")
    
    # Use the connections...
    
    # Close connections when done
    manager.close()
else:
    print("Failed to establish all connections")
```

## Environment Variables

To simplify configuration, consider using environment variables for connection parameters:

```bash
# .env file
NEO4J_URI=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=localhost
QDRANT_PORT=6335
QDRANT_COLLECTION=document_chunks
```

To load these environment variables in Python:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get connection parameters
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
qdrant_host = os.getenv("QDRANT_HOST")
qdrant_port = int(os.getenv("QDRANT_PORT"))
qdrant_collection = os.getenv("QDRANT_COLLECTION")
```

## Troubleshooting Connection Issues

### Neo4j Connection Issues

1. **Connection Refused**: 
   - Verify Neo4j is running
   - Check the correct port (7688 for this setup)
   - Try connecting directly via the Neo4j Browser at http://localhost:7474

2. **Authentication Failed**:
   - Verify username and password
   - Check if authentication is enabled in Neo4j configuration

3. **Timeout**:
   - Check network connectivity
   - Ensure Neo4j isn't overloaded with long-running queries

### Qdrant Connection Issues

1. **Connection Refused**:
   - Verify Qdrant is running
   - Check the correct port (6335 for this setup)
   - Try connecting to the Qdrant API directly: http://localhost:6335/dashboard

2. **Collection Not Found**:
   - Verify the collection name is correct ("document_chunks")
   - Check if the collection exists in the Qdrant dashboard

3. **Version Compatibility**:
   - Warnings about deprecated methods are normal between client versions
   - Use the version-handling code shown in the examples

## Additional Resources

- [Neo4j Driver Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Qdrant Client Documentation](https://qdrant.tech/documentation/quick-start/)
- [Sentence-Transformers Documentation](https://www.sbert.net/)
- [Database Connection Testing Report](../test_db_connection/index.md) 