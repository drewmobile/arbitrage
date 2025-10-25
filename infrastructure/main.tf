terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# S3 bucket for static website hosting
resource "aws_s3_bucket" "arbitrage_app" {
  bucket = "arby-sndflo-com"
}

resource "aws_s3_bucket_public_access_block" "arbitrage_app" {
  bucket = aws_s3_bucket.arbitrage_app.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "arbitrage_app" {
  bucket = aws_s3_bucket.arbitrage_app.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# S3 bucket policy for CloudFront OAI access
resource "aws_s3_bucket_policy" "arbitrage_app" {
  bucket = aws_s3_bucket.arbitrage_app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.arbitrage_app.iam_arn
        }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.arbitrage_app.arn}/*"
      }
    ]
  })
}

# S3 bucket for CSV uploads
resource "aws_s3_bucket" "csv_uploads" {
  bucket = "arby-csv-uploads"
}

resource "aws_s3_bucket_versioning" "csv_uploads_versioning" {
  bucket = aws_s3_bucket.csv_uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "csv_uploads_encryption" {
  bucket = aws_s3_bucket.csv_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "csv_uploads_pab" {
  bucket = aws_s3_bucket.csv_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "csv_uploads" {
  bucket = aws_s3_bucket.csv_uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["https://arby.sndflo.com"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "arbitrage_app" {
  # S3 origin for static files
  origin {
    domain_name = aws_s3_bucket.arbitrage_app.bucket_regional_domain_name
    origin_id   = "S3-arby-sndflo-com"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.arbitrage_app.cloudfront_access_identity_path
    }
  }

  # API Gateway origin for Lambda functions
  origin {
    domain_name = replace(aws_api_gateway_deployment.arbitrage_api.invoke_url, "/^https?://([^/]+).*$/", "$1")
    origin_id   = "API-Gateway"
    origin_path = ""

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Cache behavior for API Gateway (no caching)
  ordered_cache_behavior {
    path_pattern           = "/prod/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]  # Required by CloudFront, but TTL is 0
    target_origin_id       = "API-Gateway"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Completely disable caching for API calls
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
      headers = ["*"]  # Forward all headers for API calls
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Arbitrage App Distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]  # Required by CloudFront, but TTL is 0
    target_origin_id       = "S3-arby-sndflo-com"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Completely disable caching
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
      headers = ["Authorization", "CloudFront-Forwarded-Proto", "CloudFront-Is-Desktop-Viewer", "CloudFront-Is-Mobile-Viewer", "CloudFront-Is-Tablet-Viewer", "CloudFront-Viewer-Country"]
    }
  }

  # Custom error pages to prevent caching
  custom_error_response {
    error_code         = 400
    response_code      = 400
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 403
    response_code      = 403
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 500
    response_code      = 500
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 502
    response_code      = 502
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 503
    response_code      = 503
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code         = 504
    response_code      = 504
    response_page_path = "/error.html"
    error_caching_min_ttl = 0
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.arbitrage_app.certificate_arn
    ssl_support_method        = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Restrict to North America
  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "CA", "MX"]
    }
  }

  aliases = ["arby.sndflo.com"]
}

resource "aws_cloudfront_origin_access_identity" "arbitrage_app" {
  comment = "OAI for arby.sndflo.com"
}

# Route53 hosted zone (assuming sndflo.com already exists)
data "aws_route53_zone" "sndflo" {
  name = "sndflo.com"
}

# ACM Certificate for HTTPS
resource "aws_acm_certificate" "arbitrage_app" {
  domain_name       = "arby.sndflo.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "Arbitrage App Certificate"
  }
}

resource "aws_acm_certificate_validation" "arbitrage_app" {
  certificate_arn         = aws_acm_certificate.arbitrage_app.arn
  validation_record_fqdns = [for record in aws_route53_record.arbitrage_app_cert_validation : record.fqdn]

  timeouts {
    create = "5m"
  }
}

resource "aws_route53_record" "arbitrage_app_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.arbitrage_app.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.sndflo.zone_id
}

resource "aws_route53_record" "arbitrage_app" {
  zone_id = data.aws_route53_zone.sndflo.zone_id
  name    = "arby.sndflo.com"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.arbitrage_app.domain_name
    zone_id                = aws_cloudfront_distribution.arbitrage_app.hosted_zone_id
    evaluate_target_health = false
  }
}

# RDS PostgreSQL database
resource "aws_db_instance" "arbitrage_db" {
  identifier = "arbitrage-db"
  
  engine         = "postgres"
  engine_version = "15.14"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type         = "gp2"
  storage_encrypted    = true
  
  db_name  = "arbitrage"
  username = "arbitrage_user"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.arbitrage.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  publicly_accessible = true
  
  tags = {
    Name = "arbitrage-db"
  }
}

resource "aws_db_subnet_group" "arbitrage" {
  name       = "arbitrage-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "arbitrage-db-subnet-group"
  }
}

# Use existing VPC instead of creating new one
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "arbitrage-rds-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "arbitrage-rds-sg"
  }
}

# Lambda function for CSV processing
resource "aws_lambda_function" "csv_processor" {
  filename         = "csv_processor.zip"
  function_name    = "arbitrage-csv-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "csv_processor.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512

  environment {
    variables = {
      DB_HOST     = aws_db_instance.arbitrage_db.endpoint
      DB_NAME     = aws_db_instance.arbitrage_db.db_name
      DB_USER     = aws_db_instance.arbitrage_db.username
      DB_PASSWORD = var.db_password
      OPENAI_API_KEY = var.openai_api_key
      EBAY_APP_ID = var.ebay_app_id
    }
  }

  # vpc_config removed to allow internet access for AI API
}

# Lambda function for CSV upload handling
resource "aws_lambda_function" "csv_uploader" {
  filename         = "csv_uploader.zip"
  function_name    = "arbitrage-csv-uploader"
  role            = aws_iam_role.lambda_role.arn
  handler         = "csv_uploader.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      DB_HOST     = aws_db_instance.arbitrage_db.endpoint
      DB_NAME     = aws_db_instance.arbitrage_db.db_name
      DB_USER     = aws_db_instance.arbitrage_db.username
      DB_PASSWORD = var.db_password
      S3_UPLOADS_BUCKET = aws_s3_bucket.csv_uploads.bucket
    }
  }

  layers = ["arn:aws:lambda:us-east-1:784289278185:layer:psycopg2-binary-v2:1"]
}

# Lambda function for async CSV processing
resource "aws_lambda_function" "csv_processor_async" {
  filename         = "csv_processor_async.zip"
  function_name    = "arbitrage-csv-processor-async"
  role            = aws_iam_role.lambda_role.arn
  handler         = "csv_processor_async.lambda_handler"
  runtime         = "python3.9"
  timeout         = 900
  memory_size     = 512

  environment {
    variables = {
      DB_HOST     = aws_db_instance.arbitrage_db.endpoint
      DB_NAME     = aws_db_instance.arbitrage_db.db_name
      DB_USER     = aws_db_instance.arbitrage_db.username
      DB_PASSWORD = var.db_password
      S3_UPLOADS_BUCKET = aws_s3_bucket.csv_uploads.bucket
      OPENAI_API_KEY = var.openai_api_key
    }
  }

  layers = ["arn:aws:lambda:us-east-1:784289278185:layer:psycopg2-binary-v2:1"]
}

resource "aws_iam_role" "lambda_role" {
  name = "arbitrage-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "arbitrage-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.csv_uploads.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_security_group" "lambda" {
  name_prefix = "arbitrage-lambda-"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "arbitrage-lambda-sg"
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "arbitrage_api" {
  name        = "arbitrage-api"
  description = "API for arbitrage analysis"
}

resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  parent_id   = aws_api_gateway_rest_api.arbitrage_api.root_resource_id
  path_part   = "upload"
}

resource "aws_api_gateway_method" "upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "upload_options_200" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration" "upload_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_integration_response" "upload_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = aws_api_gateway_method_response.upload_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent,X-Amz-Source-Arn,X-Amz-Trace-Id'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "upload_post_200" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "upload_post_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  status_code = aws_api_gateway_method_response.upload_post_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent,X-Amz-Source-Arn,X-Amz-Trace-Id'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

resource "aws_api_gateway_integration" "upload_integration" {
  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.csv_processor.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_processor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.arbitrage_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "arbitrage_api" {
  depends_on = [
    aws_api_gateway_integration.upload_integration,
    aws_api_gateway_integration.upload_options_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.arbitrage_api.id
  stage_name  = "prod"
}

# Variables
variable "db_password" {
  description = "Password for the RDS database"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for AI analysis"
  type        = string
  sensitive   = true
}

variable "ebay_app_id" {
  description = "eBay App ID for Finding API access"
  type        = string
  sensitive   = true
}

# Outputs
output "cloudfront_domain" {
  value = aws_cloudfront_distribution.arbitrage_app.domain_name
}

output "api_gateway_url" {
  value = aws_api_gateway_deployment.arbitrage_api.invoke_url
}

output "openai_api_key" {
  value = var.openai_api_key
  sensitive = true
}

output "s3_bucket_name" {
  value = aws_s3_bucket.arbitrage_app.bucket
}

output "db_endpoint" {
  value = aws_db_instance.arbitrage_db.endpoint
}
