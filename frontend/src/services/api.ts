import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export interface Video {
  id: string;
  url: string;
  title?: string;
  duration?: number;
  filename?: string;
  file_size?: number;
  minio_object_name?: string;
  download_date?: string;
  meta?: Record<string, any>;
}

export interface PDF {
  id: string;
  url: string;
  filename?: string;
  file_size?: number;
  minio_object_name?: string;
  download_date?: string;
  meta?: Record<string, any>;
}

export interface ScrapeRequest {
  urls: string[];
  keywords: string[];
}

export interface ScrapeStatus {
  status: string;
  message: string;
  task_id?: string;
}

export const apiService = {
  // Scraping endpoints
  async scrapeContent(request: ScrapeRequest): Promise<ScrapeStatus> {
    const response = await api.post('/scrape', request);
    return response.data;
  },

  // Data retrieval endpoints
  async getVideos(): Promise<Video[]> {
    const response = await api.get('/videos');
    return response.data;
  },

  async getPDFs(): Promise<PDF[]> {
    const response = await api.get('/pdfs');
    return response.data;
  },

  // Download endpoints
  async downloadVideo(videoId: string): Promise<Blob> {
    const response = await api.get(`/videos/${videoId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async downloadPDF(pdfId: string): Promise<Blob> {
    const response = await api.get(`/pdfs/${pdfId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Reports endpoints
  async generateReports(): Promise<{ status: string; message: string }> {
    const response = await api.post('/reports/generate');
    return response.data;
  },

  async downloadReports(): Promise<Blob> {
    const response = await api.get('/reports/download', {
      responseType: 'blob',
    });
    return response.data;
  },
};

// Utility function to trigger file download
export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
