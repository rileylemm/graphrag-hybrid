#!/usr/bin/env python3
"""
Query demonstration script for the hybrid Neo4j/Qdrant database system.

This script demonstrates how to query the hybrid database system using
different query types (semantic, category, or hybrid) and displays the results.
"""

import os
import sys
import logging
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database.neo4j_manager import Neo4jManager
from src.database.qdrant_manager import QdrantManager
from src.processors.embedding_processor import EmbeddingProcessor
from src.query_engine import QueryEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_argparse():
    """Set up command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Demonstrate querying the hybrid Neo4j/Qdrant system'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='.env',
        help='Path to configuration file (.env or YAML)'
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Query string'
    )
    
    parser.add_argument(
        '--type', '-t',
        type=str,
        default='hybrid',
        choices=['semantic', 'category', 'hybrid'],
        help='Query type: semantic, category, or hybrid (default: hybrid)'
    )
    
    parser.add_argument(
        '--category', '-cat',
        type=str,
        help='Filter results by category'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=5,
        help='Maximum number of results to return (default: 5)'
    )
    
    parser.add_argument(
        '--document', '-d',
        type=str,
        help='Get document by ID instead of searching'
    )
    
    parser.add_argument(
        '--expand', '-e',
        type=str,
        help='Expand context around a chunk ID'
    )
    
    parser.add_argument(
        '--context-size', '-cs',
        type=int,
        default=2,
        help='Context size for expansion (default: 2)'
    )
    
    parser.add_argument(
        '--list-categories', '-lc',
        action='store_true',
        default=False,
        help='List all available categories'
    )
    
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        default=False,
        help='Show system statistics'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Write results to file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=False,
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def format_result_for_display(result: Dict[str, Any], index: int = None) -> str:
    """Format a search result for display"""
    output = []
    
    if index is not None:
        output.append(f"Result #{index+1}")
    
    # Add document info
    if 'document' in result and result['document']:
        doc = result['document']
        output.append(f"Document: {doc.get('title', 'Untitled')} ({doc.get('id', 'No ID')})")
        output.append(f"Category: {doc.get('category', 'Uncategorized')}")
    
    # Add chunk info
    output.append(f"Chunk ID: {result.get('id', 'No ID')}")
    output.append(f"Score: {result.get('score', result.get('semantic_score', 0)):.4f}")
    
    # Add content
    output.append("\nContent:")
    output.append("-" * 50)
    output.append(result.get('text', 'No content'))
    output.append("-" * 50)
    
    # Add context if available
    if 'context' in result and result['context']:
        output.append("\nContext:")
        output.append("-" * 50)
        if isinstance(result['context'], str):
            output.append(result['context'])
        elif isinstance(result['context'], dict):
            if 'previous' in result['context'] and result['context']['previous']:
                output.append("Previous:")
                for prev in result['context']['previous']:
                    if isinstance(prev, str):
                        output.append(prev)
                    else:
                        output.append(prev.get('text', ''))
                    
            if 'next' in result['context'] and result['context']['next']:
                output.append("Next:")
                for next_chunk in result['context']['next']:
                    if isinstance(next_chunk, str):
                        output.append(next_chunk)
                    else:
                        output.append(next_chunk.get('text', ''))
        output.append("-" * 50)
    
    return "\n".join(output)

def main():
    """Main execution function"""
    args = setup_argparse()
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Load configuration
    try:
        config = Config(args.config)
        logger.info(f"Configuration loaded from {args.config}")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return 1
    
    # Initialize components
    try:
        # Create embedding processor
        embedding_processor = EmbeddingProcessor(config)
        if args.type in ['semantic', 'hybrid'] or args.query:
            embedding_processor.load_model()
        
        # Create database managers
        neo4j_manager = Neo4jManager(config)
        neo4j_manager.connect()
        
        qdrant_manager = QdrantManager(config, embedding_processor)
        qdrant_manager.connect()
        
        # Create query engine
        query_engine = QueryEngine(
            neo4j_manager,
            qdrant_manager,
            embedding_processor
        )
        
        logger.info("Query engine initialized")
    except Exception as e:
        logger.error(f"Error initializing query engine: {str(e)}")
        return 1
    
    results = None
    output_text = []
    
    try:
        # Check what action to perform
        if args.stats:
            # Show statistics
            stats = query_engine.get_statistics()
            output_text.append("System Statistics:")
            output_text.append("-" * 50)
            
            neo4j_stats = stats.get('neo4j', {})
            output_text.append(f"Neo4j:")
            output_text.append(f"  Document count: {neo4j_stats.get('document_count', 0)}")
            output_text.append(f"  Chunk count: {neo4j_stats.get('chunk_count', 0)}")
            output_text.append(f"  Category count: {neo4j_stats.get('category_count', 0)}")
            
            qdrant_stats = stats.get('qdrant', {})
            output_text.append(f"Qdrant:")
            output_text.append(f"  Vector count: {qdrant_stats.get('vector_count', 0)}")
            output_text.append(f"  Estimated document count: {qdrant_stats.get('estimated_document_count', 0)}")
            output_text.append(f"  Vector size (bytes): {qdrant_stats.get('size_bytes', 0)}")
            output_text.append(f"  Distance metric: {qdrant_stats.get('distance', 'unknown')}")
            
            results = stats
            
        elif args.list_categories:
            # List categories
            categories = query_engine.get_all_categories()
            output_text.append(f"Available Categories ({len(categories)}):")
            output_text.append("-" * 50)
            for category in categories:
                output_text.append(f"- {category}")
            
            results = categories
            
        elif args.document:
            # Get document by ID
            doc_id = args.document
            document = query_engine.get_document_with_chunks(doc_id)
            
            if document:
                output_text.append(f"Document: {document.get('title', 'Untitled')} ({doc_id})")
                output_text.append(f"Category: {document.get('category', 'Uncategorized')}")
                
                if 'chunks' in document and document['chunks']:
                    output_text.append(f"Chunks: {len(document['chunks'])}")
                    
                    # Get the full text
                    full_text = []
                    for chunk in sorted(document['chunks'], key=lambda x: x.get('position', 0)):
                        full_text.append(chunk.get('text', ''))
                    
                    output_text.append("\nContent:")
                    output_text.append("-" * 50)
                    output_text.append("\n\n".join(full_text))
                    output_text.append("-" * 50)
                    
                    # Get related documents
                    related = query_engine.suggest_related(doc_id)
                    if related:
                        output_text.append("\nRelated Documents:")
                        for i, rel_doc in enumerate(related):
                            output_text.append(f"{i+1}. {rel_doc.get('title', 'Untitled')} ({rel_doc.get('id', 'No ID')})")
            else:
                output_text.append(f"Document not found: {doc_id}")
            
            results = document
            
        elif args.expand:
            # Expand context around chunk
            chunk_id = args.expand
            context_size = args.context_size
            
            context = query_engine.expand_context(chunk_id, context_size)
            
            if context:
                output_text.append(f"Context for Chunk: {chunk_id}")
                output_text.append("-" * 50)
                
                # Center chunk
                if 'center' in context:
                    center = context['center']
                    output_text.append(f"Center Chunk:")
                    output_text.append(f"ID: {center.get('id', 'No ID')}")
                    output_text.append(center.get('text', 'No content'))
                    output_text.append("")
                
                # Previous chunks
                if 'previous' in context and context['previous']:
                    output_text.append(f"Previous Chunks:")
                    for prev in context['previous']:
                        output_text.append(f"ID: {prev.get('id', 'No ID')}")
                        output_text.append(prev.get('text', 'No content'))
                        output_text.append("")
                
                # Next chunks
                if 'next' in context and context['next']:
                    output_text.append(f"Next Chunks:")
                    for next_chunk in context['next']:
                        output_text.append(f"ID: {next_chunk.get('id', 'No ID')}")
                        output_text.append(next_chunk.get('text', 'No content'))
                        output_text.append("")
                
                # Document info
                if 'document' in context:
                    doc = context['document']
                    output_text.append(f"Document: {doc.get('title', 'Untitled')} ({doc.get('id', 'No ID')})")
                    output_text.append(f"Category: {doc.get('category', 'Uncategorized')}")
            else:
                output_text.append(f"Chunk not found: {chunk_id}")
            
            results = context
            
        elif args.query:
            # Perform search
            query = args.query
            search_type = args.type
            category = args.category
            limit = args.limit
            
            output_text.append(f"Query: '{query}'")
            output_text.append(f"Type: {search_type}")
            if category:
                output_text.append(f"Category: {category}")
            output_text.append(f"Limit: {limit}")
            output_text.append("")
            
            if search_type == 'semantic':
                # Semantic search
                results = query_engine.semantic_search(query, limit, category)
            elif search_type == 'category':
                # Category search
                if not category:
                    output_text.append("Error: Category search requires a category")
                    return 1
                results = query_engine.category_search(category, limit)
            else:
                # Hybrid search (default)
                results = query_engine.hybrid_search(query, limit, category)
            
            # Display results
            if results:
                output_text.append(f"Found {len(results)} results:")
                output_text.append("")
                
                for i, result in enumerate(results):
                    output_text.append(format_result_for_display(result, i))
                    if i < len(results) - 1:
                        output_text.append("\n" + "=" * 70 + "\n")
            else:
                output_text.append("No results found")
        else:
            # No action specified
            output_text.append("Error: No action specified. Use --query, --document, --expand, --list-categories, or --stats")
            return 1
        
        # Display output
        print("\n".join(output_text))
        
        # Write results to file if requested
        if args.output and results:
            with open(args.output, 'w') as f:
                if isinstance(results, list) and len(results) > 0 and isinstance(results[0], str):
                    # List of strings (categories)
                    f.write(json.dumps(results, indent=2))
                else:
                    # Other results (dict or list of dicts)
                    json.dump(results, f, indent=2)
            logger.info(f"Results written to {args.output}")
        
        return 0
    except Exception as e:
        logger.error(f"Error during query execution: {str(e)}")
        return 1
    finally:
        # Clean up connections
        try:
            neo4j_manager.close()
            qdrant_manager.close()
            if embedding_processor.model:
                embedding_processor.unload_model()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

if __name__ == "__main__":
    sys.exit(main()) 