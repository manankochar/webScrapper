from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import yt_dlp
import os
import threading
import asyncio
import httpx
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from datetime import datetime
import tempfile
import io
from bson import ObjectId

# MongoDB imports
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# MinIO imports
from minio import Minio
from minio.error import S3Error

app = FastAPI(title="Video Downloader API with MongoDB & MinIO", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class DownloadRequest(BaseModel):
    url: str

class DownloadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    video_id: Optional[str] = None

class VideoResponse(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    duration: Optional[int] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    minio_object_name: Optional[str] = None
    download_date: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None

class ScrapeRequest(BaseModel):
    urls: List[str] = []
    keywords: List[str] = []

class ScrapeStatus(BaseModel):
    status: str
    message: str

class PDFResponse(BaseModel):
    id: str
    url: str
    filename: Optional[str] = None
    file_size: Optional[int] = None
    minio_object_name: Optional[str] = None
    download_date: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None

# MongoDB setup
MONGO_URL = "mongodb://localhost:27017"
MONGO_DB = "video_downloader"
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[MONGO_DB]
videos_col = db["videos"]
pdfs_col = db["pdfs"]

# MinIO setup
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET_VIDEOS = "videos"
MINIO_BUCKET_PDFS = "pdfs"

class DatabaseManager:
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[MONGO_DB]
        self.videos = self.db.videos
        self.pdfs = self.db.pdfs
        
        # Create indexes for better performance
        try:
            self.videos.create_index("url", unique=True)
            self.pdfs.create_index("url", unique=True)
        except Exception as e:
            print(f"Index creation warning: {e}")
        
    def save_video(self, video_data: dict) -> str:
        """Save video metadata to MongoDB"""
        try:
            video_data["_id"] = ObjectId()
            video_data["download_date"] = datetime.utcnow()
            result = self.videos.insert_one(video_data)
            return str(result.inserted_id)
        except DuplicateKeyError:
            print(f"Video {video_data['url']} already exists in database - merging metadata")
            existing = self.videos.find_one({"url": video_data["url"]})
            if not existing:
                # Fallback: if for some reason find failed, try upsert
                upsert_fields = {k: v for k, v in video_data.items() if k not in {"_id"}}
                self.videos.update_one(
                    {"url": video_data["url"]},
                    {"$set": upsert_fields},
                    upsert=True,
                )
                found = self.videos.find_one({"url": video_data["url"]})
                return str(found["_id"]) if found else ""
            # Merge meta dictionaries (new keys override existing)
            merged_meta = {**existing.get("meta", {}), **video_data.get("meta", {})}
            # Build update fields (avoid changing _id)
            update_fields = {k: v for k, v in video_data.items() if k not in {"_id", "url", "meta"}}
            update_fields["meta"] = merged_meta
            update_fields["download_date"] = datetime.utcnow()
            self.videos.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            return str(existing["_id"])
    
    def save_pdf(self, pdf_data: dict) -> str:
        """Save PDF metadata to MongoDB"""
        try:
            pdf_data["_id"] = ObjectId()
            pdf_data["download_date"] = datetime.utcnow()
            result = self.pdfs.insert_one(pdf_data)
            return str(result.inserted_id)
        except DuplicateKeyError:
            print(f"PDF {pdf_data['url']} already exists in database")
            existing = self.pdfs.find_one({"url": pdf_data["url"]})
            return str(existing["_id"])
    
    def get_all_videos(self) -> List[dict]:
        """Get all videos from MongoDB"""
        videos = []
        for video in self.videos.find():
            video["id"] = str(video["_id"])
            del video["_id"]
            videos.append(video)
        return videos
    
    def get_all_pdfs(self) -> List[dict]:
        """Get all PDFs from MongoDB"""
        pdfs = []
        for pdf in self.pdfs.find():
            pdf["id"] = str(pdf["_id"])
            del pdf["_id"]
            pdfs.append(pdf)
        return pdfs
    
    def get_video_by_id(self, video_id: str) -> Optional[dict]:
        """Get video by ID from MongoDB"""
        try:
            video = self.videos.find_one({"_id": ObjectId(video_id)})
            if video:
                video["id"] = str(video["_id"])
                del video["_id"]
                return video
            return None
        except Exception:
            return None
    
    def get_pdf_by_id(self, pdf_id: str) -> Optional[dict]:
        """Get PDF by ID from MongoDB"""
        try:
            pdf = self.pdfs.find_one({"_id": ObjectId(pdf_id)})
            if pdf:
                pdf["id"] = str(pdf["_id"])
                del pdf["_id"]
                return pdf
            return None
        except Exception:
            return None

class MinIOManager:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        # Create buckets if they don't exist
        self._ensure_bucket(MINIO_BUCKET_VIDEOS)
        self._ensure_bucket(MINIO_BUCKET_PDFS)
    
    def _ensure_bucket(self, bucket_name: str):
        """Ensure bucket exists"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"Created MinIO bucket: {bucket_name}")
        except S3Error as e:
            print(f"Error creating bucket {bucket_name}: {e}")
    
    def upload_video(self, file_path: str, object_name: str) -> bool:
        """Upload video to MinIO"""
        try:
            self.client.fput_object(MINIO_BUCKET_VIDEOS, object_name, file_path)
            print(f"Uploaded video to MinIO: {object_name}")
            return True
        except S3Error as e:
            print(f"Error uploading video to MinIO: {e}")
            return False
    
    def upload_pdf(self, file_path: str, object_name: str) -> bool:
        """Upload PDF to MinIO"""
        try:
            self.client.fput_object(MINIO_BUCKET_PDFS, object_name, file_path)
            print(f"Uploaded PDF to MinIO: {object_name}")
            return True
        except S3Error as e:
            print(f"Error uploading PDF to MinIO: {e}")
            return False
    
    def download_video(self, object_name: str) -> Optional[io.BytesIO]:
        """Download video from MinIO"""
        try:
            response = self.client.get_object(MINIO_BUCKET_VIDEOS, object_name)
            try:
                data = response.read()
                return io.BytesIO(data)
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            print(f"Error downloading video from MinIO: {e}")
            return None
    
    def download_pdf(self, object_name: str) -> Optional[io.BytesIO]:
        """Download PDF from MinIO"""
        try:
            response = self.client.get_object(MINIO_BUCKET_PDFS, object_name)
            try:
                data = response.read()
                return io.BytesIO(data)
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            print(f"Error downloading PDF from MinIO: {e}")
            return None

# Initialize managers
db_manager = DatabaseManager()
minio_manager = MinIOManager()

# PDF Scraper class
class PDFScraper:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.request_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def scrape_pdf_links(self, url: str) -> List[str]:
        if "twitter.com" in urlparse(url).netloc:
            print(f"Skipping PDF scraping on Twitter URL: {url}")
            return []

        try:
            resp = await self.client.get(url, headers=self.request_headers, follow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = []
            netloc = urlparse(url).netloc
            is_google = "google." in netloc
            for a in soup.find_all("a", href=True):
                href = a["href"]
                candidate_url = None
                if is_google:
                    # Google result links often come as /url?q=<target>&...
                    if href.startswith("/url?"):
                        try:
                            from urllib.parse import parse_qs
                            qs = parse_qs(urlparse(href).query)
                            q = qs.get("q", [None])[0]
                            if q and ".pdf" in q.lower():
                                candidate_url = q
                        except Exception:
                            pass
                else:
                    if ".pdf" in href.lower():
                        candidate_url = urljoin(url, href)

                if candidate_url:
                    # Normalize and only accept http(s)
                    parsed = urlparse(candidate_url)
                    if parsed.scheme in ("http", "https"):
                        links.append(candidate_url)
            return links
        except Exception as e:
            print(f"Failed to scrape PDF links from {url}: {e}")
            return []

    async def download_pdf(self, url: str) -> Optional[str]:
        filename = os.path.basename(urlparse(url).path)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        
        try:
            print(f"Starting PDF download: {url}")
            # Optional HEAD pre-check for Content-Type
            try:
                head_resp = await self.client.head(
                    url,
                    headers={
                        "User-Agent": self.request_headers["User-Agent"],
                        "Accept": "application/pdf,*/*;q=0.8",
                    },
                    follow_redirects=True,
                    timeout=15,
                )
                ct = head_resp.headers.get("Content-Type", "").lower()
                if head_resp.status_code < 400 and ("application/pdf" in ct or url.lower().endswith(".pdf")):
                    pass
                else:
                    # Some servers disallow HEAD or misreport content-type; proceed to GET with validation below
                    pass
            except Exception:
                # HEAD failed; proceed to GET
                pass

            async with self.client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": self.request_headers["User-Agent"],
                    "Accept": "application/pdf,*/*;q=0.8",
                },
                follow_redirects=True,
            ) as r:
                r.raise_for_status()
                content_type = r.headers.get("Content-Type", "").lower()
                if "application/pdf" not in content_type and not url.lower().endswith(".pdf"):
                    print(f"Skipping non-PDF content from {url} (Content-Type: {content_type})")
                    return None
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    async for chunk in r.aiter_bytes(chunk_size=8192):
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                # Generate unique object name
                object_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                
                # Upload to MinIO
                if minio_manager.upload_pdf(temp_file_path, object_name):
                    # Get file size
                    file_size = os.path.getsize(temp_file_path)
                    
                    # Save metadata to MongoDB
                    pdf_data = {
                        "url": url,
                        "filename": filename,
                        "file_size": file_size,
                        "minio_object_name": object_name,
                        "meta": {"downloaded": True, "source": "scraper"}
                    }
                    pdf_id = db_manager.save_pdf(pdf_data)
                    print(f"Downloaded PDF {url} and saved with ID: {pdf_id}")
                    
                    # Clean up temp file
                    os.unlink(temp_file_path)
                    return pdf_id
                else:
                    # Clean up temp file on failure
                    os.unlink(temp_file_path)
                    return None
                    
        except Exception as e:
            print(f"Failed to download PDF {url}: {e}")
            return None

async def scrape_pdfs_from_urls(urls: List[str], max_per_url: int = 5, concurrent_downloads: int = 3):
    """Scrape PDFs from given URLs with timeouts and limited concurrency"""
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=10)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        pdf_scraper = PDFScraper(client)
        semaphore = asyncio.Semaphore(concurrent_downloads)

        async def bounded_download(link: str):
            try:
                async with semaphore:
                    return await asyncio.wait_for(pdf_scraper.download_pdf(link), timeout=60)
            except Exception as e:
                print(f"Download failed for {link}: {e}")
                return None

        for url in urls:
            print(f"Scraping PDFs from URL: {url}")
            parsed = urlparse(url)
            if (parsed.path or "").lower().endswith(".pdf"):
                # Direct PDF link: download directly instead of scraping
                await bounded_download(url)
                continue
            try:
                links = await asyncio.wait_for(pdf_scraper.scrape_pdf_links(url), timeout=20)
            except Exception as e:
                print(f"Scrape links timeout/failure for {url}: {e}")
                links = []

            # Cap number of links per source URL
            links = links[:max_per_url]

            # Kick off limited concurrent downloads
            tasks = [asyncio.create_task(bounded_download(link)) for link in links]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

async def scrape_pdfs_by_keywords(keywords: List[str], max_results: int = 5, concurrent_downloads: int = 3):
    """Scrape PDFs from Google search using keywords with timeouts and limited concurrency"""
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=10)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        pdf_scraper = PDFScraper(client)
        semaphore = asyncio.Semaphore(concurrent_downloads)

        async def bounded_download(link: str):
            try:
                async with semaphore:
                    return await asyncio.wait_for(pdf_scraper.download_pdf(link), timeout=60)
            except Exception as e:
                print(f"Download failed for {link}: {e}")
                return None

        for keyword in keywords:
            query = quote_plus(f"filetype:pdf {keyword}")
            url = f"https://www.google.com/search?q={query}"
            print(f"Scraping PDFs from Google search for keyword: {keyword}")
            try:
                links = await asyncio.wait_for(pdf_scraper.scrape_pdf_links(url), timeout=20)
            except Exception as e:
                print(f"Scrape links timeout/failure for keyword '{keyword}': {e}")
                links = []

            links = links[:max_results]

            tasks = [asyncio.create_task(bounded_download(link)) for link in links]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

def download_with_timeout(url: str, timeout_seconds: int = 300) -> dict:
    """Download video with timeout to prevent hanging"""
    result = {"success": False, "message": "Download timeout", "filename": None}
    
    def download_worker():
        try:
            result.update(download_video(url))
        except Exception as e:
            result.update({"success": False, "message": str(e), "filename": None})
    
    # Start download in a separate thread
    thread = threading.Thread(target=download_worker)
    thread.daemon = True
    thread.start()
    
    # Wait for completion or timeout
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        print(f"Download timed out after {timeout_seconds} seconds")
        return {"success": False, "message": f"Download timed out after {timeout_seconds} seconds", "filename": None}
    
    return result

def download_video(url: str) -> dict:
    """Download video from URL and store in MinIO with metadata in MongoDB"""
    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Analyzing video: {url}")
            
            # Progress hook to monitor download
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', 'N/A')
                    speed = d.get('_speed_str', 'N/A')
                    print(f"Downloading... {percent} at {speed}")
                elif d['status'] == 'finished':
                    print(f"Download finished: {d['filename']}")
            
            # Try different format options with timeout
            format_options = [
                'best[height<=720]/best',  # Try 720p first
                'best[height<=480]/best',  # Then 480p
                'best',                    # Then any best quality
                'worst'                    # Finally worst quality as fallback
            ]
            
            for i, format_option in enumerate(format_options):
                try:
                    print(f"Attempt {i+1}: Trying format '{format_option}'")
                    
                    ydl_opts = {
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                        'format': format_option,
                        'noplaylist': True,
                        'writethumbnail': False,
                        'writesubtitles': False,
                        'writeautomaticsub': False,
                        'ignoreerrors': True,
                        'no_warnings': False,
                        'extract_flat': False,
                        'progress_hooks': [progress_hook],
                        'socket_timeout': 30,
                        'retries': 3,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # First, get video info with timeout
                        print("Getting video info...")
                        info = ydl.extract_info(url, download=False)
                        
                        if info is None:
                            print(f"Could not extract info for: {url}")
                            continue
                        
                        title = info.get('title', 'Unknown')
                        duration = info.get('duration', 0)
                        uploader = info.get('uploader') or info.get('channel')
                        upload_date = info.get('upload_date')  # YYYYMMDD
                        extractor = info.get('extractor', 'unknown')
                        webpage_url = info.get('webpage_url', url)
                        
                        print(f"Title: {title}")
                        if duration > 0:
                            print(f"Duration: {duration//60}:{duration%60:02d}")
                        
                        # Download the video with timeout
                        print("Starting download...")
                        ydl.download([url])
                        
                        # Find the downloaded file
                        downloaded_file = None
                        for file in os.listdir(temp_dir):
                            if file.endswith(('.mp4', '.webm', '.mkv')):
                                downloaded_file = os.path.join(temp_dir, file)
                                break
                        
                        if not downloaded_file:
                            raise Exception("Downloaded file not found")
                        
                        # Get file info
                        file_size = os.path.getsize(downloaded_file)
                        filename = os.path.basename(downloaded_file)
                        
                        # Generate unique object name for MinIO
                        object_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        
                        # Upload to MinIO
                        if minio_manager.upload_video(downloaded_file, object_name):
                            # Save metadata to MongoDB
                            video_data = {
                                "url": url,
                                "title": title,
                                "duration": duration,
                                "filename": filename,
                                "file_size": file_size,
                                "minio_object_name": object_name,
                                "meta": {
                                    "source": extractor,
                                    "title": title,
                                    "format": format_option,
                                    "uploader": uploader,
                                    "upload_date": upload_date,
                                    "webpage_url": webpage_url,
                                }
                            }
                            
                            video_id = db_manager.save_video(video_data)
                            
                            print(f"Successfully downloaded and stored: {title}")
                            return {
                                "success": True,
                                "message": f"Successfully downloaded: {title}",
                                "filename": filename,
                                "video_id": video_id
                            }
                        else:
                            raise Exception("Failed to upload video to MinIO")
                        
                except Exception as e:
                    print(f"Attempt {i+1} failed: {str(e)}")
                    if i == len(format_options) - 1:  # Last attempt
                        raise e
                    continue
            
            return {
                "success": False,
                "message": "All download attempts failed",
                "filename": None
            }
            
    except Exception as e:
        print(f"All attempts failed: {str(e)}")
        return {
            "success": False,
            "message": f"Error downloading video: {str(e)}",
            "filename": None
        }

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Video Downloader API with MongoDB & MinIO", "version": "2.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    try:
        # Check MongoDB connection
        db_manager.client.admin.command('ping')
        mongo_status = "connected"
    except Exception as e:
        mongo_status = f"error: {str(e)}"
    
    try:
        # Check MinIO connection
        minio_manager.client.list_buckets()
        minio_status = "connected"
    except Exception as e:
        minio_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "message": "API is running with MongoDB & MinIO",
        "version": "2.0.0",
        "services": {
            "mongodb": mongo_status,
            "minio": minio_status
        }
    }

@app.post("/api/scrape", response_model=ScrapeStatus)
async def scrape_content(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start scraping videos and PDFs from URLs and keywords"""
    try:
        if not request.urls and not request.keywords:
            return ScrapeStatus(status="error", message="No URLs or keywords provided")
        
        tasks_started = []
        
        # Start downloading videos in background with timeout
        if request.urls:
            video_domains = [
                "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
                "facebook.com", "twitter.com", "x.com", "reddit.com"
            ]
            scheduled = 0
            for url in request.urls:
                parsed = urlparse(url)
                path = (parsed.path or "").lower()
                host = (parsed.netloc or "").lower()
                # Skip obvious non-video URLs (direct PDFs)
                if path.endswith('.pdf'):
                    continue
                # Only schedule for known video domains
                if any(domain in host for domain in video_domains):
                    background_tasks.add_task(download_with_timeout, url, 300)  # 5 minute timeout
                    scheduled += 1
            if scheduled:
                tasks_started.append(f"{scheduled} video(s)")
        
        # Start PDF scraping in background
        if request.urls:
            background_tasks.add_task(scrape_pdfs_from_urls, request.urls)
            tasks_started.append("PDFs from URLs")
        
        if request.keywords:
            background_tasks.add_task(scrape_pdfs_by_keywords, request.keywords)
            tasks_started.append("PDFs from keywords")
        
        return ScrapeStatus(
            status="started", 
            message=f"Started scraping: {', '.join(tasks_started)}"
        )
    except Exception as e:
        return ScrapeStatus(status="error", message=str(e))

@app.post("/api/download", response_model=DownloadResponse)
async def download_video_endpoint(request: DownloadRequest):
    try:
        print(f"Downloading video from: {request.url}")
        result = download_video(request.url)
        return DownloadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos", response_model=List[VideoResponse])
async def get_videos():
    """Get all videos from MongoDB"""
    try:
        videos = db_manager.get_all_videos()
        return [VideoResponse(**video) for video in videos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}/download")
async def download_video_file(video_id: str):
    """Download a specific video file from MinIO"""
    try:
        # Get video metadata from MongoDB
        video = db_manager.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        object_name = video.get("minio_object_name")
        if not object_name:
            raise HTTPException(status_code=404, detail="Video file not found in storage")
        
        # Get video data from MinIO
        video_data = minio_manager.download_video(object_name)
        if not video_data:
            raise HTTPException(status_code=404, detail="Video file not found in MinIO")
        
        # Create streaming response
        video_data.seek(0)
        return StreamingResponse(
            io.BytesIO(video_data.read()),
            media_type='video/mp4',
            headers={"Content-Disposition": f"attachment; filename={video['filename']}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pdfs", response_model=List[PDFResponse])
async def get_pdfs():
    """Get all PDFs from MongoDB"""
    try:
        pdfs = db_manager.get_all_pdfs()
        return [PDFResponse(**pdf) for pdf in pdfs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pdfs/{pdf_id}/download")
async def download_pdf_file(pdf_id: str):
    """Download a specific PDF file from MinIO"""
    try:
        # Get PDF metadata from MongoDB
        pdf = db_manager.get_pdf_by_id(pdf_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        object_name = pdf.get("minio_object_name")
        if not object_name:
            raise HTTPException(status_code=404, detail="PDF file not found in storage")
        
        # Get PDF data from MinIO
        pdf_data = minio_manager.download_pdf(object_name)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="PDF file not found in MinIO")
        
        # Create streaming response
        pdf_data.seek(0)
        return StreamingResponse(
            io.BytesIO(pdf_data.read()),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={pdf['filename']}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get storage statistics"""
    try:
        video_count = db_manager.videos.count_documents({})
        pdf_count = db_manager.pdfs.count_documents({})
        
        # Calculate total storage used (from MongoDB metadata)
        video_pipeline = [{"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}]
        video_stats = list(db_manager.videos.aggregate(video_pipeline))
        total_video_size = video_stats[0]["total_size"] if video_stats else 0
        
        pdf_pipeline = [{"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}]
        pdf_stats = list(db_manager.pdfs.aggregate(pdf_pipeline))
        total_pdf_size = pdf_stats[0]["total_size"] if pdf_stats else 0
        
        return {
            "videos": {
                "count": video_count,
                "total_size_bytes": total_video_size,
                "total_size_mb": round(total_video_size / (1024 * 1024), 2)
            },
            "pdfs": {
                "count": pdf_count,
                "total_size_bytes": total_pdf_size,
                "total_size_mb": round(total_pdf_size / (1024 * 1024), 2)
            },
            "total": {
                "files": video_count + pdf_count,
                "total_size_bytes": total_video_size + total_pdf_size,
                "total_size_mb": round((total_video_size + total_pdf_size) / (1024 * 1024), 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reports/generate")
async def generate_reports():
    """Generate reports"""
    return {"status": "success", "message": "Reports generated"}

@app.get("/api/reports/download")
async def download_reports():
    """Download reports"""
    raise HTTPException(status_code=404, detail="Reports not implemented yet")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)