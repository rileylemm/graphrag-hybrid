"""
Embedding processor for converting text to vector embeddings
"""

import logging
from typing import List, Optional, Union, Dict, Any
import numpy as np

try:
    import torch
    from transformers import AutoTokenizer, AutoModel, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class EmbeddingProcessor:
    """Process text into vector embeddings using a transformer model"""
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.model_name = config.get('embedding.model_name', 'sentence-transformers/all-MiniLM-L6-v2')
        self.vector_size = config.get('embedding.vector_size', 384)  # Default for all-MiniLM-L6-v2
        self.device = config.get('embedding.device', 'cpu')
        self.max_length = config.get('embedding.max_length', 512)
        self.tokenizer = None
        self.model = None
        
        # Validate transformers availability
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers package not available. Please install with: pip install transformers torch")
            raise ImportError("Required package 'transformers' is not installed")
    
    def load_model(self):
        """Load the embedding model and tokenizer"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            
            # Check if CUDA is available when device is set to 'cuda'
            if self.device == 'cuda' and torch.cuda.is_available():
                logger.info("Using CUDA for embeddings")
                device = torch.device('cuda')
            else:
                if self.device == 'cuda':
                    logger.warning("CUDA requested but not available, falling back to CPU")
                device = torch.device('cpu')
                
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            
            # Move model to appropriate device
            self.model.to(device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            logger.info(f"Successfully loaded embedding model with vector size: {self.vector_size}")
            return True
        except Exception as e:
            logger.error(f"Error loading embedding model: {str(e)}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text string"""
        if not self.model or not self.tokenizer:
            self.load_model()
            
        try:
            # Handle empty or None input
            if not text:
                logger.warning("Empty text provided for embedding, returning zero vector")
                return [0.0] * self.vector_size
                
            # Truncate text if necessary
            if len(text) > 10000:  # Arbitrary limit to avoid tokenizer issues
                logger.warning(f"Text too long ({len(text)} chars), truncating to 10000 chars")
                text = text[:10000]
                
            # Tokenize and prepare for model
            inputs = self.tokenizer(
                text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            # Move inputs to same device as model
            inputs = {key: val.to(self.model.device) for key, val in inputs.items()}
            
            # Generate embeddings without gradient calculation
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            # Use mean of last hidden state as embedding (common approach)
            # Extract token embeddings, mask padding tokens, and compute mean
            embeddings = outputs.last_hidden_state
            
            # Create attention mask if not present
            if 'attention_mask' not in inputs:
                attention_mask = torch.ones_like(inputs['input_ids'])
            else:
                attention_mask = inputs['attention_mask']
                
            # Apply mask and calculate mean
            mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
            masked_embeddings = embeddings * mask
            summed = torch.sum(masked_embeddings, dim=1)
            counts = torch.sum(mask, dim=1)
            mean_pooled = summed / counts
            
            # Convert to list of floats
            embedding = mean_pooled[0].cpu().numpy().tolist()
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return zero vector on error
            return [0.0] * self.vector_size
    
    def get_batch_embeddings(self, texts: List[str], batch_size: int = 8) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        if not self.model or not self.tokenizer:
            self.load_model()
            
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            try:
                # Tokenize the batch
                encoded_batch = self.tokenizer(
                    batch, 
                    max_length=self.max_length,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )
                
                # Move batch to model device
                encoded_batch = {k: v.to(self.model.device) for k, v in encoded_batch.items()}
                
                # Generate embeddings
                with torch.no_grad():
                    outputs = self.model(**encoded_batch)
                
                # Extract embeddings using mean pooling
                embeddings = outputs.last_hidden_state
                attention_mask = encoded_batch['attention_mask']
                mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
                masked_embeddings = embeddings * mask
                summed = torch.sum(masked_embeddings, dim=1)
                counts = torch.sum(mask, dim=1)
                mean_pooled = summed / counts
                
                # Convert to list of float lists
                batch_embeddings = mean_pooled.cpu().numpy().tolist()
                results.extend(batch_embeddings)
                
                logger.debug(f"Processed batch of {len(batch)} embeddings")
            except Exception as e:
                logger.error(f"Error processing embedding batch: {str(e)}")
                # Return zero vectors for this batch
                for _ in batch:
                    results.append([0.0] * self.vector_size)
        
        return results
    
    def unload_model(self):
        """Unload model to free memory"""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        
        # Force garbage collection to free CUDA memory if applicable
        try:
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Embedding model unloaded and memory freed")
        except:
            logger.warning("Failed to fully clear memory resources")
    
    def vector_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions do not match: {len(vec1)} vs {len(vec2)}")
            
        try:
            # Convert to numpy arrays for efficient calculation
            vec1_array = np.array(vec1)
            vec2_array = np.array(vec2)
            
            # Compute dot product
            dot_product = np.dot(vec1_array, vec2_array)
            
            # Compute magnitudes
            magnitude1 = np.linalg.norm(vec1_array)
            magnitude2 = np.linalg.norm(vec2_array)
            
            # Avoid division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
                
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating vector similarity: {str(e)}")
            return 0.0