# ©2026 VIDO Mahin Ltd develop by (Tanvir)

import yt_dlp
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _extract_sync(url: str, format_type: str) -> Dict[str, Any]:
    """
    Synchronous function to perform the actual extraction using yt-dlp.
    Configured to bypass basic bot protections and return direct URLs.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'simulate': True,           # Do not download the video files to the server
        'forceurl': True,           # Force printing of direct URLs
        'noplaylist': True,         # Only download a single video, not playlists
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate'
        }
    }

    # Format selection based on user request (Video vs Audio)
    if format_type.lower() == "audio":
        ydl_opts['format'] = 'bestaudio/best'
    else:
        # Try to get the best video format with audio combined, fallback to best single file
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        
        direct_url = info_dict.get('url', '')
        
        # If the main URL is missing, search inside requested_formats
        if not direct_url and 'requested_formats' in info_dict:
            for req_format in info_dict['requested_formats']:
                if 'url' in req_format:
                    direct_url = req_format['url']
                    break

        return {
            "success": True,
            "title": info_dict.get('title', 'Unknown Title'),
            "thumbnail": info_dict.get('thumbnail', ''),
            "duration": info_dict.get('duration', 0),
            "platform": info_dict.get('extractor_key', 'Unknown'),
            "direct_url": direct_url,
            "format_requested": format_type
        }

async def extract_media_info(url: str, format_type: str = "video") -> Dict[str, Any]:
    """
    Runs the synchronous yt-dlp extraction in an asynchronous event loop
    to prevent blocking the FastAPI server during multiple user requests.
    """
    try:
        logger.info(f"Extracting info for URL: {url} with format: {format_type}")
        loop = asyncio.get_event_loop()
        
        # Run the synchronous extraction in a background thread
        result = await loop.run_in_executor(None, _extract_sync, url, format_type)
        return result
        
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp Download Error: {str(e)}")
        return {
            "success": False, 
            "error": "Failed to process URL. The link might be invalid, private, or protected."
        }
    except Exception as e:
        logger.error(f"Unexpected Extraction Error: {str(e)}")
        return {
            "success": False, 
            "error": "Internal Server Error occurred during media extraction."
        }