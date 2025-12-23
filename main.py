import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 关键修改：从系统环境读取，不留痕迹 ---
# 这样 GitHub 就不会因为扫描到明文 Token 而把你的 Key 杀了
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"

@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 增加环境校验日志
        if not GITHUB_TOKEN:
            return JSONResponse({"status": "error", "message": "环境变量 GITHUB_TOKEN 未找到，请在 Render 设置"}, status_code=500)

        # 1. 调用 AI 生成
        response = requests.post(
            "https://api.siliconflow.cn/v1/images/generations",
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": "Full body realistic photography of a person hanging from a bar, arms raised, pull-up posture, pure white background, low-fi aesthetic",
                "image_size": "512x512",
                "batch_size": 1
            },
            headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
        )
        
        # 2. 获取图片
        ai_img_url = response.json()['images'][0]['url']
        img_data = requests.get(ai_img_url).content

        # 3. 存档至 GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        
        repo.create_file(path=file_path, message="Item added to shelf", content=img_data, branch="main")

        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
        }

    except Exception as e:
        return JSONResponse({"status": "error", "message": f"系统异常: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
