import os
import uuid
import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from github import Github # 确保 requirements.txt 里有 PyGithub
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 环境变量 (在 Render 后台设置) ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO") 

# 托管静态文件
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/gallery")
async def read_gallery():
    return FileResponse('gallery.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 读取上传图
        contents = await file.read()
        base64_img = base64.b64encode(contents).decode('utf-8')

        # 2. 调用 AI (SiliconFlow)
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        sf_payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": "Windows 95 style glitch art, human portrait turned into a cheap supermarket commodity, pixelated, dithered, with a price tag, low-fi aesthetic",
            "width": 512, "height": 512
        }
        sf_headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}
        
        sf_res = requests.post(sf_url, json=sf_payload, headers=sf_headers)
        ai_img_url = sf_res.json()['images'][0]['url']
        final_img_data = requests.get(ai_img_url).content

        # 3. 存档至 GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        file_name = f"carbon_life_{uuid.uuid4().hex[:8]}.png"
        path = f"shelf/{file_name}"
        
        repo.create_file(path=path, message="New Arrival", content=final_img_data, branch="main")

        return {"status": "success", "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
