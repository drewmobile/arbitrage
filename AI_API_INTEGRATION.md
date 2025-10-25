# AI API Integration Configuration

This document outlines how to integrate various AI APIs for arbitrage analysis.

## Supported AI Services

### 1. OpenAI GPT-4
```python
# Environment variables needed:
# OPENAI_API_KEY=your_openai_api_key

def call_openai_api(prompt, item):
    api_key = os.environ.get('OPENAI_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'gpt-4',
        'messages': [
            {'role': 'system', 'content': 'You are an expert in retail arbitrage analysis for industrial equipment.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 500
    }
    
    response = requests.post('https://api.openai.com/v1/chat/completions', 
                           headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    else:
        raise Exception(f"OpenAI API error: {response.status_code}")
```

### 2. Anthropic Claude
```python
# Environment variables needed:
# ANTHROPIC_API_KEY=your_anthropic_api_key

def call_anthropic_api(prompt, item):
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'claude-3-sonnet-20240229',
        'max_tokens': 500,
        'messages': [
            {'role': 'user', 'content': prompt}
        ]
    }
    
    response = requests.post('https://api.anthropic.com/v1/messages', 
                           headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        content = result['content'][0]['text']
        return json.loads(content)
    else:
        raise Exception(f"Anthropic API error: {response.status_code}")
```

### 3. Google Gemini
```python
# Environment variables needed:
# GOOGLE_API_KEY=your_google_api_key

def call_gemini_api(prompt, item):
    api_key = os.environ.get('GOOGLE_API_KEY')
    
    data = {
        'contents': [{
            'parts': [{'text': prompt}]
        }],
        'generationConfig': {
            'temperature': 0.3,
            'maxOutputTokens': 500
        }
    }
    
    response = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}', 
                           json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        content = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(content)
    else:
        raise Exception(f"Gemini API error: {response.status_code}")
```

## Configuration

To enable AI API integration:

1. Add the API key to your Lambda environment variables
2. Uncomment the appropriate API call function in `csv_processor.py`
3. Update the `call_ai_api` function to use your preferred service

## Fallback Strategy

The system includes a robust fallback strategy:
1. Try AI API first
2. If AI API fails, use mock analysis based on item characteristics
3. Log all errors for monitoring and debugging

## Cost Considerations

- **OpenAI GPT-4**: ~$0.03 per item analysis
- **Anthropic Claude**: ~$0.015 per item analysis  
- **Google Gemini**: ~$0.01 per item analysis

For a manifest with 100 items, expect costs of $1-3 per analysis.

## Rate Limiting

All APIs have rate limits. The Lambda function includes:
- Exponential backoff retry logic
- Request queuing for large manifests
- Error handling for rate limit responses

## Monitoring

The system logs:
- AI API response times
- Success/failure rates
- Cost per analysis
- Fallback usage statistics
