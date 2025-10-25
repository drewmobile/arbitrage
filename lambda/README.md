# Arbitrage Analysis Lambda Function

This Lambda function processes CSV manifests and performs AI-powered arbitrage analysis.

## Features

- **CSV Parsing**: Handles Grainger manifest CSV format
- **AI Analysis**: Analyzes each item for resale potential
- **Database Storage**: Saves results to PostgreSQL RDS
- **Chart Generation**: Creates data for frontend visualization
- **Error Handling**: Comprehensive error handling and logging

## Dependencies

- `psycopg2-binary`: PostgreSQL database adapter
- `boto3`: AWS SDK for Python
- `requests`: HTTP library for AI API calls

## Environment Variables

- `DB_HOST`: RDS endpoint
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password

## CSV Format Support

The function supports Grainger manifest CSV files with columns:
- Grainger item # / GRAINGER #
- title line / ITEM DESC.
- msrp - grainger / G $
- notes / NOTES
- pallet / PALLET #

## AI Analysis

Currently uses mock analysis based on item characteristics:
- **High Demand**: Compressors, vacuums, pressure washers
- **Medium Demand**: Motors, pumps, fans, cabinets
- **Low Demand**: Specialized equipment, custom enclosures

## Database Schema

- `manifests`: Store manifest metadata and summary
- `items`: Store individual item analysis results
- `manifest_summary`: View for aggregated statistics

## Deployment

1. Install dependencies:
```bash
pip install -r requirements.txt -t .
```

2. Create deployment package:
```bash
zip -r csv_processor.zip .
```

3. Upload to Lambda function

## Testing

The function can be tested with sample CSV data or actual Grainger manifests.
