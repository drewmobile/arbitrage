import React, { useState, useMemo } from 'react';
import {
    ArrowLeftIcon,
    CurrencyDollarIcon,
    ChartBarIcon,
    ClockIcon,
    ArrowTrendingUpIcon as TrendingUpIcon,
    ArrowTrendingDownIcon as TrendingDownIcon,
    MinusIcon,
    ChevronUpIcon,
    ChevronDownIcon
} from '@heroicons/react/24/outline';
import { Line, Bar } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend
);

const AnalysisResults = ({ results, onReset, fileName }) => {
    const { summary, items, charts } = results;

    // Sorting state
    const [sortField, setSortField] = useState('profit');
    const [sortDirection, setSortDirection] = useState('desc');

    // Image modal state
    const [imageModal, setImageModal] = useState({ isOpen: false, imageUrl: '', title: '' });

    // Sort items based on current sort settings
    const sortedItems = useMemo(() => {
        if (!items || !sortField) return items;

        return [...items].sort((itemA, itemB) => {
            let valueA, valueB;

            switch (sortField) {
                case 'estimatedSalePrice':
                    valueA = itemA.analysis?.estimatedSalePrice || 0;
                    valueB = itemB.analysis?.estimatedSalePrice || 0;
                    break;
                case 'profit':
                    valueA = itemA.profit || 0;
                    valueB = itemB.profit || 0;
                    break;
                case 'demand':
                    // Convert demand to numeric for sorting
                    const demandOrder = { 'High': 3, 'Medium': 2, 'Low': 1 };
                    valueA = demandOrder[itemA.analysis?.demand] || 0;
                    valueB = demandOrder[itemB.analysis?.demand] || 0;
                    break;
                case 'salesTime':
                    // Convert sales time to numeric for sorting (extract weeks/months)
                    valueA = parseSalesTimeToDays(itemA.analysis?.salesTime);
                    valueB = parseSalesTimeToDays(itemB.analysis?.salesTime);
                    break;
                default:
                    return 0;
            }

            if (valueA < valueB) return sortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }, [items, sortField, sortDirection]);

    // Helper function to parse sales time to days for sorting
    const parseSalesTimeToDays = (salesTime) => {
        if (!salesTime) return 0;

        const timeStr = salesTime.toLowerCase();
        if (timeStr.includes('week')) {
            const weeks = parseInt(timeStr.match(/(\d+)/)?.[1] || '0');
            return weeks * 7;
        } else if (timeStr.includes('month')) {
            const months = parseInt(timeStr.match(/(\d+)/)?.[1] || '0');
            return months * 30;
        }
        return 0;
    };

    // Handle column header click for sorting
    const handleSort = (field) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const openImageModal = (imageUrl, title) => {
        setImageModal({ isOpen: true, imageUrl, title });
    };

    const closeImageModal = () => {
        setImageModal({ isOpen: false, imageUrl: '', title: '' });
    };

    // Get sort icon for column headers
    const getSortIcon = (field) => {
        if (sortField !== field) {
            return <ChevronUpIcon className="h-4 w-4 text-gray-400" />;
        }
        return sortDirection === 'asc'
            ? <ChevronUpIcon className="h-4 w-4 text-gray-600" />
            : <ChevronDownIcon className="h-4 w-4 text-gray-600" />;
    };

    const getProfitIcon = (profit) => {
        if (profit > 0) return <TrendingUpIcon className="h-5 w-5 text-green-500" />;
        if (profit < 0) return <TrendingDownIcon className="h-5 w-5 text-red-500" />;
        return <MinusIcon className="h-5 w-5 text-gray-500" />;
    };

    const getProfitClass = (profit) => {
        if (profit > 0) return 'profit-positive';
        if (profit < 0) return 'profit-negative';
        return 'profit-neutral';
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    };

    const formatPercentage = (value) => {
        return `${(value * 100).toFixed(1)}%`;
    };

    // Chart data
    const revenueChartData = {
        labels: charts?.revenueTimeline?.labels || [],
        datasets: [
            {
                label: 'Projected Revenue',
                data: charts?.revenueTimeline?.data || [],
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.1,
            },
        ],
    };

    const categoryChartData = {
        labels: charts?.categoryBreakdown?.labels || [],
        datasets: [
            {
                label: 'Items Count',
                data: charts?.categoryBreakdown?.data || [],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(139, 92, 246, 0.8)',
                ],
            },
        ],
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center">
                    <button
                        onClick={onReset}
                        className="mr-4 p-2 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <ArrowLeftIcon className="h-5 w-5" />
                    </button>
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Analysis Results</h2>
                        <p className="text-sm text-gray-500">Manifest: {fileName}</p>
                    </div>
                </div>
                <button
                    onClick={onReset}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                    <ArrowLeftIcon className="h-4 w-4 mr-2" />
                    New Analysis
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <CurrencyDollarIcon className="h-8 w-8 text-blue-600" />
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-500">Total MSRP</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {formatCurrency(summary?.totalMsrp || 0)}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <ChartBarIcon className="h-8 w-8 text-green-600" />
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-500">Projected Revenue</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {formatCurrency(summary?.projectedRevenue || 0)}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <CurrencyDollarIcon className="h-8 w-8 text-yellow-600" />
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-500">Suggested Purchase Price</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {formatCurrency((summary?.projectedRevenue || 0) * 0.33)}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <TrendingUpIcon className="h-8 w-8 text-purple-600" />
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-500">Potential Profit Margin</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {formatPercentage(((summary?.projectedRevenue || 0) - ((summary?.projectedRevenue || 0) * 0.33)) / (summary?.projectedRevenue || 0) * 100)}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <ClockIcon className="h-8 w-8 text-orange-600" />
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-500">Avg. Sales Time</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {summary?.avgSalesTime || 'N/A'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow-sm p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        Revenue Timeline
                    </h3>
                    <Line data={revenueChartData} options={{
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function (value) {
                                        return formatCurrency(value);
                                    }
                                }
                            }
                        }
                    }} />
                </div>

                <div className="bg-white rounded-lg shadow-sm p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        Category Breakdown
                    </h3>
                    <Bar data={categoryChartData} options={{
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                            }
                        }
                    }} />
                </div>
            </div>

            {/* Items Table */}
            <div className="bg-white rounded-lg shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">
                        Item Analysis ({items?.length || 0} items)
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Item
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Image
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    MSRP
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Qty
                                </th>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                                    onClick={() => handleSort('estimatedSalePrice')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Est. Sale Price</span>
                                        {getSortIcon('estimatedSalePrice')}
                                    </div>
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    <div className="flex items-center space-x-1">
                                        <span>Amazon Price</span>
                                    </div>
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    <div className="flex items-center space-x-1">
                                        <span>eBay Price</span>
                                    </div>
                                </th>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                                    onClick={() => handleSort('profit')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Profit</span>
                                        {getSortIcon('profit')}
                                    </div>
                                </th>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                                    onClick={() => handleSort('demand')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Demand</span>
                                        {getSortIcon('demand')}
                                    </div>
                                </th>
                                <th
                                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                                    onClick={() => handleSort('salesTime')}
                                >
                                    <div className="flex items-center space-x-1">
                                        <span>Sales Time</span>
                                        {getSortIcon('salesTime')}
                                    </div>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedItems?.map((item, index) => (
                                <tr key={index} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div>
                                                <div className="text-sm font-medium text-gray-900">
                                                    {item.item_number || item.sku}
                                                </div>
                                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                                    {item.title}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {item.analysis?.image?.thumbnail_url ? (
                                            <div className="flex items-center">
                                                <img
                                                    src={item.analysis.image.thumbnail_url}
                                                    alt={item.title}
                                                    className="h-12 w-12 rounded-lg object-cover cursor-pointer hover:opacity-80 transition-opacity"
                                                    onClick={() => openImageModal(item.analysis.image.original_url, item.title)}
                                                />
                                            </div>
                                        ) : (
                                            <div className="h-12 w-12 bg-gray-200 rounded-lg flex items-center justify-center">
                                                <span className="text-gray-400 text-xs">No Image</span>
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {formatCurrency(item.msrp || 0)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {item.quantity || 1}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {formatCurrency(item.analysis?.estimatedSalePrice || 0)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        <div className="flex items-center">
                                            {item.analysis?.marketplace?.amazon?.available ? (
                                                <div className="flex items-center">
                                                    <span className="text-green-600 mr-1">✓</span>
                                                    <span>{formatCurrency(item.analysis.marketplace.amazon.price || 0)}</span>
                                                </div>
                                            ) : (
                                                <span className="text-gray-400">N/A</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        <div className="flex items-center">
                                            {item.analysis?.marketplace?.ebay?.available ? (
                                                <div className="flex items-center">
                                                    <span className="text-blue-600 mr-1">✓</span>
                                                    <span>{formatCurrency(item.analysis.marketplace.ebay.price || 0)}</span>
                                                </div>
                                            ) : (
                                                <span className="text-gray-400">N/A</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            {getProfitIcon(item.profit || 0)}
                                            <span className={`ml-1 text-sm font-medium ${getProfitClass(item.profit || 0)}`}>
                                                {formatCurrency(item.profit || 0)}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${item.analysis?.demand === 'High' ? 'bg-green-100 text-green-800' :
                                            item.analysis?.demand === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                                                'bg-red-100 text-red-800'
                                            }`}>
                                            {item.analysis?.demand || 'Unknown'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {item.analysis?.salesTime || 'N/A'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Recommendations */}
            {summary?.recommendations && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-blue-900 mb-3">
                        AI Recommendations
                    </h3>
                    <ul className="space-y-2 text-sm text-blue-800">
                        {summary.recommendations.map((rec, index) => (
                            <li key={index} className="flex items-start">
                                <div className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3"></div>
                                <span>{rec}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Image Modal */}
            {imageModal.isOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={closeImageModal}>
                    <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
                        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                            <h3 className="text-lg font-medium text-gray-900">{imageModal.title}</h3>
                            <button
                                onClick={closeImageModal}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="p-4">
                            <img
                                src={imageModal.imageUrl}
                                alt={imageModal.title}
                                className="max-w-full max-h-[70vh] object-contain mx-auto"
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnalysisResults;
