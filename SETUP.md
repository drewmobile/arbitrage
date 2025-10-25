# Environment Setup

## API Keys Configuration

This project uses environment variables for sensitive API keys. **Never commit `.env` files to git!**

### Setup Steps:

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your actual API keys:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Required API Keys:**
   - **OpenAI API Key**: Get from https://platform.openai.com/account/api-keys
   - **eBay App ID**: Get from https://developer.ebay.com/my/keys
   - **Database Credentials**: From your RDS instance
   - **Amazon PAAPI**: Stored in AWS Secrets Manager (see below)

### AWS Secrets Manager (Recommended for Production)

Sensitive credentials like Amazon PAAPI keys should be stored in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name arbitrage/paapi-credentials \
  --secret-string '{
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "partner_tag": "YOUR_PARTNER_TAG",
    "region": "US"
  }' \
  --region us-east-1
```

### Updating Lambda Environment Variables

To update Lambda function environment variables:

```bash
aws lambda update-function-configuration \
  --function-name arbitrage-csv-processor \
  --environment Variables="{
    OPENAI_API_KEY=your-new-key,
    EBAY_APP_ID=your-ebay-id,
    DB_HOST=your-db-host,
    DB_NAME=arbitrage,
    DB_USER=arbitrage_user,
    DB_PASSWORD=your-password
  }" \
  --region us-east-1
```

### Security Best Practices

✅ **DO:**
- Keep `.env` files in `.gitignore`
- Use AWS Secrets Manager for production secrets
- Rotate API keys regularly
- Use different keys for dev/staging/production
- Store credentials in environment variables, not in code

❌ **DON'T:**
- Commit `.env` files to git (even private repos!)
- Hard-code API keys in source code
- Share API keys in chat/email/Slack
- Use production keys in development
- Store keys in plaintext files

### If a Key is Leaked

1. **Immediately revoke** the leaked key
2. **Generate a new key** from the provider
3. **Update** all places where the key is used
4. **Review** git history and remove if committed
5. **Enable** monitoring/alerts for unusual API usage

## Frontend Environment Variables

The React frontend uses `.env.production` for build-time configuration:

```bash
REACT_APP_API_URL=https://your-api-gateway-url.amazonaws.com/prod
```

This file can be committed since it contains public URLs, not secrets.
