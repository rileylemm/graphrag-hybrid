# Database Connection Testing

This directory contains scripts for testing connections to the Neo4j and Qdrant databases that power the GraphRAG system.

## Connection Details

Database connections:

**Neo4j**
- HTTP Port: 7474
- Bolt Port: 7687
- Authentication: neo4j/password

**Qdrant**
- HTTP Port: 6333
- Collection: document_chunks

## Test Scripts

- `test_connections.py` - Tests connections to both Neo4j and Qdrant databases

## Running Tests

To verify database connections:

```bash
# Activate virtual environment if needed
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the test script
python test_db_connection/test_connections.py
```

## Expected Output

When successful, the test script will:

1. Connect to Neo4j on port 7687
2. Run a simple query to verify connection
3. Count nodes in the Neo4j database
4. Connect to Qdrant on port 6333
5. Verify the Qdrant service health
6. List available collections
7. Display information about the document_chunks collection

## Troubleshooting

If connection tests fail:

1. Verify that both Neo4j and Qdrant containers are running:
   ```bash
   docker ps | grep graphrag
   ```

2. Check if the ports are correctly mapped in docker-compose.yml:
   ```bash
   cat docker-compose.yml | grep -E "7474|7687|6333"
   ```

3. Verify that the .env file has the correct connection information:
   ```bash
   cat .env | grep -E "NEO4J|QDRANT"
   ```

4. Ensure that no other service is using the required ports:
   ```bash
   lsof -i :7474 -i :7687 -i :6333
   ``` 