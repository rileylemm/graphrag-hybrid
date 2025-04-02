# GraphRAG Documentation Guides

This directory contains comprehensive documentation for the GraphRAG hybrid retrieval system that combines Neo4j for document relationships and Qdrant for vector similarity search.

## Available Guides

- [GraphRAG MCP Integration](mcp/index.md) - Guide for integrating with an external MCP server
- [Database Setup Guide](database_setup.md) - Instructions for setting up Neo4j and Qdrant databases

## Testing Documentation

- [Database Connection Testing](testing/index.md) - Details on connection verification and troubleshooting

## Key Topics Covered

- Neo4j and Qdrant database configuration with correct ports
  - Neo4j: HTTP on port 7475, Bolt on port 7688
  - Qdrant: HTTP on port 6335, gRPC on port 6334
- Document processing and embedding
- GraphRAG query patterns and optimization
- MCP integration API
- Troubleshooting and debugging

## Using These Guides

These guides are designed to be read in the following order:

1. Start with the [Database Setup Guide](database_setup.md) for initial configuration
2. Read the integration documents in the [MCP directory](mcp/index.md)
3. Check the [Testing Documentation](testing/index.md) if you encounter connection issues 