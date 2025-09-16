import React, { useState } from 'react';
import { Download, FileText, RefreshCw, BarChart3 } from 'lucide-react';
import { apiService, downloadFile } from '../services/api';

const ReportsManager: React.FC = () => {
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleGenerateReports = async () => {
    try {
      setGenerating(true);
      const result = await apiService.generateReports();
      alert(result.message);
    } catch (error) {
      console.error('Failed to generate reports:', error);
      alert('Failed to generate reports');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadReports = async () => {
    try {
      setDownloading(true);
      const blob = await apiService.downloadReports();
      downloadFile(blob, 'reports.zip');
    } catch (error) {
      console.error('Failed to download reports:', error);
      alert('Failed to download reports');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Reports & Analytics</h2>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Generate Reports Card */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="h-6 w-6 text-primary-600" />
            <h3 className="text-lg font-semibold text-white">Generate Reports</h3>
          </div>
          
          <p className="text-gray-600 mb-4">
            Create comprehensive reports of all scraped content in JSON and CSV formats.
          </p>
          
          <button
            onClick={handleGenerateReports}
            disabled={generating}
            className="btn btn-primary w-full flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <BarChart3 className="h-4 w-4" />
                Generate Reports
              </>
            )}
          </button>
        </div>

        {/* Download Reports Card */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Download className="h-6 w-6 text-green-600" />
            <h3 className="text-lg font-semibold text-white">Download Reports</h3>
          </div>
          
          <p className="text-gray-600 mb-4">
            Download all generated reports as a ZIP file containing JSON and CSV files.
          </p>
          
          <button
            onClick={handleDownloadReports}
            disabled={downloading}
            className="btn btn-success w-full flex items-center justify-center gap-2"
          >
            {downloading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Download Reports
              </>
            )}
          </button>
        </div>
      </div>

      {/* Report Information */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Report Contents</h3>
        
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <FileText className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-white">JSON Reports</h4>
              <p className="text-sm text-gray-600">
                Structured data files containing metadata for all videos and PDFs with detailed information.
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <BarChart3 className="h-5 w-5 text-green-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-white">CSV Reports</h4>
              <p className="text-sm text-gray-600">
                Spreadsheet-compatible files for easy data analysis and visualization.
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3">
            <Download className="h-5 w-5 text-purple-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-white">File Information</h4>
              <p className="text-sm text-gray-600">
                Each report includes URLs, local file paths, metadata, and download status.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Usage Instructions */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-medium text-yellow-900 mb-2">Usage Instructions</h3>
        <div className="text-sm text-yellow-800 space-y-1">
          <p>1. First, scrape some content using the "Start Scraping" tab</p>
          <p>2. Generate reports to create the data files</p>
          <p>3. Download the reports ZIP file for analysis</p>
          <p>4. Use the JSON/CSV files in your preferred data analysis tools</p>
        </div>
      </div>
    </div>
  );
};

export default ReportsManager;
