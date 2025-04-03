# GraphRAG Query Implementation

This guide explains how to implement querying functionality in your MCP tools to interact with the GraphRAG system.

## Query Flow

The query process involves several steps:

1. Generate embeddings for the query text
2. Search Qdrant for similar vectors
3. Retrieve related documents from Neo4j
4. Combine and rank results

## Implementation

### 1. Query Class

```python
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

class GraphRAGQuery:
    def __init__(self, manager, model_name="all-MiniLM-L6-v2"):
        self.manager = manager
        self.embedding_model = SentenceTransformer(model_name)
        
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for query text."""
        return self.embedding_model.encode(text)
        
    async def search(self, query: str, limit: int = 5) -> List[Dict[Any, Any]]:
        """Perform hybrid search using both Qdrant and Neo4j."""
        # Generate query embedding
        query_vector = self.generate_embedding(query)
        
        # Search Qdrant
        qdrant_results = self.search_qdrant(query_vector, limit)
        
        # Get related documents from Neo4j
        neo4j_results = self.expand_context(qdrant_results)
        
        # Combine and rank results
        final_results = self.rank_results(query, qdrant_results, neo4j_results)
        
        return final_results
        
    def search_qdrant(self, query_vector: np.ndarray, limit: int) -> List[Dict[Any, Any]]:
        """Search Qdrant for similar vectors."""
        try:
            results = self.manager.qdrant.client.search(
                collection_name=self.manager.collection_name,
                query_vector=query_vector.tolist(),
                limit=limit
            )
            return [
                {
                    'doc_id': hit.payload.get('doc_id'),
                    'score': hit.score,
                    'category': hit.payload.get('category')
                }
                for hit in results
            ]
        except Exception as e:
            print(f"Qdrant search error: {str(e)}")
            return []
            
    def expand_context(self, qdrant_results: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
        """Get related documents from Neo4j."""
        doc_ids = [result['doc_id'] for result in qdrant_results]
        
        try:
            with self.manager.neo4j.driver.session() as session:
                query = """
                MATCH (d:Document)
                WHERE d.doc_id IN $doc_ids
                OPTIONAL MATCH (d)-[r]-(related)
                RETURN d.doc_id as doc_id,
                       d.title as title,
                       d.content as content,
                       collect(DISTINCT {
                           type: type(r),
                           doc_id: related.doc_id,
                           title: related.title
                       }) as related_docs
                """
                result = session.run(query, doc_ids=doc_ids)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Neo4j query error: {str(e)}")
            return []
            
    def rank_results(self, query: str, 
                    qdrant_results: List[Dict[Any, Any]], 
                    neo4j_results: List[Dict[Any, Any]]) -> List[Dict[Any, Any]]:
        """Combine and rank results from both databases."""
        # Create a mapping of doc_ids to Neo4j results
        neo4j_map = {doc['doc_id']: doc for doc in neo4j_results}
        
        # Combine results
        ranked_results = []
        for qdrant_hit in qdrant_results:
            doc_id = qdrant_hit['doc_id']
            if doc_id in neo4j_map:
                neo4j_doc = neo4j_map[doc_id]
                ranked_results.append({
                    'doc_id': doc_id,
                    'title': neo4j_doc['title'],
                    'content': neo4j_doc['content'],
                    'score': qdrant_hit['score'],
                    'category': qdrant_hit['category'],
                    'related_docs': neo4j_doc['related_docs']
                })
                
        return ranked_results
```

### 2. MCP Tool Implementation

Here's how to implement the GraphRAG functionality as an MCP tool:

```python
from typing import Optional, Dict, Any
from mcp.tools import BaseTool

class GraphRAGTool(BaseTool):
    name = "GraphRAG"
    description = "Search through documents using hybrid Neo4j and Qdrant search"
    
    def __init__(self):
        super().__init__()
        self.manager = GraphRAGManager(
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD,
            qdrant_host=QDRANT_HOST,
            qdrant_port=QDRANT_PORT,
            collection_name=QDRANT_COLLECTION
        )
        self.query_engine = GraphRAGQuery(self.manager)
        
    async def execute(self, query: str, 
                     limit: Optional[int] = 5,
                     category: Optional[str] = None) -> Dict[str, Any]:
        """Execute a search query."""
        try:
            results = await self.query_engine.search(query, limit)
            
            # Filter by category if specified
            if category:
                results = [r for r in results if r['category'] == category]
                
            return {
                'status': 'success',
                'results': results,
                'count': len(results)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def cleanup(self):
        """Clean up database connections."""
        self.manager.close()
```

## Usage Example

Here's how to use the GraphRAG tool in your MCP environment:

```python
# Initialize the tool
graphrag_tool = GraphRAGTool()

# Execute a search
results = await graphrag_tool.execute(
    query="How to configure Neo4j authentication?",
    limit=5,
    category="setup"
)

# Process results
if results['status'] == 'success':
    for doc in results['results']:
        print(f"Document: {doc['title']}")
        print(f"Score: {doc['score']}")
        print(f"Related docs: {len(doc['related_docs'])}")
        print("---")
else:
    print(f"Error: {results['error']}")

# Clean up
graphrag_tool.cleanup()
```

## Query Parameters

- `query` (str): The search query text
- `limit` (int, optional): Maximum number of results (default: 5)
- `category` (str, optional): Filter results by category

## Response Format

The search results are returned in the following format:

```python
{
    'status': 'success',
    'results': [
        {
            'doc_id': str,
            'title': str,
            'content': str,
            'score': float,
            'category': str,
            'related_docs': [
                {
                    'type': str,
                    'doc_id': str,
                    'title': str
                }
            ]
        }
    ],
    'count': int
}
```

## Error Handling

See [Error Handling](error_handling.md) for detailed information about handling query errors and edge cases. 