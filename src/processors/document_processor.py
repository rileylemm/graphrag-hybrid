"""
Document processor for parsing and chunking documents
"""

import re
import os
import uuid
import yaml
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process documents into chunks with metadata"""
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.chunk_size = config.get('chunking.chunk_size', 600)
        self.chunk_overlap = config.get('chunking.chunk_overlap', 100)
        self.supported_extensions = ['.md', '.markdown']
    
    def process_document(self, file_path):
        """Process a document file into chunks with metadata"""
        logger.info(f"Processing document: {file_path}")
        
        # Check if file exists and has supported extension
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
            
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.supported_extensions:
            raise ValueError(f"Unsupported file extension: {ext}. Supported: {self.supported_extensions}")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract YAML front matter and content
        metadata, text = self._extract_front_matter(content)
        
        # Add defaults and file path to metadata
        metadata['path'] = file_path
        if 'id' not in metadata:
            metadata['id'] = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Ensure required fields
        if 'title' not in metadata or not metadata['title']:
            # Try to extract title from first heading or use filename
            title = self._extract_title_from_text(text)
            if not title:
                title = os.path.basename(file_path)
            metadata['title'] = title
        
        if 'category' not in metadata:
            # Default category based on directory structure
            dir_path = os.path.dirname(file_path)
            base_dir = os.path.basename(dir_path)
            metadata['category'] = base_dir if base_dir else 'uncategorized'
        
        # Chunk the document
        chunks = self._chunk_text(text)
        logger.info(f"Document chunked into {len(chunks)} parts")
        
        # Create chunk objects with metadata
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            # Use UUID for both Neo4j and Qdrant
            chunk_id = str(uuid.uuid4())
            chunk_objects.append({
                'id': chunk_id,
                'text': chunk_text,
                'doc_id': metadata['id'],
                'position': i,
                'metadata': metadata,
            })
        
        return metadata, chunk_objects
    
    def _extract_front_matter(self, content):
        """Extract YAML front matter from document content"""
        # Match YAML front matter pattern ---\n...\n---
        front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        
        if front_matter_match:
            yaml_text = front_matter_match.group(1)
            content_text = front_matter_match.group(2)
            try:
                metadata = yaml.safe_load(yaml_text)
                if metadata and isinstance(metadata, dict):
                    logger.debug(f"Extracted metadata: {metadata.keys()}")
                    return metadata, content_text
            except yaml.YAMLError as e:
                logger.warning(f"Error parsing YAML front matter: {str(e)}")
        
        # No front matter or parsing failed, return minimal metadata
        logger.debug("No valid front matter found, using defaults")
        return {'title': '', 'category': ''}, content
    
    def _extract_title_from_text(self, text):
        """Extract title from first heading in the document"""
        # Look for first # heading
        heading_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()
        return ''
    
    def _chunk_text(self, text):
        """Split text into chunks with overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # Adjust end to nearest paragraph or sentence boundary if possible
            if end < len(text):
                # First try paragraph boundary
                paragraph_boundary = text.find('\n\n', end - 100, end + 100)
                if paragraph_boundary != -1:
                    end = paragraph_boundary + 2  # Include the newlines
                else:
                    # Try sentence boundary
                    sentence_boundary = re.search(r'[.!?]\s+', text[end-50:end+50])
                    if sentence_boundary:
                        # Adjust the match position to the global text
                        end = end - 50 + sentence_boundary.end()
            
            # Extract chunk with adjusted boundary
            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Move start position for next chunk, accounting for overlap
            start = max(end - self.chunk_overlap, start + 1)  # Ensure progress
        
        return chunks
    
    def process_directory(self, directory_path, recursive=True):
        """Process all documents in a directory"""
        logger.info(f"Processing directory: {directory_path} (recursive: {recursive})")
        
        all_docs = []
        all_chunks = []
        
        # Get list of files
        files = []
        if recursive:
            for root, _, filenames in os.walk(directory_path):
                for filename in filenames:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in self.supported_extensions:
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in self.supported_extensions:
                        files.append(file_path)
        
        logger.info(f"Found {len(files)} documents to process")
        
        # Process each file
        for file_path in files:
            try:
                metadata, chunks = self.process_document(file_path)
                all_docs.append(metadata)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        logger.info(f"Processed {len(all_docs)} documents with {len(all_chunks)} total chunks")
        return all_docs, all_chunks 