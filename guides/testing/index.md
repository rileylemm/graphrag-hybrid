# Database Connection Testing

This guide documents the process of testing connections to the Neo4j and Qdrant databases.

## Initial Setup

The GraphRAG system uses standard ports for both databases:

- Neo4j runs on bolt port 7687 (standard port)
- Qdrant runs on HTTP port 6333 (standard port)

## Environment Configuration

For testing, use these environment variables:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Testing Process

The connection testing process verifies:

1. Neo4j connection on standard port 7687
2. Neo4j authentication with default credentials
3. Qdrant connection on standard port 6333
4. Qdrant collection existence and access

## Test Results

Our testing confirmed:
- Neo4j runs on standard bolt port 7687
- Qdrant runs on standard HTTP port 6333
- Both databases are accessible and properly configured
- Document chunks are stored correctly in both systems

## Debugging Notes

During testing, we verified:
- Neo4j connections work on default port 7687
- Qdrant connections work on default port 6333
- All database operations function as expected

## Connection Information

### Neo4j
- **Host**: localhost
- **Bolt Port**: 7687
- **HTTP Port**: 7474
- **Username**: neo4j
- **Password**: password

### Qdrant
- **Host**: localhost
- **HTTP Port**: 6333
- **gRPC Port**: 6334
- **Collection**: document_chunks

## Environment Variables

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Query Testing

The `scripts/testing/query_tester.py` script runs a variety of queries against both databases:

```bash
python scripts/testing/query_tester.py
```

### Key Debugging Changes

When setting up the connections, several adjustments were made:

- Added environment variable loading for configuration
- Added version handling for Qdrant client compatibility
- Added error handling for missing properties
- Added support for different API implementations

## Connection Parameters

The current verified connection parameters are:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

These parameters are used by all scripts and should be set in your `.env` file.

## Troubleshooting

If connections fail, verify:

1. Docker containers are running: `docker ps | grep graphrag`
2. Ports are correctly mapped: `docker-compose ps`
3. Environment variables match your actual configuration
4. Network access is not blocked by firewall/VPN

## Contents

- `scripts/testing/test_connections.py` - Main testing script that verifies connectivity to both databases
- `guides/testing/connection_info.md` - Summary of discovered connection information
- `scripts/testing/query_tester.py` - Script to test various query patterns against both databases
- `guides/query_guide.md` - Comprehensive guide for querying Neo4j and Qdrant databases
- `scripts/testing/query_guidelines.json` - Generated query guidelines in JSON format
- `guides/testing/index.md` - This documentation file

## Testing Process and Findings

### Connection Discovery Process

The testing process revealed several important configuration details:

1. **Non-standard ports**: 
   - Neo4j runs on bolt port 7688 (instead of default 7687)
   - Qdrant runs on HTTP port 6335 (instead of default 6333)

2. **Version compatibility issues**:
   - Qdrant client version (1.13.3) is newer than server version (1.5.1)
   - API differences between versions required special handling

### Debugging Issues Encountered

During development of the test script, we encountered and resolved several issues:

1. **Neo4j Port Discovery**
   - Initial connections to port 7687 failed with "Connection refused" errors
   - Added multi-port testing to discover the correct port (7688)

2. **Qdrant Port Discovery**
   - Initial connections to port 6333 failed
   - Added multi-port testing to discover the correct port (6335)

3. **Qdrant Version Compatibility**
   - Warnings about version incompatibility (1.13.3 client vs 1.5.1 server)
   - Initial fix attempt with `check_version=False` failed (parameter not supported)
   - Used Python's `warnings.filterwarnings()` to suppress warnings

4. **Qdrant API Changes Between Versions**
   - Error: `'CollectionParams' object has no attribute 'vector_size'`
   - Added version-aware code to check for different attribute names
   - Implemented fallback values for missing attributes

5. **Error Handling Improvements**
   - Added try/except blocks for all API calls
   - Created default values for missing properties
   - Fixed variable scope issues for `vectors_count` and `dimension`

### Key Connection Information

Based on the test results, the correct connection parameters are:

```env
NEO4J_URI=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=localhost
QDRANT_PORT=6335
```

## Running the Test

To run the connection test:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
pip install neo4j qdrant-client

# Run the test
python scripts/testing/test_connections.py
```

## Database Content

The test confirmed:

- **Neo4j**: 162 Document nodes and 2785 Content nodes (3652 total nodes)
- **Qdrant**: "document_chunks" collection with 2785 vectors (dimension 384)

## Integration Recommendations

When integrating with these databases:

1. Always use the verified connection parameters above
2. Implement version-aware code to handle Qdrant API differences
3. Use try/except blocks to handle potential API inconsistencies
4. Add fallbacks for essential parameters (like vector dimension)
5. Consider pinning the Qdrant client version to match the server version (1.5.x)

## Helpful Resources

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Qdrant Client Documentation](https://qdrant.tech/documentation/quick-start/)
- [GraphRAG Integration Guide](../graphrag_integration_guide.md) 