import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 路由：支持首页访问
@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 变量校验
        sk_key = os.getenv("SILICONFLOW_API_KEY")
        gh_token = os.getenv("GITHUB_TOKEN")
        gh_repo = os.getenv("GITHUB_REPO") # 格式: 用户名/仓库名

        # 2. 调用 AI (FLUX.1-schnell)
        sf_res = requests.post(
            "https://api.siliconflow.cn/v1/images/generations",
            headers={"Authorization": f"Bearer {sk_key}"},
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": "Windows 95 style glitch art, human portrait as a supermarket product, thermal printer style, dithered pixel art",
                "width": 512, "height": 512
            }
        )
        # 捕获 Token 无效等错误
        if sf_res.status_code != 200:
            return JSONResponse({"status": "error", "message": f"AI服务异常: {sf_res.json().get('message')}"}, status_code=500)

        ai_url = sf_res.json()['images'][0]['url']
        img_data = requests.get(ai_url).content

        # 3. 存档 GitHub
        g = Github(gh_token)
        repo = g.get_repo(gh_repo)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        repo.create_file(path=file_path, message="Add new item", content=img_data, branch="main")

        return {"status": "success", "url": f"https://raw.githubusercontent.com/{gh_repo}/main/{file_path}"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
