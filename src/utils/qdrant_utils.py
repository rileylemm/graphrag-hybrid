"""
Qdrant utility functions.
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
import warnings

from src.config import (
    QDRANT_HOST, 
    QDRANT_PORT, 
    EMBEDDING_DIMENSION, 
    QDRANT_COLLECTION
)

class QdrantHelper:
    """Helper class for Qdrant operations."""
    
    def __init__(self, host=QDRANT_HOST, port=QDRANT_PORT, collection_name=QDRANT_COLLECTION):
        """Initialize the Qdrant client."""
        # Suppress the version mismatch warning
        warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
    
    def verify_connection(self):
        """Verify the Qdrant connection is working."""
        try:
            # Try to get collections as a simple connectivity check
            collections = self.client.get_collections()
            return f"Connection successful. Collections: {collections}"
        except Exception as e:
            return f"Connection failed: {str(e)}"
    
    def test_connection(self):
        """Test the Qdrant connection."""
        try:
            result = self.verify_connection()
            return "Connection successful" in result
        except Exception:
            return False
    
    def setup_collection(self, dimension=EMBEDDING_DIMENSION):
        """Set up the Qdrant collection for document embeddings."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            # Create collection if it doesn't exist
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE
                    ),
                )
                
                # Create payload index for efficient filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="metadata.doc_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                
                # Create payload index for chunk sequence
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="metadata.sequence",
                    field_schema=models.PayloadSchemaType.INTEGER,
                )
                
                return f"Collection '{self.collection_name}' created successfully."
            else:
                return f"Collection '{self.collection_name}' already exists."
        
        except Exception as e:
            return f"Collection setup failed: {str(e)}"
    
    def store_embeddings(self, points):
        """
        Store document chunk embeddings in Qdrant.
        
        Args:
            points: List of dictionaries with the following keys:
                - id: Unique identifier for the chunk
                - vector: Embedding vector
                - payload: Metadata including text, doc_id, etc.
        
        Returns:
            Operation result message
        """
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return f"Successfully stored {len(points)} embeddings in Qdrant."
        except Exception as e:
            return f"Failed to store embeddings: {str(e)}"
    
    def search_similar(self, query_vector, limit=5, filter_by=None):
        """Search for similar documents based on a query vector."""
        try:
            # Handle older Qdrant versions by checking if filter_by is provided
            if filter_by:
                # Try to convert the filter to a proper Qdrant filter format
                try:
                    filter_param = models.Filter(**filter_by)
                    results = self.client.query_points(
                        collection_name=self.collection_name,
                        vector=query_vector,
                        limit=limit,
                        query_filter=filter_param
                    )
                except TypeError:
                    # If filter format is not compatible, try without filter
                    print(f"Filter not compatible with this Qdrant version, searching without filter")
                    results = self.client.query_points(
                        collection_name=self.collection_name,
                        vector=query_vector,
                        limit=limit
                    )
            else:
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    vector=query_vector,
                    limit=limit
                )
            return results
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    def get_collection_info(self):
        """Get information about the collection."""
        try:
            return self.client.get_collection(collection_name=self.collection_name)
        except Exception as e:
            return f"Failed to get collection info: {str(e)}" 