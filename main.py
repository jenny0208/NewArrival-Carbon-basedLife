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

# --- 硬编码配置区域 ---
# SiliconFlow API Key
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"

# 你提供的 GitHub Token
GITHUB_TOKEN = "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"

# 你的仓库名
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
# --------------------

@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 调用 SiliconFlow API (严格匹配你提供的文档)
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            # 匹配汇报稿：写实风格、统一白底、悬挂姿态、商品化感
            "prompt": "Full body realistic photography of a person hanging from a bar with arms raised above head, pull-up posture, arms reaching up, professional studio lighting, pure white background, high resolution, minimalist commodity aesthetic, slightly unsettling but clean",
            "image_size": "512x512",
            "batch_size": 1,
            "num_inference_steps": 20
        }
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(sf_url, json=payload, headers=headers)
        res_json = response.json()

        if response.status_code != 200:
            error_detail = res_json.get("message", str(res_json)) if isinstance(res_json, dict) else str(res_json)
            return JSONResponse({"status": "error", "message": f"AI服务报错: {error_detail}"}, status_code=500)

        # 获取生成的图片 URL
        ai_img_url = res_json['images'][0]['url']
        img_data = requests.get(ai_img_url).content

        # 2. 存档至 GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # 随机生成文件名
        file_name = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        
        # 提交到仓库
        repo.create_file(
            path=file_name, 
            message="Asset shelving: carbon-based life-form", 
            content=img_data, 
            branch="main"
        )

        # 返回图片在 GitHub 上的原始链接
        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_name}"
        }

    except Exception as e:
        print(f"系统运行错误: {str(e)}")
        return JSONResponse({"status": "error", "message": f"程序执行异常: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Render 默认端口通常为 10000
    uvicorn.run(app, host="0.0.0.0", port=10000)
