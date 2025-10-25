# Arbitrage Analysis Platform

A serverless web application for analyzing liquidation manifests and determining retail arbitrage potential using AI-powered analysis and marketplace integration.

## Overview

This platform allows users to upload CSV manifests from liquidation companies and receive AI-powered analysis of each item's resale potential, including estimated sale prices, profit margins, demand levels, and marketplace availability on Amazon and eBay.

## Architecture

### Frontend
- **React.js** application hosted on S3
- **CloudFront** distribution for global content delivery
- **Custom domain**: `arby.sndflo.com`
- Features:
  - File upload and CSV text paste functionality
  - Interactive results table with sorting and filtering
  - Image thumbnails with modal popups
  - Real-time analysis progress tracking

### Backend
- **AWS Lambda** functions for serverless processing
- **API Gateway** for REST API endpoints
- **PostgreSQL RDS** database for data persistence
- **S3** for file storage and image hosting
- **AWS Secrets Manager** for secure credential storage

### AI & Marketplace Integration
- **OpenAI GPT-4** for intelligent item analysis
- **Amazon Product Advertising API (PAAPI)** for Amazon marketplace data
- **eBay API** for eBay marketplace data
- **Image search and processing** using Pillow

## Key Features

### 1. Universal CSV Parser
- Supports multiple liquidation company formats:
  - Grainger manifests
  - Liquidation.com format
  - Wayfair liquidation
  - Staples liquidation
  - DirectLiquidation
  - Department store formats
  - Electronics liquidation
  - Costco liquidation
  - Generic product manifests

### 2. AI-Powered Analysis
- Intelligent item categorization and demand assessment
- Realistic liquidation pricing (15-50% of MSRP)
- Sales time estimation based on item characteristics
- Profit margin calculations based on liquidation purchase costs

### 3. Marketplace Integration
- Amazon product availability and pricing
- eBay product availability and pricing
- Concurrent API calls for performance optimization
- Fallback handling for API failures

### 4. Image Processing
- Automatic product image search
- S3 storage with CloudFront URLs
- Thumbnail generation and display
- Clickable image modals

### 5. Data Visualization
- Revenue timeline charts
- Category breakdown analysis
- Profit margin summaries
- Interactive results tables

## Technical Implementation

### Infrastructure (Terraform)
- **S3 buckets** for static hosting and file storage
- **CloudFront** distribution with no caching for real-time updates
- **Route53** DNS management for custom domain
- **ACM** SSL certificate for HTTPS
- **RDS PostgreSQL** database
- **Lambda functions** with appropriate IAM roles
- **API Gateway** with CORS configuration

### Lambda Functions
- **csv_processor**: Main analysis function
  - CSV parsing and format detection
  - AI analysis integration
  - Marketplace lookups
  - Image processing
  - Database operations
- **csv_uploader**: File upload handler
- **Dependencies**: psycopg2, xmltodict, python-amazon-paapi, Pillow

### Database Schema
- **manifests**: Analysis metadata and summaries
- **items**: Individual item analysis
- **Foreign key relationships** with automatic updates

### Security
- API credentials stored in AWS Secrets Manager
- IAM roles with least privilege access
- CORS configuration for secure cross-origin requests
- Environment variables for sensitive data

## Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform installed
- Node.js and npm for frontend development

### Infrastructure Deployment
```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

### Lambda Deployment
```bash
cd lambda
./deploy.sh
```

### Frontend Deployment
```bash
cd frontend
npm run build
aws s3 sync build/ s3://arby-sndflo-com --delete
```

## Usage

1. **Upload Manifest**: Users can either upload a CSV file or paste CSV data directly
2. **AI Analysis**: The system analyzes each item using OpenAI GPT-4
3. **Marketplace Lookup**: Concurrent searches on Amazon and eBay
4. **Results Display**: Interactive table with analysis results, images, and charts
5. **Data Persistence**: Results are saved to the database for future reference

## Performance Optimizations

- **Concurrent API calls** for marketplace lookups
- **Timeout handling** to prevent long-running operations
- **Result caching** with hash-based deduplication
- **Lambda memory optimization** (512MB)
- **CloudFront caching disabled** for real-time updates

## Error Handling

- **Graceful degradation** when APIs are unavailable
- **Comprehensive logging** for debugging
- **Fallback analysis** using mock data when needed
- **CORS error resolution** with proper headers

## Current Status

### ✅ Completed Features
- Universal CSV parsing for multiple formats
- AI-powered analysis with realistic pricing
- Amazon and eBay marketplace integration
- Image search and processing
- Frontend with interactive results
- Database persistence
- CORS configuration
- Profit margin calculations

### 🔧 Known Issues
- **Amazon PAAPI**: Credentials need verification for full functionality
- **eBay API**: Integration needs testing
- **Image Processing**: Pillow dependency issues in Lambda
- **Profit Calculations**: Recently fixed unrealistic margins

### 📋 Future Enhancements
- Enhanced marketplace API reliability
- Additional liquidation company formats
- Advanced filtering and search capabilities
- Bulk analysis features
- Export functionality for results

## API Endpoints

- `POST /prod/upload` - Upload and analyze CSV manifests
- `GET /prod/results/{manifestId}` - Retrieve saved analysis results

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key for AI analysis
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
- `EBAY_APP_ID` - eBay API application ID
- AWS Secrets Manager for Amazon PAAPI credentials

## Monitoring

- CloudWatch logs for Lambda functions
- API Gateway request/response logging
- Database query performance monitoring
- Error tracking and alerting

## Cost Optimization

- Serverless architecture minimizes costs
- Lambda functions scale automatically
- S3 storage with lifecycle policies
- CloudFront for global content delivery
- RDS with appropriate instance sizing

---

**Last Updated**: October 25, 2025
**Version**: 1.0.0
**Status**: Production Ready (with known limitations)