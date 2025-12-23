import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 静态首页路由
@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 核心配置（建议从 Render 环境变量读取，不要直接写死在代码推送到 GitHub）
        # 如果你一定要写死，请确保 GitHub 仓库是 Private 私有的
        API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm" 
        GH_TOKEN = "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"
        GH_REPO = "Jenny0208/NewArrival-Carbon-basedLife"

        # 2. 调用 SiliconFlow 图像生成 API
        # 严格匹配文档中的 /images/generations 接口
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell", 
            "prompt": "Full body realistic photography of a person hanging from a bar with arms raised above head, pull-up posture, pure white background, commodity aesthetic",
            "image_size": "512x512", # 严格匹配文档要求的 widthxheight 格式
            "batch_size": 1
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(sf_url, json=payload, headers=headers)
        
        # 安全解析响应，防止 'str' object has no attribute 'get' 报错
        try:
            res_json = response.json()
        except:
            return JSONResponse({"status": "error", "message": f"API 返回了非 JSON 错误: {response.text}"}, status_code=500)

        if response.status_code != 200:
            error_msg = res_json.get("message", "未知错误") if isinstance(res_json, dict) else str(res_json)
            return JSONResponse({"status": "error", "message": f"AI生成失败: {error_msg}"}, status_code=500)

        # 3. 获取图片并上传至 GitHub
        ai_img_url = res_json['images'][0]['url']
        img_data = requests.get(ai_img_url).content

        g = Github(GH_TOKEN)
        repo = g.get_repo(GH_REPO)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        
        repo.create_file(path=file_path, message="New product shelved", content=img_data, branch="main")

        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GH_REPO}/main/{file_path}"
        }

    except Exception as e:
        return JSONResponse({"status": "error", "message": f"系统异常: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
