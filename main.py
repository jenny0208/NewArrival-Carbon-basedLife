import os
import uuid
import base64
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域，防止前端请求被拦截
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 环境变量 (从系统获取) ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO") 

# 首页路由：支持 GET（展示页面）和 HEAD（Render 健康检查）
@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

# 货架页路由
@app.get("/gallery")
async def read_gallery():
    return FileResponse('gallery.html')

# 核心处理接口
@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 读取上传图片并转为 Base64（供 AI 模型使用）
        contents = await file.read()
        
        # 2. 调用 SiliconFlow AI (FLUX.1-schnell)
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        sf_payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": "Windows 95 style glitch art, portrait as a cheap supermarket commodity, pixelated, dithered, low-fi aesthetic",
            "width": 512, "height": 512
        }
        sf_headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}
        
        sf_res = requests.post(sf_url, json=sf_payload, headers=sf_headers)
        ai_img_url = sf_res.json()['images'][0]['url']
        final_img_data = requests.get(ai_img_url).content

        # 3. 通过 GitHub API 存档
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        file_name = f"carbon_life_{uuid.uuid4().hex[:8]}.png"
        path = f"shelf/{file_name}"
        
        # 将二进制图片存入仓库的 shelf 文件夹
        repo.create_file(path=path, message="New Item Shelved", content=final_img_data, branch="main")

        # 返回成功状态及图片的 Raw 访问链接
        return {"status": "success", "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"}
    
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Render 部署必须监听 0.0.0.0 和 10000 端口
    uvicorn.run(app, host="0.0.0.0", port=10000)
