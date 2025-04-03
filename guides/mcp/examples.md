# GraphRAG Examples

This guide provides practical examples of using the GraphRAG system in various scenarios.

## Basic Search Example

```python
from graphrag import GraphRAGTool

async def basic_search():
    # Initialize the tool
    tool = GraphRAGTool()
    
    try:
        # Execute a simple search
        results = await tool.execute(
            query="How to configure Neo4j authentication?",
            limit=5
        )
        
        # Process results
        if results['status'] == 'success':
            for doc in results['results']:
                print(f"Title: {doc['title']}")
                print(f"Score: {doc['score']:.4f}")
                print(f"Content: {doc['content'][:200]}...")
                print("---")
    finally:
        tool.cleanup()
```

## Category-Filtered Search

```python
async def category_search():
    tool = GraphRAGTool()
    
    try:
        # Search within a specific category
        results = await tool.execute(
            query="How to set up replication?",
            category="deployment",
            limit=3
        )
        
        if results['status'] == 'success':
            print(f"Found {results['count']} results:")
            for doc in results['results']:
                print(f"Category: {doc['category']}")
                print(f"Title: {doc['title']}")
                print("---")
    finally:
        tool.cleanup()
```

## Related Documents Search

```python
async def related_docs_search():
    tool = GraphRAGTool()
    
    try:
        # Search with related documents
        results = await tool.execute(
            query="Neo4j backup strategies",
            limit=2
        )
        
        if results['status'] == 'success':
            for doc in results['results']:
                print(f"Main Document: {doc['title']}")
                print("\nRelated Documents:")
                for related in doc['related_docs']:
                    print(f"- {related['title']} ({related['type']})")
                print("---")
    finally:
        tool.cleanup()
```

## Error Handling Example

```python
from graphrag import GraphRAGTool, ErrorLogger

async def robust_search():
    tool = GraphRAGTool()
    logger = ErrorLogger()
    
    try:
        # Attempt search with retry
        for attempt in range(3):
            try:
                results = await tool.execute(
                    query="Database optimization techniques"
                )
                if results['status'] == 'success':
                    return results
            except Exception as e:
                logger.log_error(e, {
                    'attempt': attempt + 1,
                    'operation': 'search'
                })
                if attempt < 2:
                    print(f"Retrying... (attempt {attempt + 2}/3)")
                    await asyncio.sleep(1)
                else:
                    print("All attempts failed")
                    return None
    finally:
        tool.cleanup()
```

## Health Check Example

```python
from graphrag import GraphRAGTool, HealthCheck

async def system_health_check():
    tool = GraphRAGTool()
    health_checker = HealthCheck(tool.manager)
    
    try:
        # Check system health
        status = await health_checker.check_health()
        
        print("System Health Status:")
        print(f"Timestamp: {status['timestamp']}")
        
        # Neo4j status
        print("\nNeo4j:")
        print(f"Status: {status['neo4j']['status']}")
        if 'message' in status['neo4j']:
            print(f"Message: {status['neo4j']['message']}")
        elif 'error' in status['neo4j']:
            print(f"Error: {status['neo4j']['error']}")
            
        # Qdrant status
        print("\nQdrant:")
        print(f"Status: {status['qdrant']['status']}")
        if status['qdrant']['status'] == 'healthy':
            print(f"Vectors: {status['qdrant']['vectors_count']}")
        elif 'error' in status['qdrant']:
            print(f"Error: {status['qdrant']['error']}")
    finally:
        tool.cleanup()
```

## Batch Processing Example

```python
from graphrag import GraphRAGTool
from typing import List

async def batch_search(queries: List[str]):
    tool = GraphRAGTool()
    
    try:
        results = []
        for query in queries:
            # Execute search for each query
            response = await tool.execute(query=query)
            if response['status'] == 'success':
                results.append({
                    'query': query,
                    'results': response['results']
                })
            else:
                print(f"Failed query: {query}")
                print(f"Error: {response.get('error')}")
                
        return results
    finally:
        tool.cleanup()

# Usage example
queries = [
    "Neo4j backup strategies",
    "Qdrant optimization techniques",
    "Database security best practices"
]

results = await batch_search(queries)
for item in results:
    print(f"\nQuery: {item['query']}")
    print(f"Found {len(item['results'])} results")
```

## Custom Ranking Example

```python
from graphrag import GraphRAGTool
from typing import List, Dict, Any

class CustomRankedSearch:
    def __init__(self):
        self.tool = GraphRAGTool()
        
    def rank_results(self, results: List[Dict[Any, Any]], 
                    weights: Dict[str, float]) -> List[Dict[Any, Any]]:
        """Custom ranking function."""
        for result in results:
            # Calculate weighted score
            score = result['score'] * weights.get('similarity', 1.0)
            
            # Adjust score based on related documents
            related_count = len(result['related_docs'])
            score += related_count * weights.get('relations', 0.1)
            
            # Adjust score based on category
            if result['category'] == weights.get('preferred_category'):
                score *= weights.get('category_boost', 1.2)
                
            result['adjusted_score'] = score
            
        # Sort by adjusted score
        return sorted(results, key=lambda x: x['adjusted_score'], reverse=True)
        
    async def search(self, query: str, weights: Dict[str, float]):
        try:
            # Execute basic search
            response = await self.tool.execute(query=query, limit=10)
            
            if response['status'] == 'success':
                # Apply custom ranking
                ranked_results = self.rank_results(
                    response['results'],
                    weights
                )
                return {
                    'status': 'success',
                    'results': ranked_results[:5]  # Return top 5
                }
            return response
        finally:
            self.tool.cleanup()

# Usage example
weights = {
    'similarity': 1.0,      # Base similarity score weight
    'relations': 0.1,       # Weight for related documents
    'category_boost': 1.2,  # Boost for preferred category
    'preferred_category': 'setup'
}

searcher = CustomRankedSearch()
results = await searcher.search(
    "Database configuration",
    weights
)
```

## Integration with MCP Server

```python
from mcp.tools import BaseTool
from graphrag import GraphRAGTool

class GraphRAGMCPTool(BaseTool):
    name = "GraphRAG"
    description = "Search through documentation using GraphRAG"
    
    def __init__(self):
        super().__init__()
        self.tool = GraphRAGTool()
        
    async def execute(self, query: str, **kwargs):
        try:
            # Extract parameters
            limit = kwargs.get('limit', 5)
            category = kwargs.get('category')
            
            # Execute search
            results = await self.tool.execute(
                query=query,
                limit=limit,
                category=category
            )
            
            # Format response for MCP
            if results['status'] == 'success':
                return {
                    'success': True,
                    'data': {
                        'results': results['results'],
                        'count': results['count']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': results.get('error', 'Unknown error')
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.tool.cleanup()
            
    def cleanup(self):
        """Clean up resources when the tool is unloaded."""
        if hasattr(self, 'tool'):
            self.tool.cleanup()
```

## Running the Examples

To run these examples:

1. Ensure both Neo4j and Qdrant are running
2. Install required packages:
   ```bash
   pip install neo4j qdrant-client sentence-transformers
   ```
3. Set up environment variables or update connection parameters
4. Run the examples:
   ```python
   import asyncio
   
   async def main():
       # Basic search
       await basic_search()
       
       # Category search
       await category_search()
       
       # Health check
       await system_health_check()
       
   if __name__ == "__main__":
       asyncio.run(main())
   ```

See [Connection Setup](connection.md) for detailed configuration instructions. 