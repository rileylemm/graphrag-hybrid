# Testing MCP Integration with GraphRAG

This guide provides instructions for testing your MCP integration with the GraphRAG system to ensure proper connectivity and functionality.

## Prerequisites

- GraphRAG system up and running
- Neo4j database populated with documents
- Qdrant database populated with vector embeddings
- MCP server with the DocumentationGPTTool implemented
- Python 3.8+ environment

## Connection Testing

First, verify that your MCP server can connect to both databases:

```python
import logging
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress Qdrant version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

def test_neo4j_connection():
    """Test connection to Neo4j with the verified port"""
    logger.info("Testing Neo4j connection...")
    
    
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "password"
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j connection successful' as message")
            logger.info(result.single()["message"])
            
            # Count nodes
            count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            logger.info(f"Neo4j database contains {count} nodes")
        driver.close()
        return True
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        return False

def test_qdrant_connection():
    """Test connection to Qdrant with the verified port"""
    logger.info("Testing Qdrant connection...")
    
    # Use the verified non-standard port
    try:
        client = QdrantClient(host="localhost", port=6333)
        # Check if Qdrant is running by making a simple API call
        status = client.get_collections()
        logger.info(f"Qdrant connection successful. Collections: {len(status.collections)}")
        
        # Check document_chunks collection
        if any(c.name == "document_chunks" for c in status.collections):
            collection_info = client.get_collection("document_chunks")
            logger.info(f"document_chunks collection info: {collection_info}")
            
            # Get vector count
            try:
                vectors_count = collection_info.vectors_count
                logger.info(f"Collection contains {vectors_count} vectors")
            except AttributeError:
                # Try alternative attribute names for different Qdrant versions
                if hasattr(collection_info, "vectors_count"):
                    logger.info(f"Collection contains {collection_info.vectors_count} vectors")
                elif hasattr(collection_info, "points_count"):
                    logger.info(f"Collection contains {collection_info.points_count} vectors")
                else:
                    logger.warning("Could not determine vector count - check Qdrant version compatibility")
                    
        return True
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")
        return False

def main():
    """Run all connection tests"""
    logger.info("Starting connection tests...")
    
    neo4j_success = test_neo4j_connection()
    qdrant_success = test_qdrant_connection()
    
    if neo4j_success and qdrant_success:
        logger.info("\n✅ All database connections successful!")
    else:
        logger.error("\n❌ Some connections failed. Please check the logs above.")

if __name__ == "__main__":
    main()
```

## Functional Testing

After verifying connections, test the actual functionality of your MCP tool implementation:

```python
from your_mcp_package import DocumentationGPTTool

def test_search_functionality():
    """Test the search functionality of the DocumentationGPTTool"""
    print("Testing search functionality...")
    
    # Initialize the tool
    doc_tool = DocumentationGPTTool()
    
    # Test with a simple query
    test_query = "database setup"
    print(f"Searching for: '{test_query}'")
    
    results = doc_tool.search_documentation(
        query=test_query,
        limit=3
    )
    
    # Print results
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Score: {result.get('score')}")
        print(f"Text snippet: {result.get('text')[:150]}...")
        doc_info = result.get('document', {})
        print(f"Document: {doc_info.get('title', 'Unknown')} ({doc_info.get('id', 'Unknown')})")
    
    # Clean up
    doc_tool.close()
    
    return len(results) > 0

if __name__ == "__main__":
    if test_search_functionality():
        print("\n✅ Search functionality working correctly!")
    else:
        print("\n❌ Search functionality test failed!")
```

## Integration Testing with MCP

Finally, test the integration with your MCP framework:

1. Start your MCP server with the DocumentationGPTTool registered
2. Send a test request to the MCP API endpoint:

```bash
curl -X POST http://localhost:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "documentation_search",
    "parameters": {
      "query": "How to set up Neo4j",
      "limit": 3
    }
  }'
```

Verify that you receive properly formatted results containing relevant documentation.

## Troubleshooting

If you encounter issues during testing:

1. **Connection Failures**: Verify port numbers in your configuration (Neo4j: 7687, Qdrant: 6333)
2. **Version Compatibility**: Ensure your Qdrant client version is compatible with your server
3. **Empty Results**: Check that your databases are properly populated with document data
4. **Poor Result Quality**: Adjust your embedding model or search parameters
5. **Errors in Response Format**: Update your result enrichment logic to match expected format

## Performance Metrics

Monitor these key metrics during testing:

- **Response Time**: Should be under 1 second for most queries
- **Result Relevance**: At least 70% of results should be relevant to the query
- **Memory Usage**: Keep below 500MB for the tool instance
- **Error Rate**: Less than 1% of requests should fail 