import React, { useState, useEffect } from 'react';
import { Download, Play, ExternalLink, RefreshCw } from 'lucide-react';
import { apiService, Video, downloadFile } from '../services/api';

const VideoManager: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<Set<string>>(new Set());

  const fetchVideos = async () => {
    try {
      setLoading(true);
      const data = await apiService.getVideos();
      setVideos(data);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  const handleDownload = async (video: Video) => {
    if (!video.minio_object_name) {
      alert('Video not available for download');
      return;
    }

    try {
      setDownloading(prev => new Set(prev).add(video.id));
      const blob = await apiService.downloadVideo(video.id);
      const filename = video.filename || video.url.split('/').pop() || `video_${video.id}.mp4`;
      downloadFile(blob, filename);
    } catch (error) {
      console.error('Failed to download video:', error);
      alert('Failed to download video');
    } finally {
      setDownloading(prev => {
        const newSet = new Set(prev);
        newSet.delete(video.id);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-primary-600" />
        <span className="ml-2">Loading videos...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Videos ({videos.length})</h2>
        <button
          onClick={fetchVideos}
          className="btn btn-secondary flex items-center gap-2"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {videos.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Play className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p className="text-lg">No videos found</p>
          <p className="text-sm">Start scraping to see videos here</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {videos.slice(0, 3).map((video) => (
            <div key={video.id} className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-white truncate">
                    {video.title || `Video ${video.id}`}
                  </h3>
                  <p className="text-sm text-gray-500 truncate">
                    {getDomainFromUrl(video.url)}
                  </p>
                </div>
                <div className="flex gap-2 ml-2">
                  <a
                    href={video.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="View original"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                  {video.minio_object_name && (
                    <button
                      onClick={() => handleDownload(video)}
                      disabled={downloading.has(video.id)}
                      className="p-1 text-primary-600 hover:text-primary-700 disabled:opacity-50"
                      title="Download video"
                    >
                      {downloading.has(video.id) ? (
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
                  <strong>URL:</strong> {video.url}
                </div>
                {video.minio_object_name && (
                  <div className="text-xs text-green-600">
                    <strong>Status:</strong> Downloaded
                  </div>
                )}
                {video.meta && (
                  <div className="text-xs text-gray-500">
                    <strong>Source:</strong> {video.meta.source || 'Unknown'}
                  </div>
                )}
              </div>

              {!video.minio_object_name && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    Video is being processed or download failed
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

export default VideoManager;
