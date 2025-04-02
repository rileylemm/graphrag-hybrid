"""
Qdrant vector database manager for GraphRAG
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Union
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

class QdrantManager:
    """Manager for Qdrant vector database operations"""
    
    def __init__(self, config, embedding_model=None):
        """Initialize Qdrant manager with configuration"""
        self.config = config
        self.host = config.get('qdrant.host', 'localhost')
        self.port = config.get('qdrant.port', 6333)
        self.grpc_port = config.get('qdrant.grpc_port', 6334)
        self.collection_name = config.get('qdrant.collection', 'document_chunks')
        self.prefer_grpc = config.get('qdrant.prefer_grpc', True)
        self.vector_size = config.get('embedding.vector_size', 384)
        self.embedding_model = embedding_model
        self.client = None
        
    def connect(self):
        """Connect to Qdrant server"""
        try:
            logger.info(f"Connecting to Qdrant at {self.host}:{self.port}")
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.prefer_grpc
            )
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Successfully connected to Qdrant. Available collections: {collections.collections}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise
    
    def close(self):
        """Close Qdrant connection"""
        # Qdrant client doesn't have an explicit close method
        # But we set it to None to allow garbage collection
        if self.client:
            self.client = None
            logger.info("Qdrant connection released")
    
    def create_collection(self, recreate=False):
        """Create or recreate the vector collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if exists:
                if recreate:
                    logger.warning(f"Deleting existing collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return True
            
            # Create collection
            logger.info(f"Creating collection: {self.collection_name} with vector size {self.vector_size}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )
            
            # Create payload index for filtering
            index_fields = ["category", "doc_id"]
            for field in index_fields:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
            
            logger.info(f"Collection {self.collection_name} created with indexes")
            return True
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    def get_collection_info(self):
        """Get information about the collection"""
        try:
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None
    
    def clear_collection(self):
        """Clear all vectors from the collection"""
        try:
            logger.warning(f"Clearing all data from collection: {self.collection_name}")
            self.client.delete_collection(self.collection_name)
            self.create_collection()
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            raise
    
    def import_chunks(self, chunks):
        """Import document chunks into Qdrant collection"""
        if not self.embedding_model:
            raise ValueError("Embedding model is required for importing chunks")
        
        logger.info(f"Importing {len(chunks)} chunks into Qdrant")
        
        # Batch processing and progress tracking
        batch_size = 100
        points = []
        
        try:
            for i, chunk in enumerate(chunks):
                # Generate embedding for the chunk text
                try:
                    embedding = self.embedding_model.get_embedding(chunk['text'])
                except Exception as e:
                    logger.error(f"Error generating embedding for chunk {i}: {str(e)}")
                    continue
                
                # Prepare point data
                point_id = chunk['id']
                
                # Prepare payload (metadata)
                payload = {
                    'text': chunk['text'],
                    'doc_id': chunk['doc_id'],
                    'position': chunk['position']
                }
                
                # Add metadata from the document
                if 'metadata' in chunk:
                    for key, value in chunk['metadata'].items():
                        if key not in payload and key not in ['text', 'id']:
                            payload[key] = value
                
                # Create point
                point = models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                
                points.append(point)
                
                # Upload batch when reaching batch size
                if len(points) >= batch_size:
                    self._upload_batch(points)
                    logger.debug(f"Uploaded batch of {len(points)} vectors. Progress: {i+1}/{len(chunks)}")
                    points = []
            
            # Upload any remaining points
            if points:
                self._upload_batch(points)
                logger.debug(f"Uploaded final batch of {len(points)} vectors")
            
            logger.info(f"Successfully imported {len(chunks)} chunks into Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error importing chunks to Qdrant: {str(e)}")
            raise
    
    def _upload_batch(self, points):
        """Upload a batch of points to Qdrant"""
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            logger.error(f"Error uploading batch to Qdrant: {str(e)}")
            raise
    
    def search(self, query_text, limit=5, filter_conditions=None):
        """Search for similar vectors in Qdrant"""
        if not self.embedding_model:
            raise ValueError("Embedding model is required for search")
        
        try:
            logger.info(f"Searching for: '{query_text}' with limit {limit}")
            query_vector = self.embedding_model.get_embedding(query_text)
            
            # Prepare filter if needed
            search_filter = None
            if filter_conditions:
                search_filter = self._prepare_filter(filter_conditions)
            
            # Search in Qdrant
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter
            )
            
            # Process results
            results = []
            for scored_point in search_result:
                result = {
                    'id': scored_point.id,
                    'score': scored_point.score,
                    'text': scored_point.payload.get('text', ''),
                    'doc_id': scored_point.payload.get('doc_id', ''),
                    'position': scored_point.payload.get('position', 0),
                }
                
                # Add additional metadata
                for key, value in scored_point.payload.items():
                    if key not in result and key not in ['text']:
                        result[key] = value
                
                results.append(result)
            
            logger.info(f"Found {len(results)} results for query")
            return results
        except Exception as e:
            logger.error(f"Error searching in Qdrant: {str(e)}")
            return []
    
    def _prepare_filter(self, filter_conditions):
        """Prepare Qdrant filter from conditions"""
        if not filter_conditions:
            return None
        
        # Try to handle both older and newer Qdrant filter formats
        try:
            # First try newer format (dict-based)
            if isinstance(filter_conditions, dict):
                # Simple filter structure for categories, doc_ids, etc.
                filter_parts = []
                
                # Handle dict filters
                for key, value in filter_conditions.items():
                    if isinstance(value, list):
                        filter_parts.append(
                            models.FieldCondition(
                                key=key, 
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        filter_parts.append(
                            models.FieldCondition(
                                key=key, 
                                match=models.MatchValue(value=value)
                            )
                        )
                
                if len(filter_parts) > 1:
                    return models.Filter(
                        must=filter_parts
                    )
                elif len(filter_parts) == 1:
                    return models.Filter(
                        must=[filter_parts[0]]
                    )
            
            # Fall back to allowing a pre-constructed Filter object
            return filter_conditions
            
        except Exception as e:
            logger.warning(f"Error preparing filter with newer format, trying legacy: {str(e)}")
            
            # Legacy format (Qdrant v0.x)
            try:
                # Convert dictionary format to legacy Qdrant filter
                if isinstance(filter_conditions, dict):
                    conditions = []
                    for key, value in filter_conditions.items():
                        if isinstance(value, list):
                            conditions.append({
                                "key": key,
                                "match": {"any": value}
                            })
                        else:
                            conditions.append({
                                "key": key,
                                "match": {"value": value}
                            })
                    
                    if len(conditions) > 1:
                        return {"must": conditions}
                    elif len(conditions) == 1:
                        return conditions[0]
                return filter_conditions
            except Exception as e2:
                logger.error(f"Error preparing filter with legacy format: {str(e2)}")
                return None
    
    def get_count(self, filter_conditions=None):
        """Get the count of vectors in the collection"""
        try:
            search_filter = None
            if filter_conditions:
                search_filter = self._prepare_filter(filter_conditions)
            
            count = self.client.count(
                collection_name=self.collection_name,
                count_filter=search_filter
            )
            return count.count
        except Exception as e:
            logger.error(f"Error getting count from Qdrant: {str(e)}")
            return 0
    
    def get_by_id(self, chunk_id):
        """Get a specific vector by ID"""
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id],
                with_vectors=True
            )
            
            if points and len(points) > 0:
                point = points[0]
                result = {
                    'id': point.id,
                    'vector': point.vector,
                    'text': point.payload.get('text', ''),
                    'doc_id': point.payload.get('doc_id', ''),
                    'position': point.payload.get('position', 0),
                }
                
                # Add additional metadata
                for key, value in point.payload.items():
                    if key not in result and key not in ['text']:
                        result[key] = value
                
                return result
            return None
        except Exception as e:
            logger.error(f"Error retrieving point from Qdrant: {str(e)}")
            return None
    
    def get_by_filter(self, filter_conditions, limit=100):
        """Get vectors by filter conditions"""
        try:
            search_filter = self._prepare_filter(filter_conditions)
            
            # Scroll through results (pagination)
            points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=limit,
                with_vectors=False
            )[0]  # scroll returns (points, offset)
            
            # Process results
            results = []
            for point in points:
                result = {
                    'id': point.id,
                    'text': point.payload.get('text', ''),
                    'doc_id': point.payload.get('doc_id', ''),
                    'position': point.payload.get('position', 0),
                }
                
                # Add additional metadata
                for key, value in point.payload.items():
                    if key not in result and key not in ['text']:
                        result[key] = value
                
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error getting vectors by filter from Qdrant: {str(e)}")
            return []
    
    def get_document_chunks(self, doc_id):
        """Get all chunks for a specific document ordered by position"""
        try:
            # Get chunks by document ID
            chunks = self.get_by_filter({'doc_id': doc_id})
            
            # Sort by position
            chunks.sort(key=lambda x: x.get('position', 0))
            
            return chunks
        except Exception as e:
            logger.error(f"Error getting document chunks from Qdrant: {str(e)}")
            return []
    
    def get_statistics(self):
        """Get vector collection statistics"""
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            
            # Count vectors
            total_vectors = collection_info.vectors_count
            
            # Count documents by distinct doc_id
            # No direct Qdrant API for this, so use an approximation
            sample_size = min(1000, total_vectors)
            if sample_size > 0:
                sample = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=sample_size,
                    with_vectors=False
                )[0]
                
                doc_ids = set()
                for point in sample:
                    doc_id = point.payload.get('doc_id')
                    if doc_id:
                        doc_ids.add(doc_id)
                
                # Rough estimate of distinct documents
                estimated_docs = len(doc_ids) / sample_size * total_vectors
            else:
                estimated_docs = 0
            
            return {
                'vector_count': total_vectors,
                'estimated_document_count': int(estimated_docs),
                'size_bytes': collection_info.config.params.vectors.size * total_vectors * 4,  # size in bytes (float32)
                'distance': collection_info.config.params.vectors.distance.name
            }
        except Exception as e:
            logger.error(f"Error getting Qdrant statistics: {str(e)}")
            return {} 