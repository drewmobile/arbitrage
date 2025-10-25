# Arbitrage Analyzer Frontend

A React-based frontend for the arbitrage analysis web application that allows users to upload CSV manifests and view AI-powered arbitrage analysis results.

## Features

- **CSV Upload**: Drag-and-drop interface for uploading Grainger manifest CSV files
- **Real-time Analysis**: Progress tracking during AI analysis
- **Results Dashboard**: Comprehensive view of arbitrage potential with charts and tables
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Built with Tailwind CSS and Heroicons

## Technology Stack

- React 18
- Tailwind CSS for styling
- React Dropzone for file uploads
- Chart.js for data visualization
- Axios for API communication
- React Hot Toast for notifications

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Set environment variables:
```bash
# Create .env file
REACT_APP_API_URL=https://your-api-gateway-url.amazonaws.com/prod
```

3. Start development server:
```bash
npm start
```

4. Build for production:
```bash
npm run build
```

## Project Structure

```
src/
├── components/
│   ├── AnalysisResults.js    # Results display component
│   └── LoadingSpinner.js     # Loading spinner component
├── App.js                    # Main application component
├── index.js                  # Application entry point
└── index.css                 # Global styles
```

## API Integration

The frontend communicates with the backend Lambda function through API Gateway:

- **POST /upload**: Upload CSV file for analysis
- **Response**: Analysis results including summary, items, and charts

## Deployment

The built application is deployed to S3 and served through CloudFront with no caching enabled for real-time updates.

## CSV Format Support

The application is designed to work with Grainger manifest CSV files containing:
- Item numbers/SKUs
- Product descriptions
- MSRP prices
- Pallet information
- Notes
