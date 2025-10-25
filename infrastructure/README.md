# Arbitrage Analysis App Infrastructure

This directory contains the Terraform configuration for the arbitrage analysis web application.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform installed
3. Domain `sndflo.com` already configured in Route53

## Setup Instructions

1. Initialize Terraform:
```bash
terraform init
```

2. Create a `terraform.tfvars` file with the database password:
```hcl
db_password = "your-secure-password-here"
```

3. Plan the deployment:
```bash
terraform plan
```

4. Apply the configuration:
```bash
terraform apply
```

## Architecture

- **S3**: Static website hosting for the React frontend
- **CloudFront**: CDN with no caching, restricted to North America
- **Route53**: DNS for arby.sndflo.com
- **Lambda**: Serverless CSV processing and AI analysis
- **RDS**: PostgreSQL database for storing manifests and results
- **API Gateway**: REST API for frontend-backend communication

## Components

### Frontend (S3 + CloudFront)
- React application for CSV upload and results display
- No caching enabled for real-time updates

### Backend (Lambda + RDS)
- CSV processing Lambda function
- PostgreSQL database for data persistence
- AI API integration for arbitrage analysis

### Infrastructure
- VPC with private subnets for RDS
- Security groups for database and Lambda access
- IAM roles and policies for secure access
