import React, { useState, useEffect } from 'react';
import { Download, FileText, ExternalLink, RefreshCw } from 'lucide-react';
import { apiService, PDF, downloadFile } from '../services/api';

const PDFManager: React.FC = () => {
  const [pdfs, setPdfs] = useState<PDF[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<Set<string>>(new Set());

  const fetchPDFs = async () => {
    try {
      setLoading(true);
      const data = await apiService.getPDFs();
      setPdfs(data);
    } catch (error) {
      console.error('Failed to fetch PDFs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPDFs();
  }, []);

  const handleDownload = async (pdf: PDF) => {
    if (!pdf.minio_object_name) {
      alert('PDF not available for download');
      return;
    }

    try {
      setDownloading(prev => new Set(prev).add(pdf.id));
      const blob = await apiService.downloadPDF(pdf.id);
      const filename = pdf.filename || pdf.url.split('/').pop() || `document_${pdf.id}.pdf`;
      downloadFile(blob, filename);
    } catch (error) {
      console.error('Failed to download PDF:', error);
      alert('Failed to download PDF');
    } finally {
      setDownloading(prev => {
        const newSet = new Set(prev);
        newSet.delete(pdf.id);
        return newSet;
      });
    }
  };

  const getDomainFromUrl = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return 'Unknown';
    }
  };

  const getPDFName = (url: string) => {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      const filename = pathname.split('/').pop();
      return filename || 'document.pdf';
    } catch {
      return 'document.pdf';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-primary-600" />
        <span className="ml-2">Loading PDFs...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">PDFs ({pdfs.length})</h2>
        <button
          onClick={fetchPDFs}
          className="btn btn-secondary flex items-center gap-2"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {pdfs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p className="text-lg">No PDFs found</p>
          <p className="text-sm">Start scraping to see PDFs here</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pdfs.map((pdf) => (
            <div key={pdf.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText className="h-8 w-8 text-red-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">
                      {getPDFName(pdf.url)}
                    </h3>
                    <p className="text-sm text-gray-500 truncate">
                      {getDomainFromUrl(pdf.url)}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 ml-2">
                  <a
                    href={pdf.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="View original"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                  {pdf.minio_object_name && (
                    <button
                      onClick={() => handleDownload(pdf)}
                      disabled={downloading.has(pdf.id)}
                      className="p-1 text-primary-600 hover:text-primary-700 disabled:opacity-50"
                      title="Download PDF"
                    >
                      {downloading.has(pdf.id) ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs text-gray-500 break-all">
                  <strong>URL:</strong> {pdf.url}
                </div>
                {pdf.minio_object_name && (
                  <div className="text-xs text-green-600">
                    <strong>Status:</strong> Downloaded
                  </div>
                )}
                {pdf.meta && (
                  <div className="text-xs text-gray-500">
                    <strong>Downloaded:</strong> {pdf.meta.downloaded ? 'Yes' : 'No'}
                  </div>
                )}
              </div>

              {!pdf.minio_object_name && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    PDF is being processed or download failed
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PDFManager;
