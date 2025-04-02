# Your Documentation Directory

This directory is where you add your markdown documents to be processed and imported into the GraphRAG hybrid retrieval system. Any `.md` files placed here will be processed, embedded, and stored in both Neo4j and Qdrant databases.

## How to Use This Directory

1. **Add Your Documents**: Place your markdown (`.md`) files in this directory
2. **Run the Import Script**: Execute `python scripts/import_docs.py --docs-dir your_docs_here/`
3. **Query Your Content**: Once imported, you can query your content through the GraphRAG system

## Document Format Requirements

For optimal results, your documents should follow this structure:

### Front Matter Format (Required)

Include YAML front matter at the beginning of your documents with these fields:

```yaml
---
title: "Document Title"          # The title of your document (required)
category: "path/to/category"     # Category path for organization (required)
updated: "YYYY-MM-DD"            # Last updated date (optional)
related:                         # Related documents (optional)
  - path/to/related1.md
  - path/to/related2.md
key_concepts:                    # Key concepts for indexing (optional)
  - concept_one
  - concept_two
---
```

### Document Structure

- Start with a single `# Title` (H1) heading after the front matter
- Use proper heading hierarchy (`##`, `###`, etc.)
- Include code blocks with language identifiers
- Use lists, tables, and other markdown features as needed
- Link to related documents where appropriate

## Example Document

See the included `analytics_example.md` file for a comprehensive example of the recommended document format.

## Importing Documents

To import your documents into the GraphRAG system:

```bash
# Import all documents from this directory
python scripts/import_docs.py --docs-dir your_docs_here/

# Or import specific documents
python scripts/import_docs.py --files your_docs_here/file1.md your_docs_here/file2.md

# To reimport (clear and rebuild)
python scripts/import_docs.py --docs-dir your_docs_here/ --clear
```

## Processing Details

When you run the import script, the system will:

1. Parse each markdown file and extract front matter metadata
2. Split the content into manageable chunks
3. Generate vector embeddings for each chunk
4. Store document structure and relationships in Neo4j
5. Store vector embeddings in Qdrant
6. Create connections between related documents

## Notes

- Place your actual documentation files in this directory
- Remove the example documents before adding your own content if desired
- The system works best with well-structured, content-rich markdown files 