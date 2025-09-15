from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, JSON
from sqlalchemy.exc import IntegrityError

app = FastAPI(title="Simple Video Downloader API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DownloadRequest(BaseModel):
    url: str

class DownloadResponse(BaseModel):
    success: bool
    message: str
    filename: str = None

class ScrapeRequest(BaseModel):
    urls: List[str] = []
    keywords: List[str] = []

class ScrapeStatus(BaseModel):
    status: str
    message: str

class PDFResponse(BaseModel):
    id: int
    url: str
    local_path: Optional[str] = None
    meta: Dict[str, Any]

# Storage for downloaded videos
downloaded_videos = []
video_counter = 1
pdf_counter = 1

# Database setup
def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

class Storage:
    def __init__(self, db_path: str):
        ensure_dir(os.path.dirname(db_path) or ".")
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        self.meta = MetaData()
        self.videos = Table(
            "videos", self.meta,
            Column("id", Integer, primary_key=True),
            Column("url", String, unique=True, nullable=False),
            Column("local_path", String),
            Column("meta", JSON),
        )
        self.pdfs = Table(
            "pdfs", self.meta,
            Column("id", Integer, primary_key=True),
            Column("url", String, unique=True, nullable=False),
            Column("local_path", String),
            Column("meta", JSON),
        )
        self.meta.create_all(self.engine)

    def save_video(self, url: str, local_path: str, meta: Dict[str, Any]):
        with self.engine.begin() as conn:
            try:
                conn.execute(self.videos.insert(), {"url": url, "local_path": local_path, "meta": meta})
            except IntegrityError:
                print(f"Video {url} already saved.")

    def save_pdf(self, url: str, local_path: str, meta: Dict[str, Any]):
        with self.engine.begin() as conn:
            try:
                conn.execute(self.pdfs.insert(), {"url": url, "local_path": local_path, "meta": meta})
            except IntegrityError:
                print(f"PDF {url} already saved.")

    def get_all_videos(self):
        with self.engine.connect() as conn:
            videos = conn.execute(self.videos.select()).fetchall()
        return [dict(r._mapping) for r in videos]

    def get_all_pdfs(self):
        with self.engine.connect() as conn:
            pdfs = conn.execute(self.pdfs.select()).fetchall()
        return [dict(r._mapping) for r in pdfs]

    def get_pdf_by_id(self, pdf_id: int):
        with self.engine.connect() as conn:
            result = conn.execute(self.pdfs.select().where(self.pdfs.c.id == pdf_id)).fetchone()
            return dict(result._mapping) if result else None

# Initialize storage
storage = Storage("../output/interactive_scraper.db")

# PDF Scraper class
class PDFScraper:
    def __init__(self, client: httpx.AsyncClient, pdf_dir: str, storage: Storage):
        self.client = client
        self.pdf_dir = pdf_dir
        ensure_dir(pdf_dir)
        self.storage = storage

    async def scrape_pdf_links(self, url: str) -> List[str]:
        if "twitter.com" in urlparse(url).netloc:
            print(f"Skipping PDF scraping on Twitter URL: {url}")
            return []

        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf"):
                    full_url = urljoin(url, href)
                    links.append(full_url)
            return links
        except Exception as e:
            print(f"Failed to scrape PDF links from {url}: {e}")
            return []

    async def download_pdf(self, url: str) -> Optional[str]:
        filename = os.path.basename(urlparse(url).path)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        local_path = os.path.join(self.pdf_dir, filename)
        try:
            async with self.client.stream("GET", url) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
            self.storage.save_pdf(url, local_path, {"downloaded": True})
            print(f"Downloaded PDF {url} to {local_path}")
            return local_path
        except Exception as e:
            print(f"Failed to download PDF {url}: {e}")
            return None

# Initialize PDF scraper
pdf_dir = "../output/pdfs"
ensure_dir(pdf_dir)
pdf_scraper = None

async def scrape_pdfs_from_urls(urls: List[str]):
    """Scrape PDFs from given URLs"""
    global pdf_scraper
    if pdf_scraper is None:
        async with httpx.AsyncClient(timeout=30) as client:
            pdf_scraper = PDFScraper(client, pdf_dir, storage)
            for url in urls:
                print(f"Scraping PDFs from URL: {url}")
                pdf_links = await pdf_scraper.scrape_pdf_links(url)
                for pdf_url in pdf_links:
                    await pdf_scraper.download_pdf(pdf_url)

async def scrape_pdfs_by_keywords(keywords: List[str], max_results=5):
    """Scrape PDFs from Google search using keywords"""
    global pdf_scraper
    if pdf_scraper is None:
        async with httpx.AsyncClient(timeout=30) as client:
            pdf_scraper = PDFScraper(client, pdf_dir, storage)
            for keyword in keywords:
                query = quote_plus(f"filetype:pdf {keyword}")
                url = f"https://www.google.com/search?q={query}"
                print(f"Scraping PDFs from Google search for keyword: {keyword}")
                pdf_links = await pdf_scraper.scrape_pdf_links(url)
                for pdf_url in pdf_links[:max_results]:
                    await pdf_scraper.download_pdf(pdf_url)

def load_existing_videos():
    """Load existing videos from output/videos directory on startup"""
    global video_counter, downloaded_videos
    
    download_dir = "../output/videos"
    if not os.path.exists(download_dir):
        return
    
    for file in os.listdir(download_dir):
        if file.endswith(('.mp4', '.webm', '.mkv')):
            file_path = os.path.join(download_dir, file)
            video_info = {
                "id": video_counter,
                "url": "https://youtube.com",  # Unknown URL for existing files
                "title": file.replace('.mp4', '').replace('.webm', '').replace('.mkv', ''),
                "duration": 0,
                "filename": file,
                "path": file_path,
                "local_path": file_path,
                "meta": {"source": "existing", "title": file}
            }
            downloaded_videos.append(video_info)
            video_counter += 1

# Load existing videos on startup
load_existing_videos()

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
        print(f"⏰ Download timed out after {timeout_seconds} seconds")
        return {"success": False, "message": f"Download timed out after {timeout_seconds} seconds", "filename": None}
    
    return result

def download_video(url: str) -> dict:
    """Download video from URL with improved timeout and progress handling"""
    try:
        output_dir = "../output/videos"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"🔍 Analyzing video: {url}")
        
        # Progress hook to monitor download
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', 'N/A')
                speed = d.get('_speed_str', 'N/A')
                print(f"⬇️  Downloading... {percent} at {speed}")
            elif d['status'] == 'finished':
                print(f"✅ Download finished: {d['filename']}")
        
        # Try different format options with timeout
        format_options = [
            'best[height<=720]/best',  # Try 720p first
            'best[height<=480]/best',  # Then 480p
            'best',                    # Then any best quality
            'worst'                    # Finally worst quality as fallback
        ]
        
        for i, format_option in enumerate(format_options):
            try:
                print(f"🔄 Attempt {i+1}: Trying format '{format_option}'")
                
                ydl_opts = {
                    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                    'format': format_option,
                    'noplaylist': True,
                    'writethumbnail': False,
                    'writesubtitles': False,
                    'writeautomaticsub': False,
                    'ignoreerrors': True,
                    'no_warnings': False,
                    'extract_flat': False,
                    'progress_hooks': [progress_hook],
                    'socket_timeout': 30,  # 30 second timeout
                    'retries': 3,  # Retry 3 times
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # First, get video info with timeout
                    print("🔍 Getting video info...")
                    info = ydl.extract_info(url, download=False)
                    
                    if info is None:
                        print(f"❌ Could not extract info for: {url}")
                        continue
                    
                    title = info.get('title', 'Unknown')
                    duration = info.get('duration', 0)
                    
                    print(f"📹 Title: {title}")
                    if duration > 0:
                        print(f"⏱️  Duration: {duration//60}:{duration%60:02d}")
                    
                    # Check available formats
                    formats = info.get('formats', [])
                    print(f"📋 Available formats: {len(formats)}")
                    
                    # Download the video with timeout
                    print("⬇️  Starting download...")
                    ydl.download([url])
                    
                    # Store info
                    global video_counter
                    video_info = {
                        "id": video_counter,
                        "url": url,
                        "title": title,
                        "duration": duration,
                        "filename": f"{title}.mp4",
                        "path": os.path.join(output_dir, f"{title}.mp4"),
                        "local_path": os.path.join(output_dir, f"{title}.mp4"),
                        "meta": {"source": "youtube", "title": title}
                    }
                    downloaded_videos.append(video_info)
                    video_counter += 1
                    
                    print(f"✅ Successfully downloaded: {title}")
                    return {
                        "success": True,
                        "message": f"Successfully downloaded: {title}",
                        "filename": f"{title}.mp4"
                    }
                    
            except Exception as e:
                print(f"❌ Attempt {i+1} failed: {str(e)}")
                if i == len(format_options) - 1:  # Last attempt
                    raise e
                continue
        
        return {
            "success": False,
            "message": "All download attempts failed",
            "filename": None
        }
        
    except Exception as e:
        print(f"❌ All attempts failed: {str(e)}")
        return {
            "success": False,
            "message": f"Error downloading video: {str(e)}",
            "filename": None
        }

@app.get("/")
async def root():
    return {"message": "Simple Video Downloader API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "API is running - UPDATED VERSION", "version": "2.0.0"}

@app.get("/api/debug")
async def debug_info():
    return {
        "downloaded_videos_count": len(downloaded_videos),
        "video_counter": video_counter,
        "directory_exists": os.path.exists("../output/videos"),
        "directory_files": os.listdir("../output/videos") if os.path.exists("../output/videos") else []
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
            for url in request.urls:
                background_tasks.add_task(download_with_timeout, url, 300)  # 5 minute timeout
            tasks_started.append(f"{len(request.urls)} video(s)")
        
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

@app.get("/api/videos")
async def get_videos():
    print(f"🔍 get_videos called - current count: {len(downloaded_videos)}")
    
    # Always check for existing files in output/videos directory
    download_dir = "../output/videos"
    print(f"📁 Checking directory: {download_dir}")
    print(f"📁 Directory exists: {os.path.exists(download_dir)}")
    
    if os.path.exists(download_dir):
        files = os.listdir(download_dir)
        print(f"📁 Found {len(files)} files in directory")
        
        for file in files:
            if file.endswith(('.mp4', '.webm', '.mkv')):
                file_path = os.path.join(download_dir, file)
                print(f"📁 Processing video file: {file}")
                
                # Check if this file is already in our list
                existing = any(v.get("filename") == file for v in downloaded_videos)
                print(f"🔍 File already exists in list: {existing}")
                
                if not existing:
                    global video_counter
                    print(f"➕ Adding new video to list")
                    video_info = {
                        "id": video_counter,
                        "url": "https://youtube.com",
                        "title": file.replace('.mp4', '').replace('.webm', '').replace('.mkv', ''),
                        "duration": 0,
                        "filename": file,
                        "path": file_path,
                        "local_path": file_path,
                        "meta": {"source": "existing", "title": file}
                    }
                    downloaded_videos.append(video_info)
                    video_counter += 1
                    print(f"✅ Added video with ID: {video_counter-1}")
                else:
                    print(f"⏭️  Video already in list, skipping")
    
    print(f"🔍 Final count: {len(downloaded_videos)} videos")
    
    # Return videos with proper structure
    return downloaded_videos

@app.get("/api/downloads")
async def list_downloads():
    """List all downloaded files"""
    download_dir = "../output/videos"
    if not os.path.exists(download_dir):
        return {"files": []}
    
    files = []
    for file in os.listdir(download_dir):
        if file.endswith(('.mp4', '.webm', '.mkv')):
            file_path = os.path.join(download_dir, file)
            files.append({
                "name": file,
                "size": os.path.getsize(file_path),
                "path": file_path
            })
    
    return {"files": files}

# Additional endpoints for frontend compatibility
@app.get("/api/pdfs", response_model=List[PDFResponse])
async def get_pdfs():
    """Get all PDFs from database"""
    try:
        pdfs = storage.get_all_pdfs()
        return [PDFResponse(**pdf) for pdf in pdfs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}/download")
async def download_video_file(video_id: int):
    """Download a specific video file"""
    try:
        # Find the video in our list
        video = next((v for v in downloaded_videos if v.get("id") == video_id), None)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        file_path = video.get("path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type='video/mp4'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pdfs/{pdf_id}/download")
async def download_pdf_file(pdf_id: int):
    """Download a specific PDF file"""
    try:
        # Find the PDF in the database
        pdf = storage.get_pdf_by_id(pdf_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        file_path = pdf.get("local_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type='application/pdf'
        )
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
