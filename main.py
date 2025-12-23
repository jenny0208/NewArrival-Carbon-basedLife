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

# --- 环境变量 (请确保在 Render 后台准确设置) ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # 格式必须为: 用户名/仓库名

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
        # 1. 读取上传图片
        contents = await file.read()
        
        # 2. 调用 SiliconFlow AI
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        sf_payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": "Windows 95 style glitch art, portrait as a cheap supermarket commodity, pixelated, dithered, low-fi aesthetic",
            "width": 512, "height": 512
        }
        sf_headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        sf_res = requests.post(sf_url, json=sf_payload, headers=sf_headers)
        res_json = sf_res.json()

        # 错误排查：如果 AI 没有生成图片，在日志打印原因
        if sf_res.status_code != 200:
            print(f"AI 接口报错: {res_json}")
            return JSONResponse({"status": "error", "message": "AI 生成失败"}, status_code=500)

        ai_img_url = res_json['images'][0]['url']
        final_img_data = requests.get(ai_img_url).content

        # 3. 通过 GitHub API 存档
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        file_name = f"carbon_life_{uuid.uuid4().hex[:8]}.png"
        path = f"shelf/{file_name}"
        
        # 将二进制图片存入仓库的 shelf 文件夹
        repo.create_file(path=path, message="New Item Shelved", content=final_img_data, branch="main")

        return {"status": "success", "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"}
    
    except Exception as e:
        print(f"致命错误详情: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
