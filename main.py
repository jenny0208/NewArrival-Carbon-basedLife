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

# --- 硬编码配置区域 (直接写入你的信息) ---
# 你的 SiliconFlow API Key
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"

# 你的 GitHub Token (请填入你之前生成的那个 sk- 或 ghp_ 开头的 Token)
# 如果你这里不填，还是会报 None 错误
GITHUB_TOKEN = "你的GITHUB_TOKEN" 

# 你的仓库全名
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
# --------------------------------------

@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 调用 AI 接口
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            # 融入了你汇报稿中的视觉设定：写实、白底、悬挂姿态
            "prompt": "Full body realistic photography of a person hanging from a bar with arms raised above head, pull-up posture, professional studio lighting, pure white background, high resolution, commodity aesthetic",
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
            return JSONResponse({"status": "error", "message": f"AI生成失败: {str(res_json)}"}, status_code=500)

        # 2. 获取图片
        ai_img_url = res_json['images'][0]['url']
        img_response = requests.get(ai_img_url)
        if img_response.status_code != 200:
            return JSONResponse({"status": "error", "message": "无法从AI服务器获取图片数据"}, status_code=500)
        
        final_img_data = img_response.content

        # 3. 存档至 GitHub
        # 这里的 GITHUB_TOKEN 如果是 None 就会报你刚才那个错
        if not GITHUB_TOKEN or GITHUB_TOKEN == "你的GITHUB_TOKEN":
            return JSONResponse({"status": "error", "message": "代码中未填写 GITHUB_TOKEN"}, status_code=500)

        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        
        repo.create_file(
            path=file_path, 
            message="New product shelved", 
            content=final_img_data, 
            branch="main"
        )

        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
        }

    except Exception as e:
        # 如果还是报错，这里会打印具体的错误信息，而不仅仅是 None
        print(f"致命错误详情: {str(e)}")
        return JSONResponse({"status": "error", "message": f"执行异常: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
