#!/bin/bash

# Deployment script for arbitrage analysis app
# This script deploys the entire application to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Arbitrage Analysis App${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed. Please install and configure it.${NC}"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform is not installed. Please install it.${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed. Please install it.${NC}"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install it.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"

# Set default values
REGION=${AWS_REGION:-"us-east-1"}
PROFILE=${AWS_PROFILE:-"default"}

echo -e "${YELLOW}Using AWS profile: $PROFILE${NC}"
echo -e "${YELLOW}Using AWS region: $REGION${NC}"

# Step 1: Deploy infrastructure
echo -e "${BLUE}📦 Step 1: Deploying infrastructure with Terraform...${NC}"
cd infrastructure

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}Creating terraform.tfvars file...${NC}"
    cat > terraform.tfvars << EOF
db_password = "$(openssl rand -base64 32)"
EOF
    echo -e "${GREEN}✅ Created terraform.tfvars with random password${NC}"
fi

# Plan deployment
echo -e "${YELLOW}Planning Terraform deployment...${NC}"
terraform plan -out=tfplan

# Apply deployment
echo -e "${YELLOW}Applying Terraform deployment...${NC}"
terraform apply tfplan

# Get outputs
API_GATEWAY_URL=$(terraform output -raw api_gateway_url)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain)
DB_ENDPOINT=$(terraform output -raw db_endpoint)

echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
echo -e "${GREEN}API Gateway URL: $API_GATEWAY_URL${NC}"
echo -e "${GREEN}CloudFront Domain: $CLOUDFRONT_DOMAIN${NC}"
echo -e "${GREEN}Database Endpoint: $DB_ENDPOINT${NC}"

cd ..

# Step 2: Deploy Lambda function
echo -e "${BLUE}🔧 Step 2: Deploying Lambda function...${NC}"
cd lambda

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install -r requirements.txt -t .

# Create deployment package
echo -e "${YELLOW}Creating Lambda deployment package...${NC}"
zip -r csv_processor.zip . -x "*.pyc" "__pycache__/*" "*.git*" "*.md" "requirements.txt"

# Update Lambda function
echo -e "${YELLOW}Updating Lambda function...${NC}"
aws lambda update-function-code \
    --function-name arbitrage-csv-processor \
    --zip-file fileb://csv_processor.zip \
    --profile $PROFILE \
    --region $REGION

# Update environment variables
echo -e "${YELLOW}Updating Lambda environment variables...${NC}"
aws lambda update-function-configuration \
    --function-name arbitrage-csv-processor \
    --environment Variables="{
        DB_HOST=$DB_ENDPOINT,
        DB_NAME=arbitrage,
        DB_USER=arbitrage_user,
        DB_PASSWORD=$(terraform -chdir=../infrastructure output -raw db_password),
        OPENAI_API_KEY=$(terraform -chdir=../infrastructure output -raw openai_api_key)
    }" \
    --profile $PROFILE \
    --region $REGION

echo -e "${GREEN}✅ Lambda function deployed successfully${NC}"
cd ..

# Step 3: Deploy frontend
echo -e "${BLUE}🌐 Step 3: Deploying frontend...${NC}"
cd frontend

# Install dependencies
echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
npm install

# Create environment file
echo -e "${YELLOW}Creating environment configuration...${NC}"
cat > .env.production << EOF
REACT_APP_API_URL=$API_GATEWAY_URL
EOF

# Build frontend
echo -e "${YELLOW}Building React application...${NC}"
npm run build

# Get S3 bucket name from Terraform
S3_BUCKET=$(terraform -chdir=../infrastructure output -raw s3_bucket_name)

# Upload to S3
echo -e "${YELLOW}Uploading frontend to S3...${NC}"
aws s3 sync build/ s3://$S3_BUCKET \
    --profile $PROFILE \
    --region $REGION \
    --delete

echo -e "${GREEN}✅ Frontend deployed successfully${NC}"
cd ..

# Step 4: Setup database
echo -e "${BLUE}🗄️ Step 4: Setting up database...${NC}"
cd database

# Set database environment variables
export DB_HOST=$DB_ENDPOINT
export DB_NAME="arbitrage"
export DB_USER="arbitrage_user"
export DB_PASSWORD=$(terraform -chdir=../infrastructure output -raw db_password)

# Run database setup
echo -e "${YELLOW}Running database setup...${NC}"
PGPASSWORD=$DB_PASSWORD ./setup.sh

echo -e "${GREEN}✅ Database setup completed${NC}"
cd ..

# Step 5: Invalidate CloudFront cache
echo -e "${BLUE}🔄 Step 5: Invalidating CloudFront cache...${NC}"
CLOUDFRONT_DISTRIBUTION_ID=$(terraform -chdir=infrastructure output -raw cloudfront_distribution_id)

aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
    --paths "/*" \
    --profile $PROFILE \
    --region $REGION

echo -e "${GREEN}✅ CloudFront cache invalidated${NC}"

# Final summary
echo -e "${BLUE}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}Your application is now available at: https://arby.sndflo.com${NC}"
echo -e "${GREEN}API Gateway URL: $API_GATEWAY_URL${NC}"
echo -e "${GREEN}Database Endpoint: $DB_ENDPOINT${NC}"

# Display next steps
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo -e "1. Configure your AI API key in Lambda environment variables"
echo -e "2. Test the application by uploading a CSV manifest"
echo -e "3. Monitor CloudWatch logs for any issues"
echo -e "4. Set up monitoring and alerting"

echo -e "${GREEN}🚀 Deployment complete!${NC}"
