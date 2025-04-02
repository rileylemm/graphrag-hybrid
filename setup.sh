#!/bin/bash

# Setup script for the Neo4j and Qdrant GraphRAG project

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up the Neo4j and Qdrant GraphRAG environment...${NC}"

# Create Python virtual environment
echo -e "${BLUE}Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
else
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Activate the virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    cat > .env << EOL
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Qdrant Configuration  
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EOL
    echo -e "${GREEN}.env file created.${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo -e "To activate the virtual environment, run: ${BLUE}source venv/bin/activate${NC}"
echo -e "To start the databases, run: ${BLUE}docker-compose up -d${NC}" 