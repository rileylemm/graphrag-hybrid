"""
Configuration management for GraphRAG
"""

import os
from dotenv import load_dotenv
import yaml
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager that loads from .env, YAML, or code"""
    
    def __init__(self, config_path=None):
        """Initialize with optional config file path"""
        # Load environment variables
        load_dotenv()
        
        # Default configuration
        self.config = {
            "neo4j": {
                "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                "user": os.getenv("NEO4J_USER", "neo4j"),
                "password": os.getenv("NEO4J_PASSWORD", "password")
            },
            "qdrant": {
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": int(os.getenv("QDRANT_PORT", 6333)),
                "collection": os.getenv("QDRANT_COLLECTION", "document_chunks")
            },
            "embedding": {
                "model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                "dimension": int(os.getenv("EMBEDDING_DIMENSION", 384))
            },
            "chunking": {
                "chunk_size": int(os.getenv("CHUNK_SIZE", 600)),
                "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 100))
            }
        }
        
        # Override with YAML config if provided
        if config_path and os.path.exists(config_path):
            self._load_from_yaml(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            if config_path:
                logger.warning(f"Config file not found: {config_path}")
            logger.info("Using default configuration and environment variables")
    
    def _load_from_yaml(self, path):
        """Load configuration from YAML file"""
        try:
            with open(path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # Recursively update config
                    self._update_dict(self.config, yaml_config)
                    logger.debug(f"Loaded YAML configuration: {yaml_config}")
        except Exception as e:
            logger.error(f"Error loading YAML configuration: {str(e)}")
    
    def _update_dict(self, d, u):
        """Recursively update nested dictionary"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._update_dict(d.get(k, {}), v)
            else:
                d[k] = v
        return d
    
    def get(self, key, default=None):
        """Get a config value, traversing nested dictionaries with dot notation"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
        
    def set(self, key, value):
        """Set a config value, creating nested dictionaries as needed"""
        keys = key.split('.')
        d = self.config
        
        # Navigate to the right level
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            elif not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
            
        # Set the value
        d[keys[-1]] = value
    
    def __str__(self):
        """Return a string representation of the configuration"""
        return yaml.dump(self.config, default_flow_style=False)

# Create default configuration instance
config = Config()

# Export commonly used variables
NEO4J_URI = config.get('neo4j.uri')
NEO4J_USER = config.get('neo4j.user')
NEO4J_PASSWORD = config.get('neo4j.password')

QDRANT_HOST = config.get('qdrant.host')
QDRANT_PORT = config.get('qdrant.port')
QDRANT_COLLECTION = config.get('qdrant.collection')

EMBEDDING_MODEL = config.get('embedding.model')
EMBEDDING_DIMENSION = config.get('embedding.dimension') 