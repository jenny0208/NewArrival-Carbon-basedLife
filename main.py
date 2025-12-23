import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 直接写入 API KEY ---
# 请注意：如果你将代码推送到公开仓库，这个 Key 很快就会失效
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"
# -----------------------

@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 获取 GitHub 配置（这两个建议还是留在 Render 环境变量里，或者你也按下面格式写死）
        GH_TOKEN = os.getenv("GITHUB_TOKEN")
        GH_REPO = os.getenv("GITHUB_REPO")

        # 1. 调用 SiliconFlow API
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            # 根据你的研究稿，加入了“悬挂姿态”和“纯白背景”的描述
            "prompt": "Full body photo of a person hanging from a bar with arms raised above head, pull-up posture, professional photography, white background, glitch art style, supermarket product aesthetic",
            "image_size": "512x512",
            "batch_size": 1
        }
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(sf_url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            error_msg = res_json.get("message", str(res_json)) if isinstance(res_json, dict) else str(res_json)
            return JSONResponse({"status": "error", "message": f"AI服务异常: {error_msg}"}, status_code=500)

        # 2. 提取图片 URL
        ai_img_url = res_json['images'][0]['url']
        final_img_data = requests.get(ai_img_url).content

        # 3. 存档至 GitHub
        g = Github(GH_TOKEN)
        repo = g.get_repo(GH_REPO)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        repo.create_file(path=file_path, message="New product shelved", content=final_img_data, branch="main")

        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GH_REPO}/main/{file_path}"
        }

    except Exception as e:
        return JSONResponse({"status": "error", "message": f"执行异常: {str(e)}"}, status_code=500)
