"""
Query engine for hybrid Neo4j and Qdrant search
"""

import logging
from typing import List, Dict, Any, Optional, Union
import uuid

logger = logging.getLogger(__name__)

class QueryEngine:
    """Hybrid query engine for Neo4j and Qdrant databases"""
    
    def __init__(self, neo4j_manager, qdrant_manager, embedding_processor=None):
        """Initialize with database managers"""
        self.neo4j = neo4j_manager
        self.qdrant = qdrant_manager
        self.embedding_processor = embedding_processor
        
        # Verify connections
        self._verify_connections()
    
    def _verify_connections(self):
        """Verify database connections"""
        if not self.neo4j.driver:
            logger.warning("Neo4j connection not established, attempting to connect")
            self.neo4j.connect()
            
        if not self.qdrant.client:
            logger.warning("Qdrant connection not established, attempting to connect")
            self.qdrant.connect()
    
    def semantic_search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict[Any, Any]]:
        """Perform semantic search using Qdrant"""
        logger.info(f"Semantic search: '{query}' (limit: {limit}, category: {category})")
        
        # Set up filter if category is provided
        filter_conditions = None
        if category:
            filter_conditions = {'category': category}
            
        # Perform vector search
        try:
            if not self.embedding_processor:
                logger.error("No embedding processor available for semantic search")
                return []
                
            # Use Qdrant for vector search
            search_results = self.qdrant.search(
                query_text=query,
                limit=limit,
                filter_conditions=filter_conditions
            )
            
            # Enhance results with document information
            enhanced_results = []
            for result in search_results:
                # Get document information from Neo4j
                doc_info = self.neo4j.get_document_by_id(result.get('doc_id'))
                if doc_info:
                    result['document'] = doc_info
                    
                # Get chunk context if needed
                chunk_context = self.neo4j.get_chunk_context(result['id'], context_size=1)
                if chunk_context:
                    result['context'] = {
                        'previous': [c.get('text', '') for c in chunk_context.get('previous', [])],
                        'next': [c.get('text', '') for c in chunk_context.get('next', [])]
                    }
                
                enhanced_results.append(result)
            
            return enhanced_results
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
    
    def category_search(self, category: str, limit: int = 10) -> List[Dict[Any, Any]]:
        """Search for documents by category using Neo4j"""
        logger.info(f"Category search: '{category}' (limit: {limit})")
        
        try:
            # Use Neo4j for category search
            results = self.neo4j.search_by_category(category, limit)
            return results
        except Exception as e:
            logger.error(f"Error in category search: {str(e)}")
            return []
    
    def get_document_with_chunks(self, doc_id: str) -> Dict[Any, Any]:
        """Get document with all its chunks"""
        logger.info(f"Getting document with chunks: {doc_id}")
        
        try:
            # Get document from Neo4j
            document = self.neo4j.get_document_by_id(doc_id)
            if not document:
                logger.warning(f"Document not found: {doc_id}")
                return {}
            
            # Get chunks from Neo4j
            chunks = self.neo4j.get_document_chunks(doc_id)
            document['chunks'] = chunks
            
            return document
        except Exception as e:
            logger.error(f"Error getting document with chunks: {str(e)}")
            return {}
    
    def hybrid_search(self, query: str, limit: int = 5, category: Optional[str] = None, 
                       semantic_weight: float = 0.7) -> List[Dict[Any, Any]]:
        """
        Perform hybrid search combining semantic and graph-based search
        
        Args:
            query: Search query text
            limit: Maximum number of results
            category: Optional category filter
            semantic_weight: Weight of semantic search vs. graph-based ranking (0.0 to 1.0)
            
        Returns:
            List of search results with scores
        """
        logger.info(f"Hybrid search: '{query}' (limit: {limit}, category: {category}, weight: {semantic_weight})")
        
        try:
            # Step 1: Perform semantic search with higher limit
            semantic_limit = limit * 2  # Get more results for reranking
            semantic_results = self.semantic_search(query, semantic_limit, category)
            
            if not semantic_results:
                logger.warning("No semantic search results found")
                return []
            
            # Step 2: Get related documents for each semantic result
            result_map = {}  # Map to track unique documents
            
            for sem_result in semantic_results:
                doc_id = sem_result.get('doc_id')
                if doc_id:
                    # Add semantic result to map
                    result_map[sem_result['id']] = {
                        'id': sem_result['id'],
                        'doc_id': doc_id,
                        'text': sem_result['text'],
                        'semantic_score': sem_result['score'],
                        'graph_score': 0.0,
                        'final_score': sem_result['score'] * semantic_weight,
                        'document': sem_result.get('document', {}),
                        'context': sem_result.get('context', {})
                    }
                    
                    # Get related documents (graph connections)
                    related_docs = self.neo4j.get_related_documents(doc_id, limit=3)
                    
                    # For each related document, get a representative chunk
                    for rel_doc in related_docs:
                        rel_doc_id = rel_doc.get('id')
                        if rel_doc_id:
                            # Get first chunk of related document
                            rel_chunks = self.neo4j.get_document_chunks(rel_doc_id)
                            if rel_chunks and len(rel_chunks) > 0:
                                rel_chunk = rel_chunks[0]
                                rel_chunk_id = rel_chunk.get('id')
                                
                                # Calculate graph-based score (decreasing with distance)
                                graph_score = 0.5  # Related document score
                                
                                # Add to results if not already present or if better score
                                if rel_chunk_id not in result_map:
                                    # Combine scores
                                    final_score = (graph_score * (1 - semantic_weight))
                                    
                                    result_map[rel_chunk_id] = {
                                        'id': rel_chunk_id,
                                        'doc_id': rel_doc_id,
                                        'text': rel_chunk.get('text', ''),
                                        'semantic_score': 0.0,
                                        'graph_score': graph_score,
                                        'final_score': final_score,
                                        'document': rel_doc,
                                        'context': {}
                                    }
            
            # Step 3: Sort by final score and limit results
            results = list(result_map.values())
            results.sort(key=lambda x: x['final_score'], reverse=True)
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []
    
    def expand_context(self, chunk_id: str, context_size: int = 2) -> Dict[Any, Any]:
        """Expand context around a specific chunk"""
        logger.info(f"Expanding context for chunk: {chunk_id} (size: {context_size})")
        
        try:
            # Get chunk context from Neo4j
            context = self.neo4j.get_chunk_context(chunk_id, context_size)
            if not context:
                logger.warning(f"No context found for chunk: {chunk_id}")
                return {}
            
            # Get document info
            doc_id = None
            if context.get('center'):
                chunk = context['center']
                doc_id = self.neo4j.get_document_by_chunk_id(chunk_id)
                if doc_id:
                    doc_info = self.neo4j.get_document_by_id(doc_id)
                    if doc_info:
                        context['document'] = doc_info
            
            return context
        except Exception as e:
            logger.error(f"Error expanding context: {str(e)}")
            return {}
    
    def suggest_related(self, doc_id: str, limit: int = 5) -> List[Dict[Any, Any]]:
        """Suggest related documents based on category and graph connections"""
        logger.info(f"Suggesting related documents for: {doc_id} (limit: {limit})")
        
        try:
            # Get related documents from Neo4j
            related = self.neo4j.get_related_documents(doc_id, limit)
            return related
        except Exception as e:
            logger.error(f"Error suggesting related documents: {str(e)}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Get all available document categories"""
        logger.info("Getting all document categories")
        
        try:
            return self.neo4j.get_all_categories()
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[Any, Any]:
        """Get statistics from both databases"""
        logger.info("Getting database statistics")
        
        try:
            neo4j_stats = self.neo4j.get_statistics()
            qdrant_stats = self.qdrant.get_statistics()
            
            return {
                'neo4j': neo4j_stats,
                'qdrant': qdrant_stats
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {} 