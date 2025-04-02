"""
Markdown document processor.

This module handles the processing of markdown documents:
1. Reading markdown files
2. Extracting YAML frontmatter
3. Text chunking
4. Embedding generation
5. Storage in Neo4j and Qdrant
6. Creating document relationships
7. Adding topic relationships
"""

import os
import re
import uuid
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

from langchain.text_splitter import MarkdownTextSplitter
from sentence_transformers import SentenceTransformer

from src.utils.neo4j_utils import Neo4jHelper
from src.utils.qdrant_utils import QdrantHelper
from src.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarkdownProcessor:
    """
    Process markdown documents and store them in Neo4j and Qdrant.
    """
    
    def __init__(
        self,
        neo4j_helper: Neo4jHelper,
        qdrant_helper: QdrantHelper,
        embedding_model: str = EMBEDDING_MODEL,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        """
        Initialize the markdown processor.
        
        Args:
            neo4j_helper: Neo4j helper instance
            qdrant_helper: Qdrant helper instance
            embedding_model: Name of the embedding model to use
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.neo4j = neo4j_helper
        self.qdrant = qdrant_helper
        self.text_splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Keep track of document IDs for post-processing relationships
        self.processed_docs = {}  # {file_path: doc_id}
        self.pending_relationships = []  # [(source_doc_id, target_path, rel_type)]
        
        # Mapping between Neo4j chunk IDs and Qdrant chunk IDs
        self.chunk_id_mapping = {}  # {neo4j_chunk_id: qdrant_chunk_id}
        
    def extract_frontmatter(self, md_text: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract YAML frontmatter from markdown text.
        
        Args:
            md_text: The markdown text
            
        Returns:
            Tuple of (frontmatter dict, content without frontmatter)
        """
        frontmatter = {}
        content = md_text
        
        # Check for YAML frontmatter (between --- delimiters)
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', md_text, re.DOTALL)
        if fm_match:
            try:
                yaml_content = fm_match.group(1)
                frontmatter = yaml.safe_load(yaml_content)
                content = fm_match.group(2)
            except Exception as e:
                logger.warning(f"Failed to parse YAML frontmatter: {str(e)}")
        
        return frontmatter, content
        
    def extract_title_from_md(self, md_text: str, frontmatter: Dict[str, Any] = None) -> str:
        """
        Extract the title from a markdown document.
        
        Args:
            md_text: The markdown text
            frontmatter: Optional frontmatter dict
            
        Returns:
            The extracted title or a default title
        """
        # First check frontmatter for title
        if frontmatter and 'title' in frontmatter:
            return frontmatter['title']
            
        # Look for a level 1 heading at the start of the document
        title_match = re.search(r'^# (.*?)$', md_text, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
            
        # If no level 1 heading, look for any heading
        any_heading = re.search(r'^#{1,6} (.*?)$', md_text, re.MULTILINE)
        if any_heading:
            return any_heading.group(1).strip()
            
        # Return the first line if no heading found
        first_line = md_text.strip().split('\n')[0]
        if first_line:
            # Remove markdown formatting
            clean_line = re.sub(r'[#*`_\[\]()]', '', first_line).strip()
            return clean_line[:50] + ('...' if len(clean_line) > 50 else '')
            
        # Default title
        return "Untitled Document"
    
    def resolve_relative_path(self, base_path: str, related_path: str) -> str:
        """
        Resolve a relative path from the base document's path.
        
        Args:
            base_path: Base directory path
            related_path: Relative path from frontmatter
            
        Returns:
            Absolute path
        """
        base_dir = os.path.dirname(base_path)
        
        # Handle different path formats
        if related_path.startswith('/'):
            # Absolute path from docs root
            # Find the project root by walking up from base_dir
            root_path = Path(base_dir)
            while root_path.name != 'your_docs_here' and root_path.parent != root_path:
                root_path = root_path.parent
                
            # If we found 'your_docs_here' directory, use it as root
            if root_path.name == 'your_docs_here':
                return str(root_path / related_path[1:])
            else:
                # Fallback - just use as is
                return related_path
        else:
            # Relative path from current file
            return os.path.normpath(os.path.join(base_dir, related_path))
    
    def process_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Process a single markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Processing file: {file_path}")
        try:
            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}"
                
            # Check if it's a markdown file
            if path.suffix.lower() != '.md':
                return False, f"Not a markdown file: {file_path}"
                
            # Generate a document ID
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"
            
            # Store in mapping for relationship processing
            self.processed_docs[str(path.absolute())] = doc_id
            
            # Read the file
            md_content = path.read_text(encoding='utf-8')
            
            # Extract frontmatter
            frontmatter, content = self.extract_frontmatter(md_content)
            
            # Extract title
            title = self.extract_title_from_md(content, frontmatter)
            
            # Create document in Neo4j with metadata
            category = frontmatter.get('category', '')
            updated = frontmatter.get('updated', '')
            
            self.neo4j.create_document_with_metadata(
                doc_id=doc_id,
                title=title,
                path=str(path.absolute()),
                category=category,
                updated=updated,
                metadata=frontmatter
            )
            
            # Queue related document relationships for later processing
            if 'related' in frontmatter and isinstance(frontmatter['related'], list):
                for related_path in frontmatter['related']:
                    resolved_path = self.resolve_relative_path(str(path.absolute()), related_path)
                    self.pending_relationships.append((doc_id, resolved_path, 'RELATED_TO'))
            
            # Process key concepts
            if 'key_concepts' in frontmatter and isinstance(frontmatter['key_concepts'], list):
                for concept in frontmatter['key_concepts']:
                    self.neo4j.create_topic_and_relationship(doc_id, concept)
            
            # Split text into chunks - we only chunk the content, not the frontmatter
            chunks = self.text_splitter.split_text(content)
            
            # Process each chunk
            prev_chunk_id = None
            qdrant_points = []
            
            for i, chunk_text in enumerate(chunks):
                # Generate chunk ID for Neo4j (string ID)
                neo4j_chunk_id = f"chunk_{doc_id}_{i}"
                
                # Generate a UUID for Qdrant (Qdrant v1.5.1 requires UUID or integer IDs)
                qdrant_chunk_id = str(uuid.uuid4())  # Use string representation of UUID
                
                # Store the mapping between Neo4j and Qdrant IDs
                self.chunk_id_mapping[neo4j_chunk_id] = qdrant_chunk_id
                
                # Store in Neo4j
                self.neo4j.create_content_chunk(
                    chunk_id=neo4j_chunk_id,
                    text=chunk_text,
                    doc_id=doc_id,
                    sequence=i
                )
                
                # Link to previous chunk
                if prev_chunk_id:
                    self.neo4j.link_content_chunks(prev_chunk_id, neo4j_chunk_id)
                
                # Generate embedding
                embedding = self.embedding_model.encode(chunk_text).tolist()
                
                # Prepare for Qdrant - using UUID string as ID
                qdrant_points.append({
                    "id": qdrant_chunk_id,  # Using UUID string for Qdrant
                    "vector": embedding,
                    "payload": {
                        "text": chunk_text,
                        "metadata": {
                            "doc_id": doc_id,
                            "chunk_id": neo4j_chunk_id,  # Store the Neo4j ID in the payload
                            "sequence": i,
                            "title": title,
                            "category": category,
                            "file_path": str(path.absolute())
                        }
                    }
                })
                
                prev_chunk_id = neo4j_chunk_id
            
            # Store all embeddings in Qdrant
            if qdrant_points:
                self.qdrant.store_embeddings(qdrant_points)
            
            logger.info(f"Successfully processed {path.name}: {len(chunks)} chunks")
            return True, f"Successfully processed {path.name}: {len(chunks)} chunks"
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return False, f"Error processing {file_path}: {str(e)}"
    
    def process_relationships(self):
        """
        Process relationships between documents after all files are processed.
        """
        logger.info(f"Processing relationships between documents...")
        
        for source_id, target_path, rel_type in self.pending_relationships:
            # Check if target document exists in our processed docs
            target_id = self.processed_docs.get(target_path)
            
            if target_id:
                # Create relationship between documents
                self.neo4j.link_documents(source_id, target_id, rel_type)
                logger.debug(f"Created {rel_type} relationship: {source_id} -> {target_id}")
            else:
                # Placeholder for documents that haven't been processed yet
                logger.debug(f"Target document not found: {target_path}")
    
    def process_directory(self, dir_path: str, recursive: bool = True) -> Dict[str, Any]:
        """
        Process all markdown files in a directory.
        
        Args:
            dir_path: Path to the directory
            recursive: Whether to process subdirectories
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Processing directory: {dir_path}")
        
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            return {"error": f"Directory not found: {dir_path}"}
        
        results = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        # Get all markdown files
        pattern = '**/*.md' if recursive else '*.md'
        md_files = [str(f) for f in path.glob(pattern) if f.is_file()]
        
        results["total_files"] = len(md_files)
        
        # First process all files
        for file_path in md_files:
            success, message = self.process_file(file_path)
            
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                
            results["details"].append({
                "file": file_path,
                "success": success,
                "message": message
            })
        
        # Then process relationships after all files are loaded
        self.process_relationships()
        
        return results 