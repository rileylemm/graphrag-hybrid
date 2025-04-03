# GraphRAG Error Handling

This guide covers common errors you might encounter when integrating with the GraphRAG system and how to handle them effectively.

## Connection Errors

### Neo4j Connection Issues

1. **Connection Refused**
```python
from neo4j.exceptions import ServiceUnavailable

try:
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n)")
except ServiceUnavailable as e:
    if "Connection refused" in str(e):
        print("Neo4j is not running or wrong port")
    elif "unauthorized" in str(e).lower():
        print("Invalid credentials")
    else:
        print(f"Neo4j connection error: {str(e)}")
```

2. **Authentication Failed**
```python
from neo4j.exceptions import AuthError

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
except AuthError:
    print("Invalid Neo4j credentials")
```

### Qdrant Connection Issues

1. **Connection Timeout**
```python
from qdrant_client.http.exceptions import UnexpectedResponse

try:
    client = QdrantClient(host=host, port=port)
    client.get_collection(collection_name)
except ConnectionError:
    print("Qdrant is not running or wrong port")
except UnexpectedResponse as e:
    if "404" in str(e):
        print(f"Collection '{collection_name}' not found")
    else:
        print(f"Qdrant error: {str(e)}")
```

2. **Collection Not Found**
```python
try:
    collection_info = client.get_collection(collection_name)
except UnexpectedResponse as e:
    if "404" in str(e):
        print(f"Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
```

## Query Errors

### Embedding Generation

1. **Model Loading Error**
```python
from sentence_transformers import SentenceTransformer

try:
    model = SentenceTransformer(model_name)
except OSError as e:
    if "not found" in str(e):
        print(f"Model '{model_name}' not found. Downloading...")
        # Implement model download logic
    else:
        print(f"Error loading model: {str(e)}")
```

2. **Input Text Error**
```python
def safe_encode(text: str) -> np.ndarray:
    try:
        if not isinstance(text, str):
            text = str(text)
        if not text.strip():
            raise ValueError("Empty input text")
        return model.encode(text)
    except Exception as e:
        print(f"Embedding generation error: {str(e)}")
        return None
```

### Qdrant Search

1. **Vector Size Mismatch**
```python
def safe_search(query_vector: np.ndarray) -> List[Dict[Any, Any]]:
    try:
        collection_info = client.get_collection(collection_name)
        vector_size = collection_info.config.params.vectors.size
        
        if len(query_vector) != vector_size:
            raise ValueError(
                f"Query vector size {len(query_vector)} does not match "
                f"collection vector size {vector_size}"
            )
            
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector.tolist(),
            limit=limit
        )
    except Exception as e:
        print(f"Qdrant search error: {str(e)}")
        return []
```

2. **Version Compatibility**
```python
def get_vectors_count(collection_info) -> int:
    """Handle different Qdrant client versions."""
    try:
        return collection_info.vectors_count
    except AttributeError:
        try:
            return collection_info.points_count
        except AttributeError:
            return 0
```

### Neo4j Queries

1. **Cypher Syntax Error**
```python
from neo4j.exceptions import CypherSyntaxError

def safe_query(session, query: str, params: Dict) -> List[Dict]:
    try:
        result = session.run(query, params)
        return [dict(record) for record in result]
    except CypherSyntaxError as e:
        print(f"Invalid Cypher query: {str(e)}")
        return []
    except Exception as e:
        print(f"Neo4j query error: {str(e)}")
        return []
```

2. **Missing Properties**
```python
def safe_get_property(node: Dict, prop: str, default: Any = None) -> Any:
    """Safely get node property with default value."""
    try:
        return node.get(prop, default)
    except Exception:
        return default
```

## Error Recovery

### Connection Recovery

```python
class ConnectionManager:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    async def with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(self.retry_delay)
```

### Graceful Degradation

```python
class GraphRAGQuery:
    async def fallback_search(self, query: str) -> List[Dict[Any, Any]]:
        """Fallback to Neo4j-only search if Qdrant fails."""
        try:
            with self.manager.neo4j.driver.session() as session:
                # Fallback to text-based search in Neo4j
                result = session.run("""
                    MATCH (d:Document)
                    WHERE d.content CONTAINS $query
                    RETURN d.doc_id as doc_id,
                           d.title as title,
                           d.content as content
                    LIMIT 5
                """, query=query)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Fallback search failed: {str(e)}")
            return []
```

## Monitoring and Logging

### Error Logging

```python
import logging
from datetime import datetime

class ErrorLogger:
    def __init__(self, log_file: str = "graphrag_errors.log"):
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("GraphRAG")
        
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context information."""
        error_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        self.logger.error(error_info)
```

### Health Checks

```python
class HealthCheck:
    def __init__(self, manager):
        self.manager = manager
        
    async def check_health(self) -> Dict[str, Any]:
        """Check health of all components."""
        status = {
            'neo4j': {'status': 'unknown'},
            'qdrant': {'status': 'unknown'},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check Neo4j
        try:
            with self.manager.neo4j.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
                status['neo4j'] = {
                    'status': 'healthy',
                    'message': 'Connected successfully'
                }
        except Exception as e:
            status['neo4j'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            
        # Check Qdrant
        try:
            collection_info = self.manager.qdrant.client.get_collection(
                self.manager.collection_name
            )
            status['qdrant'] = {
                'status': 'healthy',
                'vectors_count': get_vectors_count(collection_info)
            }
        except Exception as e:
            status['qdrant'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            
        return status
```

## Best Practices

1. Always implement proper error handling for all database operations
2. Use retry logic for transient failures
3. Implement graceful degradation when services are unavailable
4. Log errors with sufficient context for debugging
5. Regularly check system health
6. Handle version compatibility issues
7. Validate input data before processing
8. Clean up resources properly
9. Monitor system performance
10. Keep error messages user-friendly 