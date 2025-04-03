#!/usr/bin/env python3

import warnings
import time
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Suppress warnings from Qdrant client
warnings.filterwarnings("ignore", category=UserWarning)

class DatabaseChecker:
    def __init__(self):
        # Neo4j connection details
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_user = "neo4j"
        self.neo4j_password = "password"
        self.neo4j_driver = None
        
        # Qdrant connection details
        self.qdrant_host = "localhost"
        self.qdrant_port = 6333
        self.qdrant_collection = "document_chunks"
        self.qdrant_client = None
        
        # Model for testing vector similarity search
        self.model_name = "all-MiniLM-L6-v2"
        self.model = None
        
    def connect_to_neo4j(self):
        """Connect to Neo4j and get basic statistics."""
        print("\n=== Testing Neo4j Connection ===")
        try:
            print(f"Connecting to Neo4j at {self.neo4j_uri}")
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test connection with a simple query
            with self.neo4j_driver.session() as session:
                # Get document count
                result = session.run("MATCH (d:Document) RETURN count(d) AS count")
                doc_count = result.single()["count"]
                print(f"✅ Connected to Neo4j with {doc_count} documents")
                
                # Get chunk count
                result = session.run("MATCH (c:Chunk) RETURN count(c) AS count")
                chunk_count = result.single()["count"]
                print(f"✅ Neo4j contains {chunk_count} chunks")
                
                # Get category count
                result = session.run("MATCH (cat:Category) RETURN count(cat) AS count")
                cat_count = result.single()["count"]
                print(f"✅ Neo4j contains {cat_count} categories")
                
                # Get relationship counts
                result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) AS type, count(r) AS count 
                ORDER BY count DESC
                """)
                print("\nRelationship Statistics:")
                for record in result:
                    print(f"  - {record['type']}: {record['count']} relationships")
                
                # Sample document titles
                result = session.run("""
                MATCH (d:Document) 
                RETURN d.title AS title 
                LIMIT 5
                """)
                print("\nSample document titles:")
                for record in result:
                    print(f"  - {record['title']}")
                
                return doc_count, chunk_count
                
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            return None, None
    
    def connect_to_qdrant(self):
        """Connect to Qdrant and get basic statistics."""
        print("\n=== Testing Qdrant Connection ===")
        try:
            print(f"Connecting to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Test connection by getting collection info
            collection_info = self.qdrant_client.get_collection(self.qdrant_collection)
            
            # Try to get vector count using different API versions
            vectors_count = 0
            if hasattr(collection_info, 'vectors_count'):
                vectors_count = collection_info.vectors_count
            elif hasattr(collection_info, 'points_count'):
                vectors_count = collection_info.points_count
            
            print(f"✅ Connected to Qdrant collection '{self.qdrant_collection}' with {vectors_count} vectors")
            
            # Get payload schema
            print("\nPayload Schema:")
            for field, schema in collection_info.payload_schema.items():
                print(f"  - {field}: {schema.data_type}, points: {schema.points}")
            
            # Sample some vectors to check content
            print("\nSampling vector data:")
            try:
                vectors = self.qdrant_client.scroll(
                    collection_name=self.qdrant_collection,
                    limit=5
                )[0]
                
                for i, vector in enumerate(vectors):
                    print(f"\nVector {i+1}:")
                    print(f"  ID: {vector.id}")
                    if hasattr(vector, 'payload'):
                        if 'doc_id' in vector.payload:
                            print(f"  Document ID: {vector.payload['doc_id']}")
                        if 'category' in vector.payload:
                            print(f"  Category: {vector.payload['category']}")
                        if 'text' in vector.payload:
                            text = vector.payload['text']
                            # Truncate text if too long
                            if len(text) > 100:
                                text = text[:100] + "..."
                            print(f"  Text: {text}")
            except Exception as e:
                print(f"⚠️ Error sampling vectors: {e}")
            
            return vectors_count
            
        except Exception as e:
            print(f"❌ Qdrant connection failed: {e}")
            return None
    
    def load_model(self):
        """Load the embedding model for testing."""
        print("\n=== Testing Embedding Model ===")
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Successfully loaded model: {self.model_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            return False
    
    def test_search(self, query="documentation"):
        """Test search functionality across both databases."""
        print(f"\n=== Testing Search with Query: '{query}' ===")
        
        if not self.model:
            print("❌ Cannot perform search: Embedding model not loaded")
            return False
        
        try:
            # Generate embedding for query
            print("Generating query embedding...")
            query_embedding = self.model.encode(query)
            print(f"✅ Generated embedding with {len(query_embedding)} dimensions")
            
            # Search Qdrant
            print("\nSearching Qdrant...")
            try:
                search_result = self.qdrant_client.search(
                    collection_name=self.qdrant_collection,
                    query_vector=query_embedding.tolist(),
                    limit=5
                )
                
                print(f"Found {len(search_result)} results in Qdrant")
                
                # Extract document IDs from search results
                doc_ids = []
                for i, result in enumerate(search_result):
                    print(f"\nResult {i+1}:")
                    print(f"  Score: {result.score:.4f}")
                    
                    if hasattr(result, 'payload') and 'doc_id' in result.payload:
                        doc_id = result.payload['doc_id']
                        doc_ids.append(doc_id)
                        print(f"  Document ID: {doc_id}")
                    
                    if hasattr(result, 'payload') and 'text' in result.payload:
                        text = result.payload['text']
                        if len(text) > 100:
                            text = text[:100] + "..."
                        print(f"  Text: {text}")
                
                # Use Neo4j to get document titles for the IDs
                if doc_ids and self.neo4j_driver:
                    print("\nFetching document details from Neo4j...")
                    with self.neo4j_driver.session() as session:
                        for doc_id in doc_ids:
                            result = session.run(
                                "MATCH (d:Document {id: $id}) RETURN d.title AS title", 
                                id=doc_id
                            )
                            record = result.single()
                            if record:
                                print(f"  Document ID {doc_id}: {record['title']}")
                            else:
                                print(f"  ❌ Document ID {doc_id} not found in Neo4j")
                
                return True
                
            except Exception as e:
                print(f"❌ Error searching Qdrant: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error in search test: {e}")
            return False
    
    def check_document_alignment(self):
        """Check if Neo4j documents and Qdrant vectors are aligned."""
        print("\n=== Checking Document Alignment ===")
        
        if not self.neo4j_driver or not self.qdrant_client:
            print("❌ Cannot check alignment: Not connected to both databases")
            return False
        
        try:
            # Get document IDs from Neo4j
            neo4j_doc_ids = set()
            with self.neo4j_driver.session() as session:
                result = session.run("MATCH (d:Document) RETURN d.id AS id")
                for record in result:
                    neo4j_doc_ids.add(record["id"])
            
            print(f"Found {len(neo4j_doc_ids)} document IDs in Neo4j")
            
            # Get document IDs from Qdrant
            qdrant_doc_ids = set()
            try:
                # Try to scroll through all vectors to extract unique document IDs
                limit = 1000
                offset = None
                total_processed = 0
                
                while True:
                    vectors, next_offset = self.qdrant_client.scroll(
                        collection_name=self.qdrant_collection,
                        limit=limit,
                        offset=offset
                    )
                    
                    if not vectors:
                        break
                    
                    for vector in vectors:
                        if hasattr(vector, 'payload') and 'doc_id' in vector.payload:
                            qdrant_doc_ids.add(vector.payload['doc_id'])
                    
                    total_processed += len(vectors)
                    print(f"Processed {total_processed} vectors from Qdrant...")
                    
                    if next_offset is None:
                        break
                    
                    offset = next_offset
            
                print(f"Found {len(qdrant_doc_ids)} unique document IDs in Qdrant vectors")
                
                # Check for misalignment
                neo4j_only = neo4j_doc_ids - qdrant_doc_ids
                qdrant_only = qdrant_doc_ids - neo4j_doc_ids
                
                if neo4j_only:
                    print(f"❌ {len(neo4j_only)} documents in Neo4j have no vectors in Qdrant")
                    print(f"Sample missing IDs: {list(neo4j_only)[:5]}")
                else:
                    print("✅ All Neo4j documents have vectors in Qdrant")
                
                if qdrant_only:
                    print(f"❌ {len(qdrant_only)} document IDs in Qdrant don't exist in Neo4j")
                    print(f"Sample extra IDs: {list(qdrant_only)[:5]}")
                else:
                    print("✅ All Qdrant document IDs exist in Neo4j")
                
                if not neo4j_only and not qdrant_only:
                    print("✅ Perfect alignment between Neo4j documents and Qdrant vectors!")
                    return True
                else:
                    print("⚠️ Databases are not fully aligned")
                    return False
                
            except Exception as e:
                print(f"❌ Error extracting Qdrant document IDs: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking document alignment: {e}")
            return False
    
    def close(self):
        """Close database connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            print("Neo4j connection closed")
        
        # Qdrant client doesn't need explicit closing

def main():
    checker = DatabaseChecker()
    
    # Connect to databases
    neo4j_docs, neo4j_chunks = checker.connect_to_neo4j()
    qdrant_vectors = checker.connect_to_qdrant()
    
    # Evaluate basic consistency
    if neo4j_docs is not None and qdrant_vectors is not None:
        if neo4j_chunks == qdrant_vectors:
            print(f"\n✅ CONSISTENT: Neo4j has {neo4j_chunks} chunks and Qdrant has {qdrant_vectors} vectors")
        else:
            print(f"\n⚠️ INCONSISTENT: Neo4j has {neo4j_chunks} chunks but Qdrant has {qdrant_vectors} vectors")
    
    # Load embedding model
    model_loaded = checker.load_model()
    
    # Test search functionality if model loaded
    if model_loaded:
        checker.test_search("how to connect to Neo4j")
    
    # Check document alignment
    checker.check_document_alignment()
    
    # Clean up
    checker.close()
    
    print("\n=== Database Check Complete ===")

if __name__ == "__main__":
    main() 