from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TIKWM_API = "https://www.tikwm.com/api/"
TIKWM_TOKEN = "461f38e6167add80420c4369d13de148"

class DownloadRequest(BaseModel):
    url: str

def is_valid_tiktok(url: str) -> bool:
    pattern = r'(https?://)?(www.|vm.|vt.)?tiktok.com/.+'
    return bool(re.match(pattern, url))

@app.post("/api/info")
async def get_info(req: DownloadRequest):
    if not is_valid_tiktok(req.url):
        raise HTTPException(status_code=400, detail="Invalid TikTok link")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                TIKWM_API,
                data={"url": req.url, "hd": "1", "token": TIKWM_TOKEN},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = resp.json()
            if data.get("code") != 0:
                raise HTTPException(status_code=400, detail=data.get("msg", "Error"))
            video = data["data"]
            video_url = video.get("hdplay") or video.get("play") or video.get("wmplay")
            return JSONResponse({
                "title": video.get("title", ""),
                "thumbnail": video.get("cover", ""),
                "duration": video.get("duration", 0),
                "video_url": f"/api/proxy?url={video_url}",
                "direct_url": video_url
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/proxy")
async def proxy_video(url: str):
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.tiktok.com/"
            })
            return StreamingResponse(
                resp.aiter_bytes(),
                media_type="video/mp4",
                headers={"Content-Disposition": "attachment; filename=tiktok_video.mp4"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.get("/")
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
