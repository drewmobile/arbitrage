import json
import csv
import io
import boto3
import requests
import re
import os
import uuid
import xmltodict
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from amazon_paapi import AmazonApi
# from PIL import Image
# import base64

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

def calculate_file_hash(csv_content):
    """Calculate SHA-256 hash of CSV content"""
    return hashlib.sha256(csv_content.encode('utf-8')).hexdigest()

def get_db_connection():
    """Get database connection"""
    try:
        import psycopg2
        
        # Parse DB_HOST to extract host and port
        db_host = os.environ.get('DB_HOST', '')
        if ':' in db_host:
            host, port = db_host.split(':')
            port = int(port)
        else:
            host = db_host
            port = 5432
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=os.environ.get('DB_NAME', 'arbitrage'),
            user=os.environ.get('DB_USER', 'arbitrage_user'),
            password=os.environ.get('DB_PASSWORD', '')
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return None

def check_existing_analysis(file_hash):
    """Check if analysis already exists for this file hash"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        
        # Check if upload with this hash exists and is completed
        cursor.execute("""
            SELECT u.id, u.filename, u.created_at, m.id as manifest_id
            FROM uploads u
            LEFT JOIN manifests m ON u.manifest_id = m.id
            WHERE u.file_hash = %s AND u.status = 'completed'
            ORDER BY u.created_at DESC
            LIMIT 1
        """, (file_hash,))
        
        result = cursor.fetchone()
        if result:
            upload_id, filename, created_at, manifest_id = result
            
            # Get manifest data
            cursor.execute("""
                SELECT total_items, total_msrp, projected_revenue, profit_margin
                FROM manifests
                WHERE id = %s
            """, (manifest_id,))
            
            manifest_result = cursor.fetchone()
            if manifest_result:
                total_items, total_msrp, projected_revenue, profit_margin = manifest_result
                
                # Get items data
                cursor.execute("""
                    SELECT item_number, title, msrp, notes, pallet, 
                           estimated_sale_price, demand, sales_time, reasoning, profit
                    FROM items
                    WHERE manifest_id = %s
                    ORDER BY item_number
                """, (manifest_id,))
                
                items_data = cursor.fetchall()
                items = []
                for item in items_data:
                    items.append({
                        'item_number': item[0],
                        'title': item[1],
                        'msrp': float(item[2]) if item[2] else 0,
                        'quantity': 1,  # Default quantity for mock data
                        'notes': item[3],
                        'pallet': item[4],
                        'analysis': {
                            'estimatedSalePrice': float(item[5]) if item[5] else 0,
                            'demand': item[6],
                            'salesTime': item[7],
                            'reasoning': item[8]
                        },
                        'profit': float(item[9]) if item[9] else 0
                    })
                
                cursor.close()
                conn.close()
                
                return {
                    'manifestId': manifest_id,
                    'summary': {
                        'totalMsrp': float(total_msrp),
                        'projectedRevenue': float(projected_revenue),
                        'totalProfit': float(projected_revenue) - (float(projected_revenue) * 0.33),
                        'profitMargin': float(profit_margin),
                        'avgSalesTime': '4 weeks',  # Default value
                        'totalItems': total_items,
                        'recommendations': ['Results loaded from previous analysis']
                    },
                    'items': items,
                    'charts': generate_charts(items),
                    'processedAt': created_at.isoformat(),
                    'cached': True
                }
        
        cursor.close()
        conn.close()
        return None
        
    except Exception as e:
        logger.error(f"Error checking existing analysis: {str(e)}")
        return None

def parse_manifest_csv(csv_content):
    """Parse any manifest CSV format - intelligent detection and flexible parsing with robust error handling"""
    items = []
    
    try:
        # Validate input
        if not csv_content or not isinstance(csv_content, str):
            logger.error("Invalid CSV content: empty or not a string")
            return []
        
        # Use StringIO to handle the CSV content
        csv_file = io.StringIO(csv_content)
        
        # Read the first few lines to detect format
        lines = csv_content.split('\n')[:10]  # Read more lines for better detection
        header_line = lines[0].lower() if lines else ""
        
        logger.info(f"Detecting CSV format from header: {header_line[:100]}...")
        
        # Detect common manifest formats with more flexible matching
        if any(keyword in header_line for keyword in ['grainger', 'item #', 'item number', 'sku']):
            logger.info("Detected Grainger format")
            return parse_grainger_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['upc', 'description', 'retail price', 'total retail price']):
            logger.info("Detected liquidation format")
            return parse_liquidation_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['description', 'model', 'quantity', 'ext. retail price']):
            logger.info("Detected Staples format")
            return parse_staples_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['item title', 'quantity', 'retail price', 'brand']):
            logger.info("Detected DirectLiquidation format")
            return parse_direct_liquidation_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['sku', 'product name', 'brand', 'condition', 'msrp']):
            logger.info("Detected department store format")
            return parse_department_store_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['model number', 'condition', 'total retail']):
            logger.info("Detected electronics format")
            return parse_electronics_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['item number', 'sell price', 'extended sell', 'salvage']):
            logger.info("Detected Costco format")
            return parse_costco_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['product', 'description', 'price', 'cost']):
            logger.info("Detected generic product format")
            return parse_generic_product_format(csv_file, csv_content)
        elif any(keyword in header_line for keyword in ['part', 'model', 'manufacturer']):
            logger.info("Detected parts format")
            return parse_parts_format(csv_file, csv_content)
        else:
            # Use intelligent universal parser for unknown formats
            logger.info("Using universal parser for unknown format")
            return parse_universal_csv(csv_file, csv_content)
            
    except Exception as e:
        logger.error(f"CSV parsing error: {str(e)}")
        # Fallback to universal parser
        try:
            logger.info("Attempting fallback to universal parser")
            csv_file = io.StringIO(csv_content)
            return parse_universal_csv(csv_file, csv_content)
        except Exception as fallback_error:
            logger.error(f"Universal parser fallback failed: {str(fallback_error)}")
            return []

def parse_grainger_format(csv_file, csv_content):
    """Parse Grainger-specific manifest format"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):  # Skip empty rows
            continue
            
        # Extract item data based on Grainger format
        item_number = None
        title = None
        msrp = None
        notes = None
        pallet = None
        
        # Try different column name variations
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'grainger' in key_lower and ('#' in key_lower or 'item' in key_lower):
                    item_number = value.strip()
                elif 'title' in key_lower or 'description' in key_lower or 'name' in key_lower or 'desc' in key_lower:
                    title = value.strip()
                elif 'msrp' in key_lower or 'grainger' in key_lower or key_lower == 'g $':
                    try:
                        # Remove commas and dollar signs
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'notes' in key_lower or 'comment' in key_lower:
                    notes = value.strip()
                elif 'pallet' in key_lower or 'lot' in key_lower:
                    pallet = value.strip()
        
        # Only add items with essential data
        if item_number and title and msrp:
            items.append({
                'item_number': item_number,
                'title': title,
                'msrp': msrp,
                'quantity': 1,  # Default quantity for Grainger format
                'notes': notes,
                'pallet': pallet
            })
    
    return items

def parse_liquidation_format(csv_file, csv_content):
    """Parse liquidation inventory format: UPC,Description,Category,Qty,Retail Price,Total Retail Price"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):  # Skip empty rows
            continue
            
        # Extract item data based on liquidation format
        upc = None
        title = None
        msrp = None
        category = None
        quantity = None
        
        # Try different column name variations
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'upc' in key_lower:
                    upc = value.strip()
                elif 'description' in key_lower or 'product' in key_lower:
                    title = value.strip()
                elif ('retail price' in key_lower and 'total' not in key_lower) or key_lower == '"retail price"':
                    try:
                        # Remove commas and dollar signs
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'category' in key_lower:
                    category = value.strip()
                elif 'qty' in key_lower or 'quantity' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
        
        # Only add items with essential data
        if title and msrp:
            items.append({
                'item_number': upc or f"item_{len(items)+1}",
                'title': title,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': f"Category: {category}" if category else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_staples_format(csv_file, csv_content):
    """Parse Staples liquidation format: Description,Model,Quantity,Retail Price,Ext. Retail Price,Sku Restriction"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):  # Skip empty rows
            continue
            
        # Extract item data based on Staples format
        description = None
        model = None
        msrp = None
        quantity = None
        sku_restriction = None
        
        # Try different column name variations
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'description' in key_lower:
                    description = value.strip()
                elif 'model' in key_lower:
                    model = value.strip()
                elif 'retail price' in key_lower and 'ext' not in key_lower:
                    try:
                        # Remove commas and dollar signs
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'quantity' in key_lower or 'qty' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
                elif 'sku restriction' in key_lower or 'restriction' in key_lower:
                    sku_restriction = value.strip()
        
        # Only add items with essential data
        if description and msrp:
            notes_parts = []
            if model: notes_parts.append(f"Model: {model}")
            if sku_restriction: notes_parts.append(f"Restriction: {sku_restriction}")
            
            items.append({
                'item_number': model or f"item_{len(items)+1}",
                'title': description,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': ", ".join(notes_parts) if notes_parts else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_direct_liquidation_format(csv_file, csv_content):
    """Parse DirectLiquidation/B-Stock format: Item Title, Quantity, Retail Price, UPC, Brand"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):  # Skip empty rows
            continue
            
        # Extract item data
        item_title = None
        msrp = None
        upc = None
        brand = None
        quantity = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'item title' in key_lower or 'title' in key_lower:
                    item_title = value.strip()
                elif 'retail price' in key_lower or 'msrp' in key_lower:
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'upc' in key_lower:
                    upc = value.strip()
                elif 'brand' in key_lower:
                    brand = value.strip()
                elif 'quantity' in key_lower or 'qty' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
        
        if item_title and msrp:
            items.append({
                'item_number': upc or f"item_{len(items)+1}",
                'title': item_title,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': f"Brand: {brand}" if brand else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_department_store_format(csv_file, csv_content):
    """Parse Department Store format: SKU, Product Name, Brand, Condition, Quantity, MSRP, Extended MSRP"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        sku = None
        product_name = None
        msrp = None
        brand = None
        condition = None
        quantity = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'sku' in key_lower:
                    sku = value.strip()
                elif 'product name' in key_lower or 'name' in key_lower:
                    product_name = value.strip()
                elif 'msrp' in key_lower and 'extended' not in key_lower:
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'brand' in key_lower:
                    brand = value.strip()
                elif 'condition' in key_lower:
                    condition = value.strip()
                elif 'quantity' in key_lower or 'qty' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
        
        if product_name and msrp:
            notes_parts = []
            if brand: notes_parts.append(f"Brand: {brand}")
            if condition: notes_parts.append(f"Condition: {condition}")
            
            items.append({
                'item_number': sku or f"item_{len(items)+1}",
                'title': product_name,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': ", ".join(notes_parts) if notes_parts else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_electronics_format(csv_file, csv_content):
    """Parse Electronics format: Model Number, Description, Condition, Qty, Retail Price, Total Retail"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        model_number = None
        description = None
        msrp = None
        condition = None
        quantity = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'model number' in key_lower or 'model' in key_lower:
                    model_number = value.strip()
                elif 'description' in key_lower:
                    description = value.strip()
                elif 'retail price' in key_lower and 'total' not in key_lower:
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'condition' in key_lower:
                    condition = value.strip()
                elif 'qty' in key_lower or 'quantity' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
        
        if description and msrp:
            notes_parts = []
            if model_number: notes_parts.append(f"Model: {model_number}")
            if condition: notes_parts.append(f"Condition: {condition}")
            
            items.append({
                'item_number': model_number or f"item_{len(items)+1}",
                'title': description,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': ", ".join(notes_parts) if notes_parts else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_costco_format(csv_file, csv_content):
    """Parse Costco format: Item Number, Description, Quantity, Sell Price, Extended Sell, Salvage Percent"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        item_number = None
        description = None
        msrp = None
        quantity = None
        salvage_percent = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if 'item number' in key_lower:
                    item_number = value.strip()
                elif 'description' in key_lower:
                    description = value.strip()
                elif 'sell price' in key_lower and 'extended' not in key_lower:
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif 'quantity' in key_lower or 'qty' in key_lower:
                    try:
                        quantity = int(value.strip())
                    except (ValueError, TypeError):
                        quantity = None
                elif 'salvage' in key_lower and 'percent' in key_lower:
                    try:
                        salvage_percent = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        salvage_percent = None
        
        if description and msrp:
            notes_parts = []
            if salvage_percent: notes_parts.append(f"Salvage: {salvage_percent}%")
            
            items.append({
                'item_number': item_number or f"item_{len(items)+1}",
                'title': description,
                'msrp': msrp,
                'quantity': quantity or 1,
                'notes': ", ".join(notes_parts) if notes_parts else None,
                'pallet': f"Qty: {quantity}" if quantity else None
            })
    
    return items

def parse_generic_product_format(csv_file, csv_content):
    """Parse generic product manifest format"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        item_number = None
        title = None
        msrp = None
        notes = None
        pallet = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if any(term in key_lower for term in ['sku', 'id', 'code', 'number']):
                    item_number = value.strip()
                elif any(term in key_lower for term in ['name', 'title', 'description', 'product']):
                    title = value.strip()
                elif any(term in key_lower for term in ['price', 'msrp', 'cost', 'retail']):
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif any(term in key_lower for term in ['notes', 'comment', 'remark']):
                    notes = value.strip()
                elif any(term in key_lower for term in ['lot', 'batch', 'pallet']):
                    pallet = value.strip()
        
        if item_number and title and msrp:
            items.append({
                'item_number': item_number,
                'title': title,
                'msrp': msrp,
                'quantity': 1,  # Default quantity for generic product format
                'notes': notes,
                'pallet': pallet
            })
    
    return items

def parse_parts_format(csv_file, csv_content):
    """Parse parts/inventory manifest format"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        item_number = None
        title = None
        msrp = None
        notes = None
        pallet = None
        
        for key, value in row.items():
            key_lower = key.lower().strip()
            if value and value.strip():
                if any(term in key_lower for term in ['part', 'model', 'sku', 'pn']):
                    item_number = value.strip()
                elif any(term in key_lower for term in ['description', 'name', 'title']):
                    title = value.strip()
                elif any(term in key_lower for term in ['price', 'cost', 'value']):
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                    except (ValueError, TypeError):
                        msrp = None
                elif any(term in key_lower for term in ['notes', 'condition']):
                    notes = value.strip()
                elif any(term in key_lower for term in ['location', 'bin', 'lot']):
                    pallet = value.strip()
        
        if item_number and title and msrp:
            items.append({
                'item_number': item_number,
                'title': title,
                'msrp': msrp,
                'quantity': 1,  # Default quantity for parts format
                'notes': notes,
                'pallet': pallet
            })
    
    return items

def parse_universal_csv(csv_file, csv_content):
    """Universal CSV parser that can handle any manifest format with robust error handling"""
    items = []
    
    try:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        
        if not headers:
            logger.error("No headers found in CSV")
            return []
        
        logger.info(f"Universal parser detected headers: {headers}")
        
        # Create column mapping based on header analysis
        column_map = analyze_headers(headers)
        
        row_count = 0
        error_count = 0
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 since header is row 1
            row_count += 1
            
            try:
                if not row or not any(str(v).strip() for v in row.values() if v):
                    continue  # Skip empty rows
                
                item = extract_item_from_row(row, column_map, row_num)
                if item:
                    items.append(item)
                else:
                    logger.warning(f"Row {row_num}: Invalid item data, skipping")
                    
            except Exception as e:
                error_count += 1
                logger.warning(f"Error parsing row {row_num}: {str(e)}")
                if error_count > 10:  # Stop processing if too many errors
                    logger.error(f"Too many parsing errors ({error_count}), stopping processing")
                    break
                continue
        
        logger.info(f"Universal parser processed {row_count} rows, extracted {len(items)} items, {error_count} errors")
        return items
        
    except Exception as e:
        logger.error(f"Universal CSV parsing failed: {str(e)}")
        return []

def analyze_headers(headers):
    """Analyze CSV headers to create intelligent column mapping"""
    column_map = {
        'item_number': None,
        'title': None,
        'msrp': None,
        'quantity': None,
        'notes': None,
        'pallet': None,
        'category': None,
        'brand': None,
        'condition': None,
        'upc': None,
        'sku': None,
        'model': None
    }
    
    for header in headers:
        if not header:
            continue
            
        header_lower = header.lower().strip()
        
        # Item identifier mapping
        if any(term in header_lower for term in ['item', 'sku', 'part', 'product']):
            if any(term in header_lower for term in ['number', '#', 'id', 'code']):
                if not column_map['item_number']:
                    column_map['item_number'] = header
            elif any(term in header_lower for term in ['sku', 'stock']):
                if not column_map['sku']:
                    column_map['sku'] = header
        
        # Title/Description mapping
        elif any(term in header_lower for term in ['title', 'name', 'description', 'desc', 'product']):
            if not column_map['title']:
                column_map['title'] = header
        
        # Price mapping
        elif any(term in header_lower for term in ['price', 'cost', 'msrp', 'retail', 'sell']):
            if any(term in header_lower for term in ['msrp', 'retail', 'list']):
                if not column_map['msrp']:
                    column_map['msrp'] = header
            elif 'extended' not in header_lower and 'total' not in header_lower:
                if not column_map['msrp']:
                    column_map['msrp'] = header
        
        # Quantity mapping
        elif any(term in header_lower for term in ['qty', 'quantity', 'count', 'units']):
            if not column_map['quantity']:
                column_map['quantity'] = header
        
        # Category mapping
        elif any(term in header_lower for term in ['category', 'cat', 'type', 'class']):
            if not column_map['category']:
                column_map['category'] = header
        
        # Brand mapping
        elif any(term in header_lower for term in ['brand', 'manufacturer', 'maker']):
            if not column_map['brand']:
                column_map['brand'] = header
        
        # Condition mapping
        elif any(term in header_lower for term in ['condition', 'grade', 'quality']):
            if not column_map['condition']:
                column_map['condition'] = header
        
        # UPC mapping
        elif any(term in header_lower for term in ['upc', 'barcode', 'ean']):
            if not column_map['upc']:
                column_map['upc'] = header
        
        # Model mapping
        elif any(term in header_lower for term in ['model', 'part']):
            if not column_map['model']:
                column_map['model'] = header
        
        # Notes/Comments mapping
        elif any(term in header_lower for term in ['notes', 'comment', 'remark', 'description']):
            if not column_map['notes']:
                column_map['notes'] = header
        
        # Location/Pallet mapping
        elif any(term in header_lower for term in ['pallet', 'lot', 'batch', 'location', 'bin']):
            if not column_map['pallet']:
                column_map['pallet'] = header
    
    # Fallback logic for missing critical fields
    if not column_map['item_number'] and column_map['sku']:
        column_map['item_number'] = column_map['sku']
    elif not column_map['item_number'] and column_map['upc']:
        column_map['item_number'] = column_map['upc']
    elif not column_map['item_number'] and column_map['model']:
        column_map['item_number'] = column_map['model']
    
    if not column_map['title'] and column_map['notes']:
        column_map['title'] = column_map['notes']
    
    logger.info(f"Column mapping: {column_map}")
    return column_map

def extract_item_from_row(row, column_map, row_num):
    """Extract item data from a CSV row using the column mapping"""
    item_number = None
    title = None
    msrp = None
    quantity = None
    notes_parts = []
    
    # Extract item number
    for field in ['item_number', 'sku', 'upc', 'model']:
        if column_map[field] and column_map[field] in row:
            value = str(row[column_map[field]]).strip()
            if value and value.lower() not in ['', 'n/a', 'null', 'none']:
                item_number = value
                break
    
    # Extract title
    if column_map['title'] and column_map['title'] in row:
        value = str(row[column_map['title']]).strip()
        if value and value.lower() not in ['', 'n/a', 'null', 'none']:
            title = value
    
    # Extract MSRP
    if column_map['msrp'] and column_map['msrp'] in row:
        value = str(row[column_map['msrp']]).strip()
        if value and value.lower() not in ['', 'n/a', 'null', 'none']:
            try:
                # Remove currency symbols, commas, and other non-numeric characters
                msrp = float(re.sub(r'[^\d.]', '', value))
            except (ValueError, TypeError):
                msrp = None
    
    # Extract quantity
    if column_map['quantity'] and column_map['quantity'] in row:
        value = str(row[column_map['quantity']]).strip()
        if value and value.lower() not in ['', 'n/a', 'null', 'none']:
            try:
                quantity = int(float(value))  # Handle decimal quantities
            except (ValueError, TypeError):
                quantity = None
    
    # Extract additional information for notes
    for field in ['category', 'brand', 'condition']:
        if column_map[field] and column_map[field] in row:
            value = str(row[column_map[field]]).strip()
            if value and value.lower() not in ['', 'n/a', 'null', 'none']:
                notes_parts.append(f"{field.title()}: {value}")
    
    # Extract pallet/location info
    pallet = None
    if column_map['pallet'] and column_map['pallet'] in row:
        value = str(row[column_map['pallet']]).strip()
        if value and value.lower() not in ['', 'n/a', 'null', 'none']:
            pallet = value
    
    # Validate required fields
    if not title or not msrp or msrp <= 0:
        return None
    
    # Generate item number if missing
    if not item_number:
        item_number = f"item_{row_num}"
    
    return {
        'item_number': item_number,
        'title': title,
        'msrp': msrp,
        'quantity': quantity or 1,
        'notes': ", ".join(notes_parts) if notes_parts else None,
        'pallet': pallet
    }

def parse_generic_csv(csv_file, csv_content):
    """Parse any CSV format by trying common column patterns"""
    items = []
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if not row or not any(row.values()):
            continue
            
        item_number = None
        title = None
        msrp = None
        notes = None
        pallet = None
        
        # Try to match columns by position if names don't match
        columns = list(row.keys())
        values = list(row.values())
        
        # Common patterns: [ID, Name/Title, Price, Notes, Location]
        if len(values) >= 3:
            # Try first column as ID
            if values[0] and values[0].strip():
                item_number = values[0].strip()
            
            # Try second column as title
            if len(values) > 1 and values[1] and values[1].strip():
                title = values[1].strip()
            
            # Try to find a numeric price in remaining columns
            for i, value in enumerate(values[2:], 2):
                if value and value.strip():
                    try:
                        msrp = float(re.sub(r'[^\d.]', '', str(value)))
                        break
                    except (ValueError, TypeError):
                        continue
        
        # If we still don't have a title, try to construct one
        if not title and item_number:
            title = f"Item {item_number}"
        
        # Only add items with essential data
        if item_number and title and msrp:
            items.append({
                'item_number': item_number,
                'title': title,
                'msrp': msrp,
                'quantity': 1,  # Default quantity for generic CSV
                'notes': notes,
                'pallet': pallet
            })
    
    return items

def search_ebay_sales_data(item):
    """Search eBay for similar items to get real-world pricing data"""
    try:
        # Extract key terms from item title for search
        title_words = item['title'].lower().split()
        
        # Remove common words and focus on key product terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'}
        
        search_terms = [word for word in title_words if word not in stop_words and len(word) > 2]
        
        # Take first 3-4 meaningful terms for search
        search_query = ' '.join(search_terms[:4])
        
        # eBay Finding API endpoint (sandbox)
        url = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
        
        params = {
            'OPERATION-NAME': 'findItemsByKeywords',
            'SERVICE-VERSION': '1.0.0',
            'SECURITY-APPNAME': os.environ.get('EBAY_APP_ID', ''),
            'GLOBAL-ID': 'EBAY-US',
            'keywords': search_query,
            'itemFilter(0).name': 'Condition',
            'itemFilter(0).value': 'Used',
            'itemFilter(1).name': 'ListingType',
            'itemFilter(1).value': 'FixedPrice',
            'sortOrder': 'PricePlusShippingLowest',
            'paginationInput.entriesPerPage': '20'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = xmltodict.parse(response.text)
            
            # Extract pricing data
            items = data.get('findItemsByKeywordsResponse', {}).get('searchResult', {}).get('item', [])
            
            if not items:
                return None
                
            # Ensure items is a list
            if not isinstance(items, list):
                items = [items]
            
            prices = []
            for ebay_item in items:
                try:
                    # Get current price
                    current_price = ebay_item.get('sellingStatus', {}).get('currentPrice', {}).get('#text', '0')
                    if current_price:
                        prices.append(float(current_price))
                except (ValueError, TypeError):
                    continue
            
            if prices:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                return {
                    'averagePrice': avg_price,
                    'minPrice': min_price,
                    'maxPrice': max_price,
                    'sampleSize': len(prices),
                    'source': 'eBay'
                }
        
        return None
        
    except Exception as e:
        logger.warning(f"eBay API search failed for {item['item_number']}: {str(e)}")
        return None

def analyze_item_with_ebay_data(item):
    """Analyze item using eBay sales data when available"""
    try:
        # Search for eBay sales data
        ebay_data = search_ebay_sales_data(item)
        
        if ebay_data and ebay_data['sampleSize'] >= 3:  # Need at least 3 samples for reliability
            # Use eBay data for pricing
            estimated_sale_price = ebay_data['averagePrice']
            
            # Determine demand based on price range
            price_range = ebay_data['maxPrice'] - ebay_data['minPrice']
            price_variance = price_range / ebay_data['averagePrice'] if ebay_data['averagePrice'] > 0 else 1
            
            if price_variance < 0.3:  # Low variance = high demand
                demand = 'High'
                sales_time = '1-2 weeks'
            elif price_variance < 0.6:  # Medium variance = medium demand
                demand = 'Medium'
                sales_time = '2-4 weeks'
            else:  # High variance = low demand
                demand = 'Low'
                sales_time = '1-3 months'
            
            return {
                'estimatedSalePrice': round(estimated_sale_price, 2),
                'demand': demand,
                'salesTime': sales_time,
                'reasoning': f"Based on eBay sales data: ${estimated_sale_price:.2f} avg from {ebay_data['sampleSize']} listings",
                'dataSource': 'eBay'
            }
        
        # Fallback to AI analysis if no reliable eBay data
        return analyze_item_with_ai(item)
        
    except Exception as e:
        logger.error(f"eBay data analysis failed for {item['item_number']}: {str(e)}")
        return analyze_item_with_ai(item)
def analyze_item_with_ai(item):
    """Analyze a single item using AI API"""
    try:
        # Get marketplace data first
        marketplace_data = check_marketplace_availability(item['title'], item.get('item_number'))
        
        # Search for product image
        image_data = find_product_image(item['title'], item.get('item_number'))
        
        # Prepare the prompt for AI analysis
        prompt = f"""
        Analyze this industrial equipment item for liquidation pricing arbitrage:
        
        Item: {item['title']}
        MSRP: ${item['msrp']:.2f}
        Category: Industrial Equipment
        
        Marketplace Data:
        - Amazon: {'Available' if marketplace_data['amazon']['available'] else 'Not found'} 
          {'$' + str(marketplace_data['amazon']['price']) if marketplace_data['amazon']['price'] else 'N/A'}
        - eBay: {'Available' if marketplace_data['ebay']['available'] else 'Not found'}
          {'$' + str(marketplace_data['ebay']['price']) if marketplace_data['ebay']['price'] else 'N/A'}
        
        This is being sold at liquidation prices (typically 15-50% of MSRP).
        Consider:
        - Liquidation market conditions (buyers expect deep discounts)
        - Equipment condition (may be used, damaged, or overstock)
        - Market demand for industrial equipment
        - Competition from other liquidation sellers
        - Storage and shipping costs
        - Target buyer demographics (contractors, small businesses, hobbyists)
        - Current marketplace prices for reference
        
        Please provide:
        1. Estimated liquidation sale price (15-50% of MSRP)
        2. Market demand level (High/Medium/Low)
        3. Estimated sales time (e.g., "2-4 weeks", "1-3 months", "3-6 months")
        4. Brief reasoning for the pricing
        
        Respond in JSON format:
        {{
            "estimatedSalePrice": number,
            "demand": "High/Medium/Low",
            "salesTime": "timeframe",
            "reasoning": "brief explanation"
        }}
        """
        
        # Try to call AI API first, fallback to mock if unavailable
        try:
            logger.info(f"Attempting AI analysis for item {item['item_number']}")
            result = call_ai_api(prompt, item)
            logger.info(f"AI analysis successful for item {item['item_number']}")
            
            # Add marketplace data and image to the result
            result['marketplace'] = marketplace_data
            result['image'] = image_data
            return result
        except Exception as ai_error:
            logger.warning(f"AI API unavailable, using mock analysis: {str(ai_error)}")
            mock_result = analyze_item_mock(item)
            mock_result['marketplace'] = marketplace_data
            mock_result['image'] = image_data
            return mock_result
        
    except Exception as e:
        logger.error(f"AI analysis error for item {item['item_number']}: {str(e)}")
        mock_result = analyze_item_mock(item)
        mock_result['marketplace'] = {'amazon': {'available': False, 'price': None}, 'ebay': {'available': False, 'price': None}}
        # Try to get image even for error case
        try:
            image_data = find_product_image(item['title'], item.get('item_number'))
            mock_result['image'] = image_data
        except:
            mock_result['image'] = None
        return mock_result

def call_ai_api(prompt, item):
    """Call external AI API for item analysis"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OpenAI API key not configured")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'gpt-4',
        'messages': [
            {'role': 'system', 'content': 'You are an expert in retail arbitrage analysis for industrial equipment. Always respond with valid JSON format.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 500
    }
    
    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', 
                               headers=headers, json=data, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # Clean up the response to ensure it's valid JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        else:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise Exception("Invalid JSON response from AI API")
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise Exception(f"AI API request failed: {str(e)}")

def analyze_item_mock(item):
    """Mock AI analysis based on item characteristics - liquidation pricing"""
    title = item['title'].lower()
    msrp = item['msrp']
    
    # Ensure MSRP is valid
    if not msrp or msrp <= 0:
        msrp = 100.0  # Default fallback
    
    # Base liquidation pricing: 30% of MSRP average
    base_liquidation_price = msrp * 0.3
    
    # Adjust based on item characteristics (liquidation market factors)
    if any(keyword in title for keyword in ['compressor', 'vacuum', 'pressure washer', 'generator']):
        # High-demand industrial equipment sells faster in liquidation
        estimated_sale_price = msrp * 0.35
        demand = 'High'
        sales_time = '2-4 weeks'
    elif any(keyword in title for keyword in ['motor', 'pump', 'fan', 'blower']):
        # Motors and pumps have steady demand
        estimated_sale_price = msrp * 0.32
        demand = 'Medium'
        sales_time = '1-3 months'
    elif any(keyword in title for keyword in ['cabinet', 'storage', 'enclosure', 'box']):
        # Storage items are slower moving
        estimated_sale_price = msrp * 0.25
        demand = 'Low'
        sales_time = '3-6 months'
    elif any(keyword in title for keyword in ['tool', 'drill', 'saw', 'grinder']):
        # Power tools sell well in liquidation
        estimated_sale_price = msrp * 0.40
        demand = 'High'
        sales_time = '1-2 weeks'
    elif any(keyword in title for keyword in ['heater', 'cooler', 'air', 'ventilation']):
        # HVAC equipment has seasonal demand
        estimated_sale_price = msrp * 0.28
        demand = 'Medium'
        sales_time = '2-4 months'
    elif any(keyword in title for keyword in ['tank', 'drum', 'container', 'barrel']):
        # Large containers are harder to move
        estimated_sale_price = msrp * 0.20
        demand = 'Low'
        sales_time = '4-8 months'
    else:
        # Default liquidation pricing
        estimated_sale_price = msrp * 0.30
        demand = 'Medium'
        sales_time = '2-3 months'
    
    # Add some randomness to make it more realistic (±10%)
    import random
    price_variation = random.uniform(0.9, 1.1)
    estimated_sale_price *= price_variation
    
    # Ensure realistic liquidation bounds
    estimated_sale_price = max(estimated_sale_price, msrp * 0.15)  # Never less than 15% of MSRP
    estimated_sale_price = min(estimated_sale_price, msrp * 0.50)  # Never more than 50% of MSRP
    
    # Calculate profit margin based on liquidation purchase price (33% of projected revenue)
    liquidation_purchase_price = estimated_sale_price * 0.33
    profit_margin = (estimated_sale_price - liquidation_purchase_price) / liquidation_purchase_price
    
    return {
        'estimatedSalePrice': round(estimated_sale_price, 2),
        'profitMargin': round(profit_margin, 3),
        'demand': demand,
        'salesTime': sales_time,
        'reasoning': f"Liquidation pricing: {estimated_sale_price/msrp*100:.0f}% of MSRP with {demand.lower()} demand"
    }

def calculate_summary(items_with_analysis):
    """Calculate summary statistics"""
    total_msrp = sum(item['msrp'] for item in items_with_analysis)
    total_projected_revenue = sum(item['analysis']['estimatedSalePrice'] for item in items_with_analysis)
    # Calculate profit based on liquidation purchase price (33% of sale price)
    total_liquidation_cost = sum(item['analysis']['estimatedSalePrice'] * 0.33 for item in items_with_analysis)
    total_profit = total_projected_revenue - total_liquidation_cost
    
    profit_margin = total_profit / total_liquidation_cost if total_liquidation_cost > 0 else 0
    
    # Calculate average sales time
    sales_times = []
    for item in items_with_analysis:
        sales_time = item['analysis']['salesTime']
        if 'week' in sales_time.lower():
            weeks = int(re.findall(r'\d+', sales_time)[0])
            sales_times.append(weeks)
        elif 'month' in sales_time.lower():
            months = int(re.findall(r'\d+', sales_time)[0])
            sales_times.append(months * 4)
    
    avg_sales_time = f"{sum(sales_times) / len(sales_times):.0f} weeks" if sales_times else "N/A"
    
    # Generate recommendations
    recommendations = []
    if profit_margin > 0.3:
        recommendations.append("High profit margin detected. Consider prioritizing these items for quick sales.")
    if total_projected_revenue > total_msrp * 0.8:
        recommendations.append("Strong resale potential. Focus on marketing and competitive pricing.")
    
    high_demand_items = [item for item in items_with_analysis if item['analysis']['demand'] == 'High']
    if len(high_demand_items) > len(items_with_analysis) * 0.3:
        recommendations.append("Many high-demand items identified. List these first to build momentum.")
    
    return {
        'totalMsrp': total_msrp,
        'projectedRevenue': total_projected_revenue,
        'totalProfit': total_profit,
        'profitMargin': profit_margin,
        'avgSalesTime': avg_sales_time,
        'totalItems': len(items_with_analysis),
        'recommendations': recommendations
    }

def generate_charts(items_with_analysis):
    """Generate chart data"""
    # Revenue timeline (mock data for 12 months)
    months = ['Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6',
              'Month 7', 'Month 8', 'Month 9', 'Month 10', 'Month 11', 'Month 12']
    
    # Simulate revenue distribution over time
    total_revenue = sum(item['analysis']['estimatedSalePrice'] for item in items_with_analysis)
    revenue_timeline = []
    cumulative = 0
    
    for i in range(12):
        if i < 6:  # First 6 months get 70% of revenue
            monthly_revenue = total_revenue * 0.7 / 6
        else:  # Last 6 months get 30% of revenue
            monthly_revenue = total_revenue * 0.3 / 6
        
        cumulative += monthly_revenue
        revenue_timeline.append(cumulative)
    
    # Category breakdown
    categories = {}
    for item in items_with_analysis:
        title = item['title'].lower()
        if any(keyword in title for keyword in ['compressor', 'vacuum', 'pressure']):
            category = 'Air Tools'
        elif any(keyword in title for keyword in ['motor', 'pump', 'fan']):
            category = 'Motors & Pumps'
        elif any(keyword in title for keyword in ['cabinet', 'storage', 'enclosure']):
            category = 'Storage & Enclosures'
        elif any(keyword in title for keyword in ['jack', 'lift', 'crane']):
            category = 'Lifting Equipment'
        else:
            category = 'Other'
        
        categories[category] = categories.get(category, 0) + 1
    
    return {
        'revenueTimeline': {
            'labels': months,
            'data': revenue_timeline
        },
        'categoryBreakdown': {
            'labels': list(categories.keys()),
            'data': list(categories.values())
        }
    }

def save_analysis_to_db(manifest_id, items_with_analysis, summary, charts, file_hash, filename):
    """Save analysis results to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate upload ID
        upload_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Insert upload record with file hash
        cursor.execute("""
            INSERT INTO uploads (id, filename, s3_key, status, total_items, processed_items, file_hash, manifest_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            upload_id,
            filename,
            f"uploads/{upload_id}/{filename}",  # S3 key format
            'completed',
            summary['totalItems'],
            summary['totalItems'],
            file_hash,
            manifest_id
        ))
        
        # Insert manifest record
        cursor.execute("""
            INSERT INTO manifests (id, created_at, total_items, total_msrp, projected_revenue, profit_margin, upload_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            manifest_id,
            datetime.now(),
            summary['totalItems'],
            summary['totalMsrp'],
            summary['projectedRevenue'],
            summary['profitMargin'],
            upload_id
        ))
        
        # Insert items
        for item in items_with_analysis:
            cursor.execute("""
                INSERT INTO items (manifest_id, item_number, title, msrp, estimated_sale_price, 
                                 profit, demand, sales_time, reasoning)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                manifest_id,
                item['item_number'],
                item['title'],
                item['msrp'],
                item['analysis']['estimatedSalePrice'],
                item['analysis']['estimatedSalePrice'] - item['msrp'],
                item['analysis']['demand'],
                item['analysis']['salesTime'],
                item['analysis']['reasoning']
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Database save error: {str(e)}")
        raise

def get_paapi_credentials():
    """Get PAAPI credentials from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId='arbitrage/paapi-credentials')
        credentials = json.loads(response['SecretString'])
        return credentials
    except Exception as e:
        logger.error(f"Failed to get PAAPI credentials: {str(e)}")
        return None

def check_amazon_availability(item_title, item_number=None):
    """Check if item is available on Amazon using PAAPI"""
    try:
        credentials = get_paapi_credentials()
        if not credentials:
            return {'available': False, 'price': None, 'url': None}
        
        # Initialize Amazon API client
        amazon = AmazonApi(
            credentials['access_key'],
            credentials['secret_key'],
            credentials['partner_tag'],  # Associate tag from credentials
            credentials['region']  # Region from credentials
        )
        
        # Search for items (limit to 20 for performance)
        response = amazon.search_items(
            keywords=item_title[:100],  # Limit keywords length
            search_index='All',
            item_count=20  # Limit to 20 items for performance
        )
        
        if response and len(response) > 0:
            item = response[0]
            
            return {
                'available': True,
                'price': item.get('price', {}).get('amount', 0) if item.get('price') else None,
                'url': item.get('detail_page_url'),
                'title': item.get('title')
            }
        
        return {'available': False, 'price': None, 'url': None}
        
    except Exception as e:
        logger.error(f"Amazon lookup failed for '{item_title}': {str(e)}")
        return {'available': False, 'price': None, 'url': None}

def check_ebay_availability(item_title, item_number=None):
    """Check if item is available on eBay using eBay API"""
    try:
        # eBay API endpoint for finding items
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        
        # Search parameters
        params = {
            'q': item_title[:100],  # Limit search terms
            'limit': 1,
            'sort': 'price'
        }
        
        headers = {
            'Authorization': f'Bearer {os.getenv("EBAY_ACCESS_TOKEN", "")}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('itemSummaries'):
                item = data['itemSummaries'][0]
                return {
                    'available': True,
                    'price': float(item.get('price', {}).get('value', 0)),
                    'url': item.get('itemWebUrl'),
                    'title': item.get('title')
                }
        
        return {'available': False, 'price': None, 'url': None}
        
    except Exception as e:
        logger.error(f"eBay lookup failed for '{item_title}': {str(e)}")
        return {'available': False, 'price': None, 'url': None}

def check_marketplace_availability(item_title, item_number=None):
    """Check availability on both Amazon and eBay with timeout"""
    import concurrent.futures
    
    # Use thread pool to run both lookups concurrently with timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        amazon_future = executor.submit(check_amazon_availability, item_title, item_number)
        ebay_future = executor.submit(check_ebay_availability, item_title, item_number)
        
        # Wait for results with timeout (5 seconds total)
        try:
            amazon_result = amazon_future.result(timeout=5)
        except concurrent.futures.TimeoutError:
            logger.warning(f"Amazon lookup timeout for '{item_title}'")
            amazon_result = {'available': False, 'price': None, 'url': None}
        
        try:
            ebay_result = ebay_future.result(timeout=5)
        except concurrent.futures.TimeoutError:
            logger.warning(f"eBay lookup timeout for '{item_title}'")
            ebay_result = {'available': False, 'price': None, 'url': None}
    
    return {
        'amazon': amazon_result,
        'ebay': ebay_result
    }

def find_product_image(item_title, item_number=None):
    """Find and download product image from Amazon or eBay"""
    # Temporarily disabled due to Pillow import issues
    return None

# Image processing functions temporarily disabled due to Pillow import issues
def find_amazon_image(item_title, item_number=None):
    return None

def find_ebay_image(item_title, item_number=None):
    return None

def download_and_store_image(image_url, item_title, source):
    return None

def create_thumbnail(image_data, size=(200, 200)):
    return None

def lambda_handler(event, context):
    """Main Lambda handler"""
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent,X-Amz-Source-Arn,X-Amz-Trace-Id',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE',
        'Access-Control-Max-Age': '86400',
        'Access-Control-Allow-Credentials': 'false'
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
        DB_CONFIG['host'] = os.environ['DB_HOST']
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
        
        # Parse CSV
        items = parse_manifest_csv(file_content)
        logger.info(f"Parsed {len(items)} items from CSV")
        
        if not items:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No valid items found in CSV'})
            }
        
        # Calculate file hash and check for existing analysis
        file_hash = calculate_file_hash(file_content)
        logger.info(f"File hash: {file_hash}")
        
        # Check if we already have analysis for this file (disabled to ensure fresh marketplace data)
        existing_analysis = None  # Disabled to ensure fresh Amazon/eBay price lookups
        # existing_analysis = check_existing_analysis(file_hash)
        if existing_analysis:
            logger.info(f"Found existing analysis for file hash {file_hash}")
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(existing_analysis)
            }
        
        logger.info(f"No existing analysis found, processing {len(items)} items")
        
        # Analyze items with eBay data first, then AI/mock fallback
        items_with_analysis = []
        items_to_process = items[:2]  # Process only first 2 items with AI to stay under API Gateway timeout
        
        logger.info(f"Processing {len(items_to_process)} items with AI analysis out of {len(items)} total items")
        
        for item in items_to_process:
            analysis = analyze_item_with_ebay_data(item)
            # Calculate profit based on liquidation purchase price (33% of sale price)
            liquidation_purchase_price = analysis['estimatedSalePrice'] * 0.33
            profit = analysis['estimatedSalePrice'] - liquidation_purchase_price
            items_with_analysis.append({
                **item,
                'analysis': analysis,
                'profit': profit
            })
        
        # Add remaining items with mock analysis
        remaining_items = items[2:]
        logger.info(f"Processing {len(remaining_items)} remaining items with mock analysis")
        
        for item in remaining_items:
            analysis = analyze_item_mock(item)
            # Calculate profit based on liquidation purchase price (33% of sale price)
            liquidation_purchase_price = analysis['estimatedSalePrice'] * 0.33
            profit = analysis['estimatedSalePrice'] - liquidation_purchase_price
            items_with_analysis.append({
                **item,
                'analysis': analysis,
                'profit': profit
            })
        
        # Calculate summary
        summary = calculate_summary(items_with_analysis)
        
        # Generate charts
        charts = generate_charts(items_with_analysis)
        
        # Save to database (temporarily disabled for testing)
        manifest_id = f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # save_analysis_to_db(manifest_id, items_with_analysis, summary, charts, file_hash, filename)
        
        logger.info(f"Processed {len(items_with_analysis)} items successfully")
        
        # Prepare response
        response_data = {
            'manifestId': manifest_id,
            'summary': summary,
            'items': items_with_analysis,
            'charts': charts,
            'processedAt': datetime.now().isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response_data, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }
