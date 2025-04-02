"""
Query utilities for the GraphRAG system.

This module provides functions for querying the hybrid Neo4j and Qdrant system.
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

from src.utils.neo4j_utils import Neo4jHelper
from src.utils.qdrant_utils import QdrantHelper
from src.config import EMBEDDING_MODEL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GraphRAGQuery:
    """
    Query utility for the hybrid GraphRAG system.
    """
    
    def __init__(
        self,
        neo4j_helper: Neo4jHelper,
        qdrant_helper: QdrantHelper,
        embedding_model: str = EMBEDDING_MODEL
    ):
        """
        Initialize the query utility.
        
        Args:
            neo4j_helper: Neo4j helper instance
            qdrant_helper: Qdrant helper instance
            embedding_model: Name of the embedding model to use
        """
        self.neo4j = neo4j_helper
        self.qdrant = qdrant_helper
        
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
    
    def semantic_search(self, query: str, limit: int = 5, filter_by: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search using Qdrant.
        
        Args:
            query: The search query
            limit: Maximum number of results
            filter_by: Optional filter criteria
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_vector = self.embedding_model.encode(query).tolist()
        
        # Search Qdrant
        results = self.qdrant.search_similar(
            query_vector=query_vector,
            limit=limit,
            filter_by=filter_by
        )
        
        # Process results
        processed_results = []
        for result in results:
            # Get the Neo4j chunk ID from the payload
            neo4j_chunk_id = result.payload.get('metadata', {}).get('chunk_id', '')
            
            processed_results.append({
                'qdrant_id': result.id,  # Store the Qdrant UUID
                'chunk_id': neo4j_chunk_id,  # Use the Neo4j chunk ID from metadata
                'text': result.payload.get('text', ''),
                'score': result.score,
                'doc_id': result.payload.get('metadata', {}).get('doc_id', ''),
                'title': result.payload.get('metadata', {}).get('title', ''),
                'category': result.payload.get('metadata', {}).get('category', ''),
                'file_path': result.payload.get('metadata', {}).get('file_path', '')
            })
        
        return processed_results
    
    def get_document_context(self, chunk_id: str, context_size: int = 2) -> List[Dict[str, Any]]:
        """
        Get surrounding context for a content chunk using graph relationships.
        
        Args:
            chunk_id: ID of the content chunk
            context_size: Number of chunks to retrieve in each direction
            
        Returns:
            List of content chunks in sequence
        """
        # Extract doc_id from chunk_id (format: chunk_doc_XXX_N)
        parts = chunk_id.split('_')
        if len(parts) >= 3:
            doc_id = '_'.join(parts[1:-1])
            sequence = int(parts[-1])
            
            # Get nearby chunks from the same document
            query = """
            MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Content)
            WHERE c.sequence >= $start_seq AND c.sequence <= $end_seq
            RETURN c.id AS id, c.text AS text, c.sequence AS sequence
            ORDER BY c.sequence
            """
            
            start_seq = max(0, sequence - context_size)
            end_seq = sequence + context_size
            
            with self.neo4j.driver.session() as session:
                result = session.run(
                    query, 
                    doc_id=doc_id, 
                    start_seq=start_seq, 
                    end_seq=end_seq
                )
                return [dict(record) for record in result]
        
        return []
    
    def get_related_documents(self, doc_id: str) -> Dict[str, Any]:
        """
        Get related documents and topics for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary with related documents and topics
        """
        # Get related documents
        related_docs = self.neo4j.get_related_documents(doc_id)
        
        # Get document topics
        topics = self.neo4j.get_document_topics(doc_id)
        
        return {
            'related_documents': related_docs,
            'topics': topics
        }
    
    def search_by_topic(self, topic_name: str) -> List[Dict[str, Any]]:
        """
        Find documents by topic.
        
        Args:
            topic_name: Topic name
            
        Returns:
            List of documents with the specified topic
        """
        return self.neo4j.get_documents_by_topic(topic_name)
    
    def hybrid_search(self, query: str, limit: int = 5, expand_context: bool = True) -> Dict[str, Any]:
        """
        Perform a hybrid search combining semantic and graph-based approaches.
        
        Args:
            query: The search query
            limit: Maximum number of direct results
            expand_context: Whether to expand results with context
            
        Returns:
            Dictionary with search results and related information
        """
        # First, get semantic search results
        semantic_results = self.semantic_search(query, limit=limit)
        
        if not semantic_results:
            return {'results': [], 'context': [], 'related': []}
        
        # Result containers
        expanded_results = []
        related_info = {}
        context_chunks = {}
        
        # Process each semantic result
        for result in semantic_results:
            chunk_id = result['chunk_id']
            doc_id = result['doc_id']
            
            # Add to expanded results
            expanded_results.append(result)
            
            # Get surrounding context if requested
            if expand_context and chunk_id:
                context = self.get_document_context(chunk_id)
                for chunk in context:
                    if chunk['id'] != chunk_id:  # Don't duplicate the main result
                        context_chunks[chunk['id']] = {
                            'chunk_id': chunk['id'],
                            'text': chunk['text'],
                            'sequence': chunk['sequence'],
                            'doc_id': doc_id,
                            'title': result['title'],
                            'category': result['category'],
                            'context_for': chunk_id
                        }
            
            # Get graph-related information
            if doc_id and doc_id not in related_info:
                related_info[doc_id] = self.get_related_documents(doc_id)
        
        # Combine results
        return {
            'results': expanded_results,
            'context': list(context_chunks.values()),
            'related': related_info
        }
    
    def category_search(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for documents by category.
        
        Args:
            category: Category to search for
            limit: Maximum number of results
            
        Returns:
            List of documents in the specified category
        """
        query = """
        MATCH (d:Document)
        WHERE d.category CONTAINS $category
        RETURN d.id AS id, d.title AS title, d.category AS category, d.path AS path
        LIMIT $limit
        """
        
        with self.neo4j.driver.session() as session:
            result = session.run(query, category=category, limit=limit)
            return [dict(record) for record in result] 