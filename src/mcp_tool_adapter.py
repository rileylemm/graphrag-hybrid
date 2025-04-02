"""
MCP Tool Adapter for GraphRAG

This module provides an adapter to make the GraphRAG tool compatible
with the MCP (Model Control Panel) system.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, Callable

# Import GraphRAG components
from .graphrag_mcp_tool import GraphRAGMCPTool

logger = logging.getLogger(__name__)

class DocumentationGPTTool:
    """
    MCP-compatible adapter for the GraphRAG document retrieval system
    
    This class implements the standard MCP tool interface required by the
    MCP system, adapting the GraphRAG tool to work with the MCP protocol.
    """
    
    # Define tool metadata for MCP registration
    tool_name = "documentation_search"
    description = "Search the documentation for relevant information"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Documentation GPT Tool
        
        Args:
            config_path: Optional path to a configuration file
        """
        self.config_path = config_path
        self.graphrag_tool = None
        
        # Initialize the tool
        self._initialize()
    
    def _initialize(self):
        """Initialize the GraphRAG tool"""
        try:
            logger.info("Initializing Documentation GPT Tool")
            self.graphrag_tool = GraphRAGMCPTool(self.config_path)
            logger.info("Documentation GPT Tool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Documentation GPT Tool: {str(e)}")
            raise
    
    def search_docs(self, query: str, limit: int = 5, category: Optional[str] = None,
                   search_type: str = "hybrid") -> Dict[str, Any]:
        """
        Search the documentation for relevant information
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            category: Optional category filter
            search_type: Type of search to perform
            
        Returns:
            Dict containing search results
        """
        try:
            logger.info(f"Documentation search: '{query}'")
            
            if not self.graphrag_tool:
                self._initialize()
                
            return self.graphrag_tool.search(
                query=query,
                limit=limit,
                category=category,
                search_type=search_type
            )
        except Exception as e:
            logger.error(f"Error in documentation search: {str(e)}")
            return {
                "error": str(e),
                "results": []
            }
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Get a specific document by ID
        
        Args:
            doc_id: The document ID
            
        Returns:
            Dict containing the document
        """
        try:
            if not self.graphrag_tool:
                self._initialize()
                
            return self.graphrag_tool.get_document(doc_id)
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return {
                "error": str(e),
                "document": None
            }
    
    def get_categories(self) -> Dict[str, Any]:
        """
        Get all document categories
        
        Returns:
            Dict containing list of categories
        """
        try:
            if not self.graphrag_tool:
                self._initialize()
                
            return self.graphrag_tool.get_categories()
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return {
                "error": str(e),
                "categories": []
            }
    
    # MCP tool interface methods
    
    @classmethod
    def get_tool_spec(cls) -> Dict[str, Any]:
        """
        Get the tool specification for MCP registration
        
        Returns:
            Dict with tool specification
        """
        return {
            "name": cls.tool_name,
            "description": cls.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search to perform (hybrid, semantic, category)",
                        "default": "hybrid",
                        "enum": ["hybrid", "semantic", "category"]
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to perform (search, get_document, get_categories)",
                        "default": "search",
                        "enum": ["search", "get_document", "get_categories"]
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID for get_document action"
                    }
                },
                "required": ["action"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        },
                        "description": "Search results"
                    },
                    "document": {
                        "type": "object",
                        "description": "Document data"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of categories"
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if any"
                    }
                }
            }
        }
    
    def call(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool interface method - call the tool with input data
        
        Args:
            input_data: Dict containing the input parameters
            
        Returns:
            Dict containing the tool response
        """
        try:
            logger.info(f"Documentation tool called with action: {input_data.get('action', 'search')}")
            
            # Extract parameters
            action = input_data.get('action', 'search')
            
            # Call appropriate method based on action
            if action == 'search':
                return self.search_docs(
                    query=input_data.get('query', ''),
                    limit=input_data.get('limit', 5),
                    category=input_data.get('category'),
                    search_type=input_data.get('search_type', 'hybrid')
                )
            elif action == 'get_document':
                return self.get_document(input_data.get('doc_id', ''))
            elif action == 'get_categories':
                return self.get_categories()
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "available_actions": ["search", "get_document", "get_categories"]
                }
        except Exception as e:
            logger.error(f"Error calling Documentation tool: {str(e)}")
            return {
                "error": str(e)
            }
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.graphrag_tool:
                self.graphrag_tool.close()
                self.graphrag_tool = None
            logger.info("Documentation tool resources released")
        except Exception as e:
            logger.error(f"Error cleaning up Documentation tool: {str(e)}")
    
    def __del__(self):
        """Cleanup when the object is garbage collected"""
        self.cleanup()

# MCP registration function
def register_mcp_tool(register_function: Callable):
    """
    Register the Documentation GPT Tool with the MCP system
    
    Args:
        register_function: MCP function to register the tool
    """
    try:
        logger.info("Registering Documentation GPT Tool with MCP")
        
        # Get tool specification
        tool_spec = DocumentationGPTTool.get_tool_spec()
        
        # Register the tool
        register_function(
            tool_spec['name'],
            tool_spec['description'],
            DocumentationGPTTool,
            input_schema=tool_spec['input_schema'],
            output_schema=tool_spec['output_schema']
        )
        
        logger.info("Documentation GPT Tool registered successfully")
        return True
    except Exception as e:
        logger.error(f"Error registering Documentation GPT Tool: {str(e)}")
        return False 