# GraphRAG Model Context Protocol Integration Guide

This guide provides detailed instructions for developing Model Context Protocol (MCP) components capable of querying the hybrid Neo4j and Qdrant database system. The integration supports powerful document retrieval with both semantic search capabilities and graph-based context expansion.

> **Note**: MCP (Model Context Protocol) is a framework for building tools that integrate with large language models (LLMs) to provide structured access to external data sources.

## System Architecture Overview

The GraphRAG system combines:

1. **Neo4j Graph Database**: Stores document relationships, categories, and metadata 
2. **Qdrant Vector Database**: Stores document chunk embeddings for semantic search

This hybrid approach enables:
- Semantic similarity search (finding content based on meaning)
- Graph-based context expansion (finding related documents)
- Filtered searches based on document categories or other metadata

## Connection Parameters

### Verified Database Endpoints

| Database | Service | Port | Authentication |
|----------|---------|------|---------------|
| Neo4j    | HTTP    | 7474 | neo4j/password |
| Neo4j    | Bolt    | 7687 | neo4j/password |
| Qdrant   | HTTP    | 6333 | None (default) |

### Environment Variables

Use these environment variables in your MCP server configuration:

```
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687  
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=document_chunks
```

## MCP Tool Implementation

### DocumentationGPTTool Class

Below is a sample implementation of a Model Context Protocol tool that can query the GraphRAG system:

```python
import os
from typing import Dict, List, Optional, Any, Union
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

class DocumentationGPTTool:
    """MCP Tool for querying the GraphRAG documentation system."""
    
    def __init__(self):
        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.neo4j_driver = None
        
        # Qdrant connection
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "document_chunks")
        self.qdrant_client = None
        
        # Embedding model
        self.model_name = "all-MiniLM-L6-v2"
        self.model = None
        
        # Initialize connections
        self._connect()
    
    def _connect(self):
        """Establish connections to Neo4j and Qdrant."""
        # Connect to Neo4j
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            with self.neo4j_driver.session() as session:
                result = session.run("MATCH (d:Document) RETURN count(d) AS count")
                record = result.single()
                print(f"Connected to Neo4j with {record['count']} documents")
        except Exception as e:
            print(f"Neo4j connection error: {e}")
        
        # Connect to Qdrant
        try:
            # Handle potential version compatibility issues
            try:
                self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
                collection_info = self.qdrant_client.get_collection(self.qdrant_collection)
                
                # Check for vectors count based on client version
                vectors_count = 0
                if hasattr(collection_info, 'vectors_count'):
                    vectors_count = collection_info.vectors_count
                elif hasattr(collection_info, 'points_count'):
                    vectors_count = collection_info.points_count
                else:
                    # Try to navigate the config structure based on observed variations
                    try:
                        if hasattr(collection_info.config, 'params'):
                            if hasattr(collection_info.config.params, 'vectors'):
                                vectors_count = collection_info.config.params.vectors.size
                    except:
                        pass
                
                print(f"Connected to Qdrant collection '{self.qdrant_collection}' with {vectors_count} vectors")
            except Exception as e:
                print(f"Qdrant connection warning: {e}")
                # Fallback for older versions if needed
        except Exception as e:
            print(f"Qdrant connection error: {e}")
        
        # Load the embedding model
        try:
            self.model = SentenceTransformer(self.model_name)
            print(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
    
    def search_documentation(self, query: str, limit: int = 5, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for documentation using semantic search and optionally expand with graph context.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            category: Optional category filter
            
        Returns:
            Dictionary with search results and related documents
        """
        results = {
            "query": query,
            "chunks": [],
            "related_documents": []
        }
        
        # Generate embedding for query
        if self.model is None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception as e:
                results["error"] = f"Failed to load embedding model: {e}"
                return results
        
        query_embedding = self.model.encode(query)
        
        # Search Qdrant
        try:
            # Handle version compatibility issues with the search API
            try:
                # Newer versions use query_vector
                search_result = self.qdrant_client.search(
                    collection_name=self.qdrant_collection,
                    query_vector=query_embedding.tolist(),
                    limit=limit
                )
            except TypeError:
                # Fall back to older versions using vector parameter
                search_result = self.qdrant_client.search(
                    collection_name=self.qdrant_collection,
                    vector=query_embedding.tolist(),
                    limit=limit
                )
                
            # Add search results to response
            for result in search_result:
                # Extract ID and score
                chunk_id = result.id
                score = result.score
                
                # Get text content from payload
                text = ""
                if hasattr(result, 'payload') and 'text' in result.payload:
                    text = result.payload['text']
                
                results["chunks"].append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "score": score
                })
        except Exception as e:
            results["error"] = f"Qdrant search error: {e}"
        
        # Expand with related documents from Neo4j
        if self.neo4j_driver and len(results["chunks"]) > 0:
            try:
                with self.neo4j_driver.session() as session:
                    # Build a query to find documents containing these chunks
                    # and their related documents
                    chunk_ids = [chunk["chunk_id"] for chunk in results["chunks"]]
                    
                    cypher_query = """
                    MATCH (c:Chunk) 
                    WHERE c.id IN $chunk_ids
                    MATCH (c)-[:PART_OF]->(d:Document)
                    OPTIONAL MATCH (d)-[:RELATED_TO]->(related:Document)
                    WITH DISTINCT d, related
                    RETURN d.id as doc_id, d.title as title, 
                           collect(DISTINCT {doc_id: related.id, title: related.title}) as related_docs
                    """
                    
                    if category:
                        cypher_query = """
                        MATCH (c:Chunk) 
                        WHERE c.id IN $chunk_ids
                        MATCH (c)-[:PART_OF]->(d:Document)-[:HAS_CATEGORY]->(cat:Category {name: $category})
                        OPTIONAL MATCH (d)-[:RELATED_TO]->(related:Document)
                        WITH DISTINCT d, related
                        RETURN d.id as doc_id, d.title as title, 
                               collect(DISTINCT {doc_id: related.id, title: related.title}) as related_docs
                        """
                    
                    result = session.run(cypher_query, chunk_ids=chunk_ids, category=category)
                    
                    # Process results
                    related_docs = set()
                    for record in result:
                        doc_id = record["doc_id"]
                        title = record["title"]
                        
                        # Add the document itself
                        results["related_documents"].append({
                            "doc_id": doc_id,
                            "title": title
                        })
                        
                        # Add related documents
                        for related in record["related_docs"]:
                            if related["doc_id"] not in related_docs:
                                related_docs.add(related["doc_id"])
                                results["related_documents"].append({
                                    "doc_id": related["doc_id"],
                                    "title": related["title"]
                                })
                                
                                # Limit the number of related documents
                                if len(related_docs) >= limit:
                                    break
                        
            except Exception as e:
                results["error"] = f"Neo4j query error: {e}"
        
        return results
```

### MCP Configuration

Register the tool in your Model Context Protocol server's tool configuration:

```python
from documentation_tool import DocumentationGPTTool

def register_documentation_tool():
    return {
        "name": "documentation_search",
        "description": "Search the documentation for information about the GraphRAG system",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant documentation"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category to filter results (e.g., 'setup', 'api', 'usage')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)"
                }
            },
            "required": ["query"]
        },
        "implementation": DocumentationGPTTool().search_documentation
    }
```

## Error Handling Considerations

When implementing GraphRAG in Model Context Protocol, include the following error handling strategies:

1. **Database Connection Failures**: 
   - Implement connection retry logic with exponential backoff
   - Provide meaningful error messages for connection issues

2. **Version Compatibility Issues**:
   - Handle Qdrant API differences (as shown in the sample code)
   - Provide fallbacks for different Neo4j APOC versions

3. **Query Timeout Handling**:
   - Set appropriate timeouts for both Neo4j and Qdrant queries
   - Implement circuit breakers for degraded performance

4. **Content Not Found**:
   - Return helpful messages when searches yield no results
   - Suggest related topics based on partial matches

## Testing Your Implementation

You can test your MCP tool implementation using the provided query tester:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test script
python scripts/testing/query_tester.py
```

## Advanced Integration Techniques

### Hybrid Search Implementation

For more sophisticated search capabilities, implement hybrid search by combining vector similarity scores with graph-based relevance:

```python
def hybrid_search(self, query: str, limit: int = 5, category: Optional[str] = None, 
                  expand_context: bool = True) -> Dict[str, Any]:
    """
    Perform hybrid search using both vector similarity and graph context.
    
    Args:
        query: Search query
        limit: Maximum results
        category: Optional category filter
        expand_context: Whether to expand results with graph context
        
    Returns:
        Combined search results
    """
    # Get vector search results
    vector_results = self.search_documentation(query, limit=limit*2, category=category)
    
    # If we don't want expanded context, return vector results
    if not expand_context:
        return vector_results
    
    # Extract document IDs from vector results
    doc_ids = [doc["doc_id"] for doc in vector_results.get("related_documents", [])]
    
    # Expand with graph context
    try:
        with self.neo4j_driver.session() as session:
            cypher_query = """
            MATCH (d:Document)
            WHERE d.id IN $doc_ids
            OPTIONAL MATCH (d)-[:RELATED_TO*1..2]->(related:Document)
            WITH related, d
            WHERE related IS NOT NULL AND related.id NOT IN $doc_ids
            RETURN DISTINCT related.id as doc_id, related.title as title,
                   count(*) as relevance_score
            ORDER BY relevance_score DESC
            LIMIT $limit
            """
            
            result = session.run(cypher_query, doc_ids=doc_ids, limit=limit)
            
            # Add expanded results
            for record in result:
                vector_results["related_documents"].append({
                    "doc_id": record["doc_id"],
                    "title": record["title"],
                    "graph_score": record["relevance_score"]
                })
    except Exception as e:
        vector_results["error"] = f"Graph expansion error: {e}"
    
    return vector_results
```

## Troubleshooting

### Common Issues and Solutions

1. **Connection Refused**:
   - Verify the correct ports: Neo4j on 7687 (Bolt), Qdrant on 6333
   - Check if the respective services are running

2. **Authentication Failed**:
   - Confirm Neo4j credentials (default: neo4j/password)
   - Ensure environment variables are correctly set

3. **Qdrant Version Compatibility**:
   - Client warnings about deprecated methods are expected
   - Use version-aware code as shown in the example

4. **Empty Search Results**:
   - Verify the Qdrant collection name (default: document_chunks)
   - Check if the embedding model matches the one used for indexing

## Resources

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Qdrant Python Client Documentation](https://qdrant.tech/documentation/quick-start/)
- [Sentence-Transformers Documentation](https://www.sbert.net/)

For detailed testing reports and connection information, see [Database Connection Testing](../test_db_connection/index.md).
