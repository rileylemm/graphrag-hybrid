import time
import os
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

def test_neo4j_connection():
    """Test connection to Neo4j"""
    print("Testing Neo4j connection...")
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "password"
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j connection successful' as message")
            print(result.single()["message"])
            # Count nodes
            count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            print(f"Neo4j database contains {count} nodes")
        driver.close()
        return True
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        return False

def test_qdrant_connection():
    """Test connection to Qdrant"""
    print("Testing Qdrant connection...")
    try:
        client = QdrantClient(host="localhost", port=6333)
        # Check if Qdrant is running by making a simple API call
        status = client.get_collections()
        print(f"Qdrant connection successful. Collections: {len(status.collections)}")
        
        # Check collections
        collections = client.get_collections().collections
        if collections:
            collection_names = [c.name for c in collections]
            print(f"Available collections: {', '.join(collection_names)}")
            
            # Check document_chunks collection
            if "document_chunks" in collection_names:
                collection_info = client.get_collection("document_chunks")
                print(f"document_chunks collection info: {collection_info}")
        return True
    except Exception as e:
        print(f"Qdrant connection failed: {e}")
        return False

def main():
    print("Testing database connections with standard ports...")
    print("Neo4j: bolt://localhost:7687, http://localhost:7474")
    print("Qdrant: http://localhost:6333")
    
    neo4j_success = test_neo4j_connection()
    qdrant_success = test_qdrant_connection()
    
    if neo4j_success and qdrant_success:
        print("\n✅ Both databases are connected successfully!")
    else:
        print("\n❌ Some connections failed. Please check the logs above.")

if __name__ == "__main__":
    main() 