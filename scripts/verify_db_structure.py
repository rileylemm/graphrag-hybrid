#!/usr/bin/env python3
"""
Script to verify that the Neo4j and Qdrant database structures
match the documented structure in guides/mcp/document_structure.md
"""

import os
import sys
import json
import warnings
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Load environment variables
load_dotenv()

# Terminal colors for better readability
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"

# Connection parameters
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "document_chunks")

def test_neo4j_structure():
    """Test Neo4j database structure against documented schema"""
    print(f"\n{BOLD}Testing Neo4j Database Structure...{ENDC}\n")
    
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            # 1. Verify node types/labels
            print("Checking node labels...")
            result = session.run("""
                CALL db.labels() YIELD label
                RETURN collect(label) AS labels
            """)
            labels = result.single()["labels"]
            
            expected_labels = ["Document", "Content", "Topic", "Category"]
            for label in expected_labels:
                if label in labels:
                    print(f"{GREEN}✓ Found node label: {label}{ENDC}")
                else:
                    print(f"{RED}✗ Missing node label: {label}{ENDC}")
            
            # 2. Verify relationship types
            print("\nChecking relationship types...")
            result = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN collect(relationshipType) AS relationships
            """)
            relationships = result.single()["relationships"]
            
            expected_relationships = ["CONTAINS", "NEXT", "HAS_TOPIC", "IN_CATEGORY", "RELATED_TO"]
            for rel in expected_relationships:
                if rel in relationships:
                    print(f"{GREEN}✓ Found relationship type: {rel}{ENDC}")
                else:
                    print(f"{RED}✗ Missing relationship type: {rel}{ENDC}")
            
            # 3. Check document structure (sample)
            print("\nChecking document structure...")
            result = session.run("""
                MATCH (d:Document) 
                RETURN d.id, d.title, d.category, d.path, d.author, d.date
                LIMIT 1
            """)
            
            doc = result.single()
            if doc:
                print(f"{GREEN}✓ Found document:{ENDC}")
                for key, value in doc.items():
                    if value:
                        print(f"  {key}: {value}")
            else:
                print(f"{RED}✗ No documents found in the database{ENDC}")
            
            # 4. Check content chunks structure (sample)
            print("\nChecking content chunks structure...")
            result = session.run("""
                MATCH (c:Content) 
                RETURN c.id, c.text
                LIMIT 1
            """)
            
            content = result.single()
            if content:
                print(f"{GREEN}✓ Found content chunk:{ENDC}")
                for key, value in content.items():
                    if key == 'text':
                        print(f"  {key}: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"{RED}✗ No content chunks found in the database{ENDC}")
            
            # 5. Verify the relationship between documents and chunks
            print("\nVerifying document-chunk relationships...")
            result = session.run("""
                MATCH (d:Document)-[r:CONTAINS]->(c:Content)
                RETURN COUNT(r) as containsCount
            """)
            
            contains_count = result.single()["containsCount"]
            print(f"{GREEN}✓ Found {contains_count} CONTAINS relationships{ENDC}")
            
            # 6. Verify the NEXT relationships between chunks
            print("\nVerifying content chunk ordering (NEXT relationships)...")
            result = session.run("""
                MATCH (c1:Content)-[r:NEXT]->(c2:Content)
                RETURN COUNT(r) as nextCount
            """)
            
            next_count = result.single()["nextCount"]
            print(f"{GREEN}✓ Found {next_count} NEXT relationships{ENDC}")
            
            # 7. Count documents by category
            print("\nCounting documents by category...")
            result = session.run("""
                MATCH (d:Document)
                RETURN d.category, COUNT(d) AS count
                ORDER BY count DESC
            """)
            
            for record in result:
                category = record["d.category"]
                count = record["count"]
                print(f"  Category '{category}': {count} documents")
                
    except Exception as e:
        print(f"{RED}Error connecting to Neo4j: {str(e)}{ENDC}")
        return False
    finally:
        if 'driver' in locals():
            driver.close()
            
    return True

def test_qdrant_structure():
    """Test Qdrant database structure against documented schema"""
    print(f"\n{BOLD}Testing Qdrant Database Structure...{ENDC}\n")
    
    try:
        # Suppress warnings about client version
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            
            # Connect to Qdrant
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            
            # 1. Check if the collection exists
            print("Checking collection existence...")
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if QDRANT_COLLECTION in collection_names:
                print(f"{GREEN}✓ Found collection: {QDRANT_COLLECTION}{ENDC}")
                
                # 2. Check collection info and vector dimension
                collection_info = client.get_collection(QDRANT_COLLECTION)
                
                # Try different property paths based on version
                vector_size = None
                try:
                    vector_size = collection_info.config.params.vectors.size
                except:
                    try:
                        vector_size = collection_info.config.params.vector_size
                    except:
                        pass
                
                if vector_size:
                    print(f"{GREEN}✓ Vector dimension: {vector_size}{ENDC}")
                    if vector_size == 384:
                        print(f"{GREEN}✓ Vector dimension matches documented value (384){ENDC}")
                    else:
                        print(f"{YELLOW}⚠ Vector dimension ({vector_size}) doesn't match documented value (384){ENDC}")
                else:
                    print(f"{YELLOW}⚠ Could not determine vector dimension{ENDC}")
                
                # 3. Check distance metric
                distance_type = None
                try:
                    distance_type = collection_info.config.params.vectors.distance
                except:
                    try:
                        distance_type = collection_info.config.params.distance
                    except:
                        pass
                
                if distance_type:
                    print(f"{GREEN}✓ Distance type: {distance_type}{ENDC}")
                    if "cosine" in str(distance_type).lower():
                        print(f"{GREEN}✓ Distance type matches documented value (Cosine){ENDC}")
                    else:
                        print(f"{YELLOW}⚠ Distance type ({distance_type}) doesn't match documented value (Cosine){ENDC}")
                else:
                    print(f"{YELLOW}⚠ Could not determine distance type{ENDC}")
                
                # 4. Get vector count
                vector_count = None
                try:
                    vector_count = collection_info.vectors_count
                except:
                    try:
                        vector_count = collection_info.vectors_count()
                    except:
                        pass
                
                if vector_count:
                    print(f"{GREEN}✓ Collection contains {vector_count} vectors{ENDC}")
                else:
                    print(f"{YELLOW}⚠ Could not determine vector count{ENDC}")
                
                # 5. Check payload structure by retrieving a sample
                print("\nChecking vector payload structure...")
                
                # Load embedding model to search for a sample
                model = SentenceTransformer("all-MiniLM-L6-v2")
                query_vector = model.encode("test query").tolist()
                
                # Search for a sample vector
                try:
                    search_result = client.search(
                        collection_name=QDRANT_COLLECTION,
                        query_vector=query_vector,
                        limit=1
                    )
                    
                    if search_result:
                        print(f"{GREEN}✓ Successfully retrieved a sample vector{ENDC}")
                        
                        # Check payload structure
                        sample = search_result[0]
                        payload = sample.payload
                        
                        print("\nPayload structure:")
                        if "text" in payload:
                            print(f"{GREEN}✓ Found 'text' field{ENDC}")
                            print(f"  text: {payload['text'][:100]}...")
                        else:
                            print(f"{RED}✗ Missing 'text' field{ENDC}")
                        
                        if "metadata" in payload:
                            print(f"{GREEN}✓ Found 'metadata' field{ENDC}")
                            metadata = payload["metadata"]
                            
                            # Check expected metadata fields
                            expected_fields = [
                                "doc_id", "chunk_id", "title", "category", "file_path"
                            ]
                            
                            for field in expected_fields:
                                if field in metadata:
                                    print(f"{GREEN}✓ Found metadata field: {field}{ENDC}")
                                    if field != "file_path":  # Skip long paths
                                        print(f"  {field}: {metadata[field]}")
                                else:
                                    print(f"{RED}✗ Missing metadata field: {field}{ENDC}")
                        else:
                            print(f"{RED}✗ Missing 'metadata' field{ENDC}")
                    else:
                        print(f"{YELLOW}⚠ No vectors found in the collection{ENDC}")
                        
                except Exception as e:
                    print(f"{RED}Error searching Qdrant: {str(e)}{ENDC}")
            else:
                print(f"{RED}✗ Collection '{QDRANT_COLLECTION}' not found{ENDC}")
                print(f"Available collections: {', '.join(collection_names)}")
                return False
                
    except Exception as e:
        print(f"{RED}Error connecting to Qdrant: {str(e)}{ENDC}")
        return False
            
    return True

def verify_document_alignment():
    """Verify that Neo4j and Qdrant are aligned (same documents and chunks)"""
    print(f"\n{BOLD}Verifying Neo4j and Qdrant Alignment...{ENDC}\n")
    
    try:
        # Connect to Neo4j
        neo4j_driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        # Connect to Qdrant
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # 1. Get total document count from Neo4j
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (d:Document)
                RETURN COUNT(d) as docCount
            """)
            neo4j_doc_count = result.single()["docCount"]
            
            # 2. Get total chunk count from Neo4j
            result = session.run("""
                MATCH (c:Content)
                RETURN COUNT(c) as chunkCount
            """)
            neo4j_chunk_count = result.single()["chunkCount"]
            
            # 3. Get chunk IDs from Neo4j (sample)
            result = session.run("""
                MATCH (c:Content)
                RETURN c.id as chunkId
                LIMIT 5
            """)
            neo4j_chunk_ids = [record["chunkId"] for record in result]
        
        # 4. Get vector count from Qdrant
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        vector_count = None
        try:
            vector_count = collection_info.vectors_count
        except:
            try:
                vector_count = collection_info.vectors_count()
            except:
                pass
        
        # 5. Check if the counts match
        print(f"Neo4j document count: {neo4j_doc_count}")
        print(f"Neo4j content chunk count: {neo4j_chunk_count}")
        print(f"Qdrant vector count: {vector_count}")
        
        if vector_count == neo4j_chunk_count:
            print(f"{GREEN}✓ Neo4j chunk count matches Qdrant vector count{ENDC}")
        else:
            print(f"{YELLOW}⚠ Neo4j chunk count ({neo4j_chunk_count}) doesn't match Qdrant vector count ({vector_count}){ENDC}")
        
        # 6. Verify sample chunk IDs exist in Qdrant
        print("\nChecking sample chunk IDs between Neo4j and Qdrant...")
        
        for chunk_id in neo4j_chunk_ids:
            try:
                # Check if the point exists in Qdrant
                point = qdrant_client.retrieve(
                    collection_name=QDRANT_COLLECTION,
                    ids=[chunk_id]
                )
                if point:
                    print(f"{GREEN}✓ Chunk ID {chunk_id} exists in both Neo4j and Qdrant{ENDC}")
                else:
                    print(f"{RED}✗ Chunk ID {chunk_id} exists in Neo4j but not in Qdrant{ENDC}")
            except Exception as e:
                print(f"{RED}Error checking chunk ID {chunk_id} in Qdrant: {str(e)}{ENDC}")
                
    except Exception as e:
        print(f"{RED}Error verifying alignment: {str(e)}{ENDC}")
        return False
    finally:
        if 'neo4j_driver' in locals():
            neo4j_driver.close()
            
    return True

def main():
    """Main function to verify database structures"""
    print(f"{BOLD}Database Structure Verification Tool{ENDC}")
    print(f"Verifying against documented structure in guides/mcp/document_structure.md")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Connection parameters:")
    print(f"  Neo4j URI: {NEO4J_URI}")
    print(f"  Qdrant Host: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"  Qdrant Collection: {QDRANT_COLLECTION}")
    
    # Run tests
    neo4j_success = test_neo4j_structure()
    qdrant_success = test_qdrant_structure()
    
    if neo4j_success and qdrant_success:
        verify_document_alignment()
    
    # Summary
    print(f"\n{BOLD}Verification Summary{ENDC}")
    print(f"Neo4j Structure: {'✓ Verified' if neo4j_success else '✗ Issues detected'}")
    print(f"Qdrant Structure: {'✓ Verified' if qdrant_success else '✗ Issues detected'}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Generate recommendations if issues were found
    if not (neo4j_success and qdrant_success):
        print(f"\n{BOLD}Recommendations:{ENDC}")
        if not neo4j_success:
            print("1. Check Neo4j connection parameters (URI, username, password)")
            print("2. Verify Neo4j is running and accessible")
            print("3. Review Neo4j schema and ensure it matches the documented structure")
        if not qdrant_success:
            print("1. Check Qdrant connection parameters (host, port, collection name)")
            print("2. Verify Qdrant is running and accessible")
            print("3. Review collection configuration and ensure it matches the documented structure")
    
if __name__ == "__main__":
    main() 