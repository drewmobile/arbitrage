# Database Setup and Management

This directory contains database setup scripts and schema for the arbitrage analysis application.

## Files

- `schema.sql`: PostgreSQL database schema with tables, indexes, and sample data
- `setup.sh`: Automated database setup script
- `README.md`: This documentation

## Database Schema

### Tables

#### `manifests`
Stores manifest metadata and summary statistics:
- `id`: Unique manifest identifier
- `created_at`: Timestamp when manifest was processed
- `total_items`: Number of items in the manifest
- `total_msrp`: Total MSRP value of all items
- `projected_revenue`: Estimated total revenue from sales
- `profit_margin`: Overall profit margin percentage

#### `items`
Stores individual item analysis results:
- `id`: Auto-incrementing primary key
- `manifest_id`: Foreign key to manifests table
- `item_number`: Grainger item number/SKU
- `title`: Item description
- `msrp`: Manufacturer's suggested retail price
- `estimated_sale_price`: AI-estimated sale price
- `profit`: Calculated profit (sale price - MSRP)
- `demand`: Market demand level (High/Medium/Low)
- `sales_time`: Estimated time to sell
- `reasoning`: AI reasoning for the analysis

### Views

#### `manifest_summary`
Aggregated view providing summary statistics for each manifest:
- Basic manifest information
- Actual item counts
- Average item profit
- Demand level breakdown

### Functions and Triggers

- `update_updated_at_column()`: Automatically updates the `updated_at` timestamp
- Trigger on `manifests` table to maintain `updated_at` field

## Setup Instructions

### Prerequisites

1. PostgreSQL 12+ installed
2. Database user with appropriate permissions
3. Environment variables set:
   - `DB_HOST`: Database host
   - `DB_PORT`: Database port (default: 5432)
   - `DB_NAME`: Database name
   - `DB_USER`: Database username

### Automated Setup

```bash
# Set environment variables
export DB_HOST="your-rds-endpoint.amazonaws.com"
export DB_NAME="arbitrage"
export DB_USER="arbitrage_user"

# Run setup script
./setup.sh
```

### Manual Setup

```bash
# Create database
createdb -h $DB_HOST -U $DB_USER $DB_NAME

# Run schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
```

## Sample Data

The schema includes sample data for testing:
- 1 sample manifest with 3 items
- Various demand levels and profit margins
- Realistic pricing data

## Performance Considerations

### Indexes
- `idx_items_manifest_id`: Fast lookups by manifest
- `idx_items_item_number`: Fast lookups by item number
- `idx_manifests_created_at`: Efficient date-based queries

### Query Optimization
- Use the `manifest_summary` view for aggregated data
- Leverage indexes for common query patterns
- Consider partitioning for large datasets

## Maintenance

### Regular Tasks
- Monitor database size and performance
- Update statistics: `ANALYZE;`
- Check for long-running queries
- Backup regularly

### Scaling Considerations
- Consider read replicas for heavy read workloads
- Implement connection pooling
- Monitor RDS performance metrics
- Set up automated backups

## Security

### Best Practices
- Use parameterized queries (prevent SQL injection)
- Limit database user permissions
- Enable SSL connections
- Regular security updates
- Monitor access logs

### RDS Security
- Use VPC security groups
- Enable encryption at rest
- Enable encryption in transit
- Use IAM database authentication
- Regular security group reviews

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check security group settings
   - Verify endpoint and port
   - Confirm user permissions

2. **Performance Issues**
   - Check query execution plans
   - Review index usage
   - Monitor connection counts

3. **Schema Errors**
   - Verify PostgreSQL version compatibility
   - Check for conflicting objects
   - Review error logs

### Monitoring

- RDS CloudWatch metrics
- Database connection monitoring
- Query performance analysis
- Error log review
