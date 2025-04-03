#!/usr/bin/env python3

import os
import sys
import time
import warnings
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance

# Suppress warnings from Qdrant client
warnings.filterwarnings("ignore", category=UserWarning)

def test_neo4j_connection(uri, auth):
    """Test connection to Neo4j database."""
    print(f"Testing Neo4j connection...")
    try:
        driver = GraphDatabase.driver(uri, auth=auth)
        with driver.session() as session:
            # Test with a simple query
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"Neo4j connection successful")
            print(f"Neo4j database contains {count} nodes")
            driver.close()
            return True
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        return False

def test_qdrant_connection(host, port):
    """Test connection to Qdrant database."""
    print(f"Testing Qdrant connection...")
    try:
        client = QdrantClient(host=host, port=port)
        collections = client.get_collections()
        print(f"Qdrant connection successful. Collections: {len(collections.collections)}")
        
        if len(collections.collections) > 0:
            collection_names = [c.name for c in collections.collections]
            print(f"Available collections: {', '.join(collection_names)}")
            
            # Get details about first collection
            if 'document_chunks' in collection_names:
                collection_info = client.get_collection('document_chunks')
                print(f"document_chunks collection info: {collection_info}")
                
                # Try to access vectors count with different API versions
                vectors_count = None
                try:
                    if hasattr(collection_info, 'vectors_count'):
                        vectors_count = collection_info.vectors_count
                    elif hasattr(collection_info, 'points_count'):
                        vectors_count = collection_info.points_count
                    
                    if vectors_count is not None:
                        print(f"Collection contains {vectors_count} vectors")
                except Exception as e:
                    print(f"Could not get vector count: {e}")
                
        return True
    except Exception as e:
        print(f"Qdrant connection failed: {e}")
        return False

def main():
    """Test connections to both databases."""
    print("Testing database connections with standard ports...")
    print("Neo4j: bolt://localhost:7687, http://localhost:7474")
    print("Qdrant: http://localhost:6333")
    
    # Test Neo4j connection
    neo4j_uri = "bolt://localhost:7687"
    neo4j_auth = ("neo4j", "password")
    neo4j_success = test_neo4j_connection(neo4j_uri, neo4j_auth)
    
    # Test Qdrant connection
    qdrant_host = "localhost"
    qdrant_port = 6333
    qdrant_success = test_qdrant_connection(qdrant_host, qdrant_port)
    
    if neo4j_success and qdrant_success:
        print("\n✅ Both databases are connected successfully!")
        return 0
    else:
        print("\n❌ One or both database connections failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 