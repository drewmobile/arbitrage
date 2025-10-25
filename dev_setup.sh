#!/bin/bash

# Development setup script for arbitrage analysis app
# This script sets up the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️ Setting up development environment...${NC}"

# Check if we're in the right directory
if [ ! -f "package.json" ] && [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Create main package.json if it doesn't exist
if [ ! -f "package.json" ]; then
    echo -e "${YELLOW}Creating main package.json...${NC}"
    cat > package.json << EOF
{
  "name": "arbitrage-analysis-app",
  "version": "1.0.0",
  "description": "AI-powered retail arbitrage analysis for industrial equipment manifests",
  "scripts": {
    "dev": "concurrently \"npm run dev:frontend\" \"npm run dev:lambda\"",
    "dev:frontend": "cd frontend && npm start",
    "dev:lambda": "cd lambda && python3 -m http.server 8001",
    "build": "cd frontend && npm run build",
    "deploy": "./deploy.sh",
    "test": "cd frontend && npm test",
    "lint": "cd frontend && npm run lint"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  },
  "keywords": ["arbitrage", "ai", "analysis", "industrial", "equipment"],
  "author": "Your Name",
  "license": "MIT"
}
EOF
fi

# Install main dependencies
echo -e "${YELLOW}Installing main dependencies...${NC}"
npm install

# Setup frontend
echo -e "${BLUE}🌐 Setting up frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Create development environment file
echo -e "${YELLOW}Creating development environment file...${NC}"
cat > .env.development << EOF
REACT_APP_API_URL=http://localhost:8001
EOF

cd ..

# Setup Lambda development environment
echo -e "${BLUE}🔧 Setting up Lambda development environment...${NC}"
cd lambda

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate
pip install -r requirements.txt
pip install flask  # For local development server

# Create development configuration
echo -e "${YELLOW}Creating development configuration...${NC}"
cat > dev_config.py << EOF
# Development configuration
import os

# Mock database configuration for development
DB_CONFIG = {
    'host': 'localhost',
    'database': 'arbitrage_dev',
    'user': 'postgres',
    'password': 'password',
    'port': 5432
}

# Mock environment variables
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'arbitrage_dev'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'password'
EOF

deactivate
cd ..

# Setup database development environment
echo -e "${BLUE}🗄️ Setting up database development environment...${NC}"
cd database

# Create development database setup script
echo -e "${YELLOW}Creating development database setup...${NC}"
cat > setup_dev.sh << 'EOF'
#!/bin/bash

# Development database setup
echo "Setting up development database..."

# Create development database
createdb arbitrage_dev 2>/dev/null || echo "Database arbitrage_dev already exists"

# Run schema
psql -d arbitrage_dev -f schema.sql

echo "Development database setup complete!"
EOF

chmod +x setup_dev.sh

cd ..

# Create development README
echo -e "${YELLOW}Creating development README...${NC}"
cat > DEV_README.md << EOF
# Development Setup

This document explains how to set up the development environment for the arbitrage analysis app.

## Prerequisites

- Node.js 16+
- Python 3.8+
- PostgreSQL 12+
- AWS CLI configured
- Terraform installed

## Quick Start

1. Run the development setup script:
\`\`\`bash
./dev_setup.sh
\`\`\`

2. Start the development servers:
\`\`\`bash
npm run dev
\`\`\`

This will start:
- Frontend development server on http://localhost:3000
- Lambda development server on http://localhost:8001

## Development Workflow

### Frontend Development
- Edit files in \`frontend/src/\`
- Hot reloading is enabled
- API calls are proxied to the Lambda development server

### Lambda Development
- Edit files in \`lambda/\`
- Use the virtual environment: \`source lambda/venv/bin/activate\`
- Test locally with the Flask development server

### Database Development
- Use the development database: \`arbitrage_dev\`
- Run migrations: \`cd database && ./setup_dev.sh\`

## Testing

### Frontend Tests
\`\`\`bash
npm test
\`\`\`

### Lambda Tests
\`\`\`bash
cd lambda
source venv/bin/activate
python -m pytest tests/
\`\`\`

## Deployment

To deploy to AWS:
\`\`\`bash
./deploy.sh
\`\`\`

## Troubleshooting

### Common Issues

1. **Port conflicts**: Make sure ports 3000 and 8001 are available
2. **Database connection**: Ensure PostgreSQL is running and accessible
3. **AWS credentials**: Verify AWS CLI configuration
4. **Python dependencies**: Use the virtual environment for Lambda development

### Logs

- Frontend logs: Check browser console
- Lambda logs: Check terminal output
- Database logs: Check PostgreSQL logs

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally
4. Submit a pull request

## Environment Variables

### Development
- \`REACT_APP_API_URL\`: Frontend API endpoint
- \`DB_HOST\`: Database host
- \`DB_NAME\`: Database name
- \`DB_USER\`: Database user
- \`DB_PASSWORD\`: Database password

### Production
- Set via Terraform and Lambda environment variables
- Use AWS Systems Manager Parameter Store for sensitive values
EOF

# Create .gitignore
echo -e "${YELLOW}Creating .gitignore...${NC}"
cat > .gitignore << EOF
# Dependencies
node_modules/
*/node_modules/
venv/
*/venv/

# Build outputs
build/
dist/
*.zip

# Environment files
.env
.env.local
.env.development
.env.production
*.tfvars

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# AWS
.aws/

# Terraform
*.tfstate
*.tfstate.backup
.terraform/
.terraform.lock.hcl

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
pip-log.txt
pip-delete-this-directory.txt

# Coverage reports
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
.hypothesis/
.pytest_cache/
EOF

# Final summary
echo -e "${GREEN}✅ Development environment setup complete!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "1. Start development servers: \`npm run dev\`"
echo -e "2. Open http://localhost:3000 in your browser"
echo -e "3. Set up your local PostgreSQL database"
echo -e "4. Configure your AI API key for testing"
echo -e "5. Start developing!"

echo -e "${GREEN}🛠️ Development setup complete!${NC}"
