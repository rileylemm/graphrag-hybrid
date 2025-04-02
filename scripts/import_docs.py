#!/usr/bin/env python3
"""
Import Markdown documents into the hybrid Neo4j/Qdrant database system.

This script processes markdown documents, extracts their content and metadata,
creates chunks, and imports them into both Neo4j and Qdrant databases.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the parent directory to the path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database.neo4j_manager import Neo4jManager
from src.database.qdrant_manager import QdrantManager
from src.processors.document_processor import DocumentProcessor
from src.processors.embedding_processor import EmbeddingProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('import_docs.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_argparse():
    """Set up command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Import documents into the Neo4j and Qdrant databases'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='.env',
        help='Path to configuration file (.env or YAML)'
    )
    
    parser.add_argument(
        '--docs-dir', '-d',
        type=str,
        default='your_docs_here',
        help='Directory containing markdown documents to import'
    )
    
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        default=True,
        help='Recursively process subdirectories (default: True)'
    )
    
    parser.add_argument(
        '--clear', '-C',
        action='store_true',
        default=False,
        help='Clear existing data before import'
    )
    
    parser.add_argument(
        '--setup-schema', '-s',
        action='store_true',
        default=True,
        help='Set up Neo4j schema (default: True)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=False,
        help='Enable verbose output'
    )
    
    return parser.parse_args()

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
    
    # Create database managers
    try:
        neo4j_manager = Neo4jManager(config)
        neo4j_manager.connect()
        
        embedding_processor = EmbeddingProcessor(config)
        embedding_processor.load_model()
        
        qdrant_manager = QdrantManager(config, embedding_processor)
        qdrant_manager.connect()
        
        logger.info("Database connections established")
    except Exception as e:
        logger.error(f"Error connecting to databases: {str(e)}")
        return 1
    
    # Set up Neo4j schema if requested
    if args.setup_schema:
        try:
            neo4j_manager.setup_schema()
            logger.info("Neo4j schema set up successfully")
        except Exception as e:
            logger.error(f"Error setting up Neo4j schema: {str(e)}")
            return 1
    
    # Clear existing data if requested
    if args.clear:
        try:
            logger.warning("Clearing existing data...")
            neo4j_manager.clear_database()
            qdrant_manager.clear_collection()
            logger.info("Existing data cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing existing data: {str(e)}")
            return 1
    
    # Create Qdrant collection if it doesn't exist
    try:
        qdrant_manager.create_collection(recreate=False)
        logger.info("Qdrant collection created/verified")
    except Exception as e:
        logger.error(f"Error creating Qdrant collection: {str(e)}")
        return 1
    
    # Process documents
    try:
        # Check if docs directory exists
        docs_dir = args.docs_dir
        if not os.path.exists(docs_dir):
            logger.error(f"Documents directory does not exist: {docs_dir}")
            return 1
        
        # Create document processor
        document_processor = DocumentProcessor(config)
        
        # Process documents
        logger.info(f"Processing documents from {docs_dir} (recursive: {args.recursive})")
        documents, chunks = document_processor.process_directory(
            docs_dir, 
            recursive=args.recursive
        )
        
        if not documents or not chunks:
            logger.warning("No documents or chunks found to import")
            return 0
        
        # Import documents and chunks into Neo4j
        logger.info(f"Importing {len(documents)} documents with {len(chunks)} chunks into Neo4j")
        neo4j_manager.import_documents(documents, chunks)
        
        # Import chunks into Qdrant
        logger.info(f"Importing {len(chunks)} chunks into Qdrant")
        qdrant_manager.import_chunks(chunks)
        
        # Log statistics
        neo4j_stats = neo4j_manager.get_statistics()
        logger.info(f"Neo4j statistics: {neo4j_stats}")
        
        qdrant_stats = qdrant_manager.get_statistics()
        logger.info(f"Qdrant statistics: {qdrant_stats}")
        
        logger.info("Import completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error during document import: {str(e)}")
        return 1
    finally:
        # Clean up connections
        try:
            neo4j_manager.close()
            qdrant_manager.close()
            embedding_processor.unload_model()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

if __name__ == "__main__":
    sys.exit(main()) 