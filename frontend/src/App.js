import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
    ArrowUpTrayIcon as UploadIcon,
    DocumentIcon,
    ChartBarIcon,
    CurrencyDollarIcon
} from '@heroicons/react/24/outline';
import toast, { Toaster } from 'react-hot-toast';
import axios from 'axios';
import AnalysisResults from './components/AnalysisResults';
import LoadingSpinner from './components/LoadingSpinner';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://1biv76cy0j.execute-api.us-east-1.amazonaws.com';

function App() {
    const [uploadedFile, setUploadedFile] = useState(null);
    const [csvText, setCsvText] = useState('');
    const [analysisResults, setAnalysisResults] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadMethod, setUploadMethod] = useState('file'); // 'file' or 'text'

    const onDrop = useCallback((acceptedFiles) => {
        const file = acceptedFiles[0];
        if (file && file.type === 'text/csv') {
            setUploadedFile(file);
            toast.success('CSV file uploaded successfully!');
        } else {
            toast.error('Please upload a valid CSV file');
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'text/csv': ['.csv']
        },
        multiple: false
    });

    const handleAnalysis = async () => {
        let fileContent = '';
        let filename = '';

        if (uploadMethod === 'file') {
            if (!uploadedFile) {
                toast.error('Please upload a CSV file first');
                return;
            }
            fileContent = await readFileAsText(uploadedFile);
            filename = uploadedFile.name;
        } else {
            if (!csvText.trim()) {
                toast.error('Please paste CSV data first');
                return;
            }
            fileContent = csvText;
            filename = 'pasted-data.csv';
        }

        setIsAnalyzing(true);
        setUploadProgress(0);

        try {
            const response = await axios.post(`${API_BASE_URL}/prod/upload`, {
                file: fileContent,
                filename: filename
            }, {
                headers: {
                    'Content-Type': 'application/json',
                },
                onUploadProgress: (progressEvent) => {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    setUploadProgress(progress);
                },
            });

            setAnalysisResults(response.data);
            toast.success('Analysis completed successfully!');
        } catch (error) {
            console.error('Analysis error:', error);
            toast.error('Failed to analyze CSV. Please try again.');
        } finally {
            setIsAnalyzing(false);
            setUploadProgress(0);
        }
    };

    const readFileAsText = (file) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    };

    const handleReset = () => {
        setUploadedFile(null);
        setCsvText('');
        setAnalysisResults(null);
        setIsAnalyzing(false);
        setUploadProgress(0);
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <Toaster position="top-right" />

            {/* Header */}
            <header className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center py-6">
                        <div className="flex items-center">
                            <ChartBarIcon className="h-8 w-8 text-blue-600 mr-3" />
                            <h1 className="text-2xl font-bold text-gray-900">Arbitrage Analyzer</h1>
                        </div>
                        <div className="text-sm text-gray-500">
                            AI-Powered Retail Arbitrage Analysis
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {!analysisResults ? (
                    <div className="space-y-8">
                        {/* Upload Method Selection */}
                        <div className="bg-white rounded-lg shadow-sm p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                                Upload Manifest CSV
                            </h2>

                            <div className="mb-6">
                                <div className="flex space-x-4">
                                    <button
                                        onClick={() => setUploadMethod('file')}
                                        className={`px-4 py-2 rounded-md text-sm font-medium ${uploadMethod === 'file'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        Upload File
                                    </button>
                                    <button
                                        onClick={() => setUploadMethod('text')}
                                        className={`px-4 py-2 rounded-md text-sm font-medium ${uploadMethod === 'text'
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        Paste CSV Data
                                    </button>
                                </div>
                            </div>

                            {uploadMethod === 'file' ? (
                                <div>
                                    <div
                                        {...getRootProps()}
                                        className={`upload-zone ${isDragActive ? 'dragover' : ''}`}
                                    >
                                        <input {...getInputProps()} />
                                        <UploadIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                                        {isDragActive ? (
                                            <p className="text-lg text-blue-600">Drop the CSV file here...</p>
                                        ) : (
                                            <div>
                                                <p className="text-lg text-gray-600 mb-2">
                                                    Drag & drop your manifest CSV here, or click to select
                                                </p>
                                                <p className="text-sm text-gray-500">
                                                    Supports any manifest CSV format (Grainger, generic products, parts, etc.)
                                                </p>
                                            </div>
                                        )}
                                    </div>

                                    {uploadedFile && (
                                        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                                            <div className="flex items-center">
                                                <DocumentIcon className="h-5 w-5 text-green-600 mr-2" />
                                                <span className="text-sm font-medium text-green-800">
                                                    {uploadedFile.name}
                                                </span>
                                                <span className="text-sm text-green-600 ml-2">
                                                    ({(uploadedFile.size / 1024).toFixed(1)} KB)
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div>
                                    <label htmlFor="csv-text" className="block text-sm font-medium text-gray-700 mb-2">
                                        Paste your CSV data below:
                                    </label>
                                    <textarea
                                        id="csv-text"
                                        value={csvText}
                                        onChange={(e) => setCsvText(e.target.value)}
                                        placeholder="Paste your CSV data here..."
                                        className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                                    />
                                    <p className="mt-2 text-sm text-gray-500">
                                        Supports any manifest CSV format (Grainger, generic products, parts, etc.)
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Analysis Button */}
                        <div className="bg-white rounded-lg shadow-sm p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="text-lg font-medium text-gray-900">Ready to Analyze</h3>
                                    <p className="text-sm text-gray-500">
                                        {uploadMethod === 'file'
                                            ? (uploadedFile ? `File: ${uploadedFile.name}` : 'No file uploaded')
                                            : (csvText.trim() ? 'CSV data ready' : 'No CSV data pasted')
                                        }
                                    </p>
                                </div>
                                <button
                                    onClick={handleAnalysis}
                                    disabled={isAnalyzing || (uploadMethod === 'file' ? !uploadedFile : !csvText.trim())}
                                    className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isAnalyzing ? (
                                        <>
                                            <LoadingSpinner />
                                            <span className="ml-2">Analyzing...</span>
                                        </>
                                    ) : (
                                        <>
                                            <CurrencyDollarIcon className="h-5 w-5 mr-2" />
                                            Analyze Manifest
                                        </>
                                    )}
                                </button>
                            </div>

                            {isAnalyzing && (
                                <div className="mt-4">
                                    <div className="bg-gray-200 rounded-full h-2">
                                        <div
                                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                            style={{ width: `${uploadProgress}%` }}
                                        ></div>
                                    </div>
                                    <p className="text-sm text-gray-600 mt-2">
                                        Processing your manifest... This may take a few moments.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <AnalysisResults
                        results={analysisResults}
                        onReset={handleReset}
                        fileName={uploadMethod === 'file' ? uploadedFile?.name : 'pasted-data.csv'}
                    />
                )}
            </main>
        </div>
    );
}

export default App;