# GraphRAG Scripts

This directory contains scripts for setting up, importing documents into, and querying the GraphRAG system.

## Main Scripts

- `import_docs.py` - Main script for importing documentation into Neo4j and Qdrant
- `query_demo.py` - Demonstrates how to query the hybrid database
- `setup_databases.py` - Sets up the Neo4j and Qdrant databases
- `setup_neo4j_schema.py` - Creates the Neo4j database schema
- `setup_qdrant_collection.py` - Creates the Qdrant collection
- `verify_db_structure.py` - Verifies the database structure is correct

## Usage Examples

### Setting up the system:
```bash
# Initialize both databases with required schemas/collections
python scripts/setup_databases.py
```

### Importing documentation:
```bash
# Import documents from the your_docs_here directory
python scripts/import_docs.py --docs-dir ./your_docs_here
```

### Querying the system:
```bash
# Run an interactive query demo
python scripts/query_demo.py
```

## Testing Scripts

The `testing/` subdirectory contains additional scripts for testing database connections and functionality:

- `test_connections.py` - Tests connections to both databases
- `query_tester.py` - Tests various query functionality and generates guidelines
- `check_db.py` - Quick check of Neo4j database 
- `check_qdrant.py` - Quick check of Qdrant database

## Important Notes

- All scripts expect the `.env` file to be properly configured
- Some scripts may require additional arguments; run with `--help` for details
- Always run scripts from the project root directory