# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
import httpx
from typing import Dict, Any
import urllib.parse

from app.api.auth import get_current_user
from app.services.extractor import extract_media_info
from app.services.cache import media_cache
from app.db.mongodb import get_database

router = APIRouter()

@router.get("/extract")
async def extract_media(
    url: str = Query(..., description="The media URL from TikTok, YouTube, or Facebook"),
    format_type: str = Query("video", description="Choose 'video' or 'audio'"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    db = get_database()
    users_collection = db.get_collection("users")

    # 1. Check download limits
    is_premium = current_user.get("is_premium", False)
    if not is_premium:
        daily_downloads = current_user.get("daily_downloads", 0)
        if daily_downloads >= 5:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Daily download limit reached."
            )

    # 2. Check Cache
    cached_data = await media_cache.get(url=url, format_type=format_type)
    
    if cached_data:
        # Generate proxy URL for cached data too
        video_title = cached_data.get('title', 'video').replace(" ", "_")
        encoded_url = urllib.parse.quote(cached_data['direct_url'])
        proxy_url = f"/api/download?video_url={encoded_url}&title={video_title}"
        return {"source": "cache", "data": cached_data, "download_proxy_url": proxy_url}

    # 3. Extract Media Info
    extraction_result = await extract_media_info(url=url, format_type=format_type)
    
    if not extraction_result.get("success"):
        raise HTTPException(status_code=400, detail=extraction_result.get("error"))

    # 4. Save to Cache
    await media_cache.set(url=url, format_type=format_type, data=extraction_result)

    # 5. Update Daily Download Count
    if not is_premium:
        await users_collection.update_one({"_id": current_user["_id"]}, {"$inc": {"daily_downloads": 1}})

    # 6. Generate the Magic Proxy Link
    video_title = extraction_result.get('title', 'video').replace(" ", "_")
    # We encode the direct_url so it can be passed safely as a parameter
    encoded_url = urllib.parse.quote(extraction_result['direct_url'])
    proxy_url = f"/api/download?video_url={encoded_url}&title={video_title}"

    return {
        "source": "extractor",
        "data": extraction_result,
        "download_proxy_url": proxy_url
    }

@router.get("/download")
async def download_video(
    video_url: str = Query(...),
    title: str = Query("video")
):
    """
    Robust streaming proxy to bypass YouTube's 0B download issue.
    Includes status checking and error handling.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
    }

    client = httpx.AsyncClient(verify=False, timeout=None)
    try:
        request = client.build_request("GET", video_url, headers=headers)
        upstream = await client.send(request, stream=True, follow_redirects=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Failed to fetch upstream video: {exc}") from exc

    if upstream.status_code not in (200, 206):
        error_text = (await upstream.aread())[:200].decode("utf-8", errors="ignore")
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail=f"Upstream returned status {upstream.status_code}. {error_text}",
        )

    async def stream_video():
        try:
            async for chunk in upstream.aiter_bytes(chunk_size=1024 * 64):
                if chunk:
                    yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    # বাংলা নাম সাপোর্ট করার জন্য হেডার ফিক্স
    safe_filename = urllib.parse.quote(f"{title}.mp4")
    content_disposition = f"attachment; filename*=UTF-8''{safe_filename}"

    return StreamingResponse(
        stream_video(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": content_disposition,
            "Cache-Control": "no-cache"
        }
    )