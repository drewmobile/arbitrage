import json
import csv
import io
import boto3
import requests
import re
import os
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# Database connection parameters
DB_CONFIG = {
    'host': None,  # Will be set from environment
    'database': None,  # Will be set from environment
    'user': None,  # Will be set from environment
    'password': None,  # Will be set from environment
    'port': 5432
}

def get_db_connection():
    """Get database connection (temporarily disabled for testing)"""
    # Temporarily disabled for testing
    return None

def parse_grainger_csv(csv_content):
    """Parse Grainger manifest CSV format"""
    items = []
    
    try:
        # Use StringIO to read CSV content
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            # Skip empty rows
            if not row.get('Grainger item #') or not row.get('title line'):
                continue
                
            # Extract and clean MSRP
            msrp_str = row.get('msrp - grainger', '0').replace('$', '').replace(',', '').strip()
            try:
                msrp = float(msrp_str) if msrp_str else 0.0
            except ValueError:
                msrp = 0.0
            
            # Only include items with valid MSRP
            if msrp > 0:
                item = {
                    'item_number': row.get('Grainger item #', '').strip(),
                    'title': row.get('title line', '').strip(),
                    'msrp': msrp,
                    'notes': row.get('notes', '').strip() if row.get('notes') else None,
                    'pallet': row.get('pallet', '').strip() if row.get('pallet') else None
                }
                items.append(item)
                
    except Exception as e:
        logger.error(f"CSV parsing error: {str(e)}")
        
    return items

def lambda_handler(event, context):
    """Main Lambda handler for S3-based CSV processing"""
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Max-Age': '86400'
    }
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS preflight successful'})
        }
    
    try:
        # Set database config from environment
        db_host = os.environ['DB_HOST']
        if ':' in db_host:
            host, port = db_host.split(':')
            DB_CONFIG['host'] = host
            DB_CONFIG['port'] = int(port)
        else:
            DB_CONFIG['host'] = db_host
        DB_CONFIG['database'] = os.environ['DB_NAME']
        DB_CONFIG['user'] = os.environ['DB_USER']
        DB_CONFIG['password'] = os.environ['DB_PASSWORD']
        
        # Parse the request body
        if 'body' in event:
            # Handle API Gateway event
            body = event['body']
            if event.get('isBase64Encoded', False):
                import base64
                body = base64.b64decode(body).decode('utf-8')
            
            # Parse JSON body
            try:
                body_data = json.loads(body)
                file_content = body_data.get('file', '')
                filename = body_data.get('filename', 'unknown.csv')
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Invalid JSON body'})
                }
        else:
            # Handle direct S3 event
            file_content = ""
            filename = "unknown.csv"
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Generate unique upload ID
        upload_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Upload CSV to S3
        s3_key = f"uploads/{upload_id}/{filename}"
        s3_bucket = os.environ.get('S3_UPLOADS_BUCKET', 'arby-csv-uploads')
        
        try:
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=file_content.encode('utf-8'),
                ContentType='text/csv'
            )
            logger.info(f"Uploaded CSV to S3: s3://{s3_bucket}/{s3_key}")
        except Exception as e:
            logger.error(f"S3 upload error: {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Failed to upload to S3', 'details': str(e)})
            }
        
        # Parse CSV to get item count
        items = parse_grainger_csv(file_content)
        
        if not items:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No valid items found in CSV'})
            }
        
        # Store upload record in database
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO uploads (id, filename, s3_key, status, total_items)
                    VALUES (%s, %s, %s, %s, %s)
                """, (upload_id, filename, s3_key, 'uploaded', len(items)))
                conn.commit()
                cursor.close()
                conn.close()
                logger.info(f"Stored upload record: {upload_id}")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            # Continue processing even if database fails
        
        # Return upload ID for frontend to poll
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'uploadId': upload_id,
                'status': 'uploaded',
                'totalItems': len(items),
                'message': 'CSV uploaded successfully. Processing will begin shortly.'
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }
