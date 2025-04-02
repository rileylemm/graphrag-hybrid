"""
GraphRAG MCP Tool Implementation

This module implements a Model Control Panel (MCP) tool for querying 
the hybrid Neo4j and Qdrant document retrieval system.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
import os
from dataclasses import dataclass
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import sentence_transformers
import warnings

# Import GraphRAG components
from .config import Config
from .database.neo4j_manager import Neo4jManager
from .database.qdrant_manager import QdrantManager
from .processors.embedding_processor import EmbeddingProcessor
from .query_engine import QueryEngine

# Suppress Qdrant version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results."""
    content: str
    document_id: str
    chunk_id: str
    score: float
    category: str
    title: str

class GraphRAGMCPTool:
    """
    GraphRAG Model Control Panel (MCP) Tool
    
    This class implements the MCP Tool interface for the GraphRAG system,
    allowing LLM-based tools to query the document database and retrieve
    relevant information based on user queries.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the GraphRAG MCP Tool
        
        Args:
            config_path: Optional path to a configuration file
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Initialize components
        self.neo4j_manager = None
        self.qdrant_manager = None
        self.embedding_processor = None
        self.query_engine = None
        
        # Initialize the system
        self._initialize_system()
        
    def _initialize_system(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing GraphRAG MCP Tool")
            
            # Load environment variables
            self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
            self.neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
            self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
            self.collection = os.getenv("QDRANT_COLLECTION", "document_chunks")
            
            # Initialize connections
            self._init_connections()
            
            # Load embedding model
            self.model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create embedding processor
            self.embedding_processor = EmbeddingProcessor(self.config)
            self.embedding_processor.load_model()
            
            # Create database managers
            self.neo4j_manager = Neo4jManager(self.config)
            self.neo4j_manager.connect()
            
            self.qdrant_manager = QdrantManager(self.config, self.embedding_processor)
            self.qdrant_manager.connect()
            
            # Create query engine
            self.query_engine = QueryEngine(
                self.neo4j_manager,
                self.qdrant_manager,
                self.embedding_processor
            )
            
            logger.info("GraphRAG MCP Tool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing GraphRAG MCP Tool: {str(e)}")
            raise
            
    def _init_connections(self):
        """Initialize database connections with error handling."""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_pass)
            )
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
        except Exception as e:
            raise ConnectionError(f"Failed to initialize database connections: {str(e)}")
            
    def search(self, query: str, limit: int = 5, category: Optional[str] = None, 
               search_type: str = "hybrid") -> Dict[str, Any]:
        """
        Search for documents based on a query
        
        Args:
            query: The search query text
            limit: Maximum number of results to return (default: 5)
            category: Optional category to filter results
            search_type: Type of search to perform ('semantic', 'hybrid', or 'category')
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            logger.info(f"MCP Search: '{query}' ({search_type}, limit: {limit}, category: {category})")
            
            results = []
            if search_type == "semantic":
                # Semantic search only (vector similarity)
                results = self.query_engine.semantic_search(query, limit, category)
            elif search_type == "category":
                # Category search only
                if not category:
                    raise ValueError("Category search requires a category parameter")
                results = self.query_engine.category_search(category, limit)
            else:
                # Default to hybrid search
                results = self.query_engine.hybrid_search(query, limit, category)
                
            # Format the results for MCP
            formatted_results = self._format_search_results(results, query)
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error in MCP search: {str(e)}")
            return {
                "error": str(e),
                "results": [],
                "metadata": {
                    "query": query,
                    "result_count": 0,
                    "search_type": search_type
                }
            }
            
    def _format_search_results(self, results: List[Dict[Any, Any]], query: str) -> Dict[str, Any]:
        """Format search results for MCP output"""
        formatted_results = []
        
        for i, result in enumerate(results):
            # Extract the most important data from each result
            formatted_result = {
                "id": result.get('id', f"result_{i}"),
                "text": result.get('text', ''),
                "score": result.get('score', result.get('semantic_score', 0)),
                "document": {
                    "id": result.get('doc_id', ''),
                    "title": result.get('document', {}).get('title', 'Untitled Document'),
                    "category": result.get('document', {}).get('category', 'Uncategorized')
                }
            }
            
            # Add context if available
            if 'context' in result and result['context']:
                context_text = []
                if 'previous' in result['context'] and result['context']['previous']:
                    context_text.extend(result['context']['previous'])
                context_text.append(result.get('text', ''))
                if 'next' in result['context'] and result['context']['next']:
                    context_text.extend(result['context']['next'])
                
                formatted_result['context'] = "\n\n".join(context_text)
            
            formatted_results.append(formatted_result)
        
        # Prepare the final response
        response = {
            "results": formatted_results,
            "metadata": {
                "query": query,
                "result_count": len(formatted_results),
                "search_type": "hybrid" if any('semantic_score' in r for r in results) else "category"
            }
        }
        
        return response
        
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Get a complete document by ID
        
        Args:
            doc_id: The document ID to retrieve
            
        Returns:
            Dict containing the document and its chunks
        """
        try:
            logger.info(f"MCP Get Document: {doc_id}")
            
            document = self.query_engine.get_document_with_chunks(doc_id)
            
            if not document:
                return {
                    "error": f"Document not found: {doc_id}",
                    "document": None
                }
            
            # Format document for MCP
            formatted_doc = {
                "id": document.get('id', ''),
                "title": document.get('title', 'Untitled Document'),
                "category": document.get('category', 'Uncategorized'),
                "chunks": []
            }
            
            # Add chunks
            if 'chunks' in document and document['chunks']:
                chunk_texts = []
                for chunk in document['chunks']:
                    chunk_texts.append(chunk.get('text', ''))
                
                # Add full text and chunks
                formatted_doc['full_text'] = "\n\n".join(chunk_texts)
                formatted_doc['chunks'] = [
                    {
                        "id": chunk.get('id', ''),
                        "text": chunk.get('text', ''),
                        "position": chunk.get('position', 0)
                    }
                    for chunk in document['chunks']
                ]
            
            return {
                "document": formatted_doc,
                "related": self.query_engine.suggest_related(doc_id)
            }
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return {
                "error": str(e),
                "document": None
            }
            
    def expand_context(self, chunk_id: str, context_size: int = 2) -> Dict[str, Any]:
        """
        Expand context around a specific chunk
        
        Args:
            chunk_id: The chunk ID to get context for
            context_size: Number of chunks before and after to include
            
        Returns:
            Dict containing the expanded context
        """
        try:
            logger.info(f"MCP Expand Context: {chunk_id} (size: {context_size})")
            
            context = self.query_engine.expand_context(chunk_id, context_size)
            
            if not context:
                return {
                    "error": f"Chunk not found: {chunk_id}",
                    "context": None
                }
            
            # Format context for MCP
            formatted_context = {
                "chunk": {
                    "id": context.get('center', {}).get('id', ''),
                    "text": context.get('center', {}).get('text', '')
                },
                "previous": [],
                "next": [],
                "document": context.get('document', {})
            }
            
            # Add previous and next chunks
            if 'previous' in context:
                formatted_context['previous'] = [
                    {
                        "id": chunk.get('id', ''),
                        "text": chunk.get('text', ''),
                        "position": chunk.get('position', 0)
                    }
                    for chunk in context['previous']
                ]
            
            if 'next' in context:
                formatted_context['next'] = [
                    {
                        "id": chunk.get('id', ''),
                        "text": chunk.get('text', ''),
                        "position": chunk.get('position', 0)
                    }
                    for chunk in context['next']
                ]
            
            # Add full context text
            context_text = []
            if formatted_context['previous']:
                for prev in formatted_context['previous']:
                    context_text.append(prev['text'])
            
            context_text.append(formatted_context['chunk']['text'])
            
            if formatted_context['next']:
                for next_chunk in formatted_context['next']:
                    context_text.append(next_chunk['text'])
            
            formatted_context['full_text'] = "\n\n".join(context_text)
            
            return {
                "context": formatted_context
            }
        except Exception as e:
            logger.error(f"Error expanding context: {str(e)}")
            return {
                "error": str(e),
                "context": None
            }
    
    def get_categories(self) -> Dict[str, Any]:
        """
        Get all document categories
        
        Returns:
            Dict containing list of categories
        """
        try:
            logger.info("MCP Get Categories")
            
            categories = self.query_engine.get_all_categories()
            
            return {
                "categories": categories,
                "count": len(categories)
            }
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return {
                "error": str(e),
                "categories": []
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dict containing system statistics
        """
        try:
            logger.info("MCP Get Statistics")
            
            stats = self.query_engine.get_statistics()
            
            # Format statistics for MCP
            formatted_stats = {
                "neo4j": {
                    "document_count": stats.get('neo4j', {}).get('document_count', 0),
                    "chunk_count": stats.get('neo4j', {}).get('chunk_count', 0),
                    "category_count": stats.get('neo4j', {}).get('category_count', 0)
                },
                "qdrant": {
                    "vector_count": stats.get('qdrant', {}).get('vector_count', 0),
                    "document_count": stats.get('qdrant', {}).get('estimated_document_count', 0)
                },
                "total": {
                    "document_count": stats.get('neo4j', {}).get('document_count', 0),
                    "chunk_count": stats.get('neo4j', {}).get('chunk_count', 0)
                }
            }
            
            return formatted_stats
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                "error": str(e),
                "neo4j": {},
                "qdrant": {},
                "total": {}
            }
    
    def close(self):
        """Close all connections and free resources"""
        try:
            logger.info("Closing GraphRAG MCP Tool connections")
            
            if self.neo4j_manager:
                self.neo4j_manager.close()
            
            if self.qdrant_manager:
                self.qdrant_manager.close()
            
            if self.embedding_processor:
                self.embedding_processor.unload_model()
            
            logger.info("GraphRAG MCP Tool connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {str(e)}")

    # MCP Tool standard method implementations
    def handle_request(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request
        
        Args:
            action: The action to perform (search, get_document, etc.)
            params: Parameters for the action
            
        Returns:
            Dict containing the action result
        """
        try:
            logger.info(f"MCP Request: {action}")
            
            if action == "search":
                return self.search(
                    query=params.get('query', ''),
                    limit=params.get('limit', 5),
                    category=params.get('category'),
                    search_type=params.get('search_type', 'hybrid')
                )
            elif action == "get_document":
                return self.get_document(params.get('doc_id', ''))
            elif action == "expand_context":
                return self.expand_context(
                    chunk_id=params.get('chunk_id', ''),
                    context_size=params.get('context_size', 2)
                )
            elif action == "get_categories":
                return self.get_categories()
            elif action == "get_statistics":
                return self.get_statistics()
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "available_actions": [
                        "search", "get_document", "expand_context", 
                        "get_categories", "get_statistics"
                    ]
                }
        except Exception as e:
            logger.error(f"Error handling MCP request: {str(e)}")
            return {
                "error": str(e),
                "action": action
            }
    
    def __del__(self):
        """Cleanup when the object is garbage collected"""
        self.close() 