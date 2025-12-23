import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域请求
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 首页路由：支持 Render 的健康检查
@app.api_route("/", methods=["GET", "HEAD"])
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 从 Render 环境变量获取配置
        API_KEY = os.getenv("SILICONFLOW_API_KEY")
        GH_TOKEN = os.getenv("GITHUB_TOKEN")
        GH_REPO = os.getenv("GITHUB_REPO")

        if not API_KEY:
            return JSONResponse({"status": "error", "message": "环境变量中缺失 AI API Key"}, status_code=500)

        # 1. 调用 SiliconFlow API (严格匹配文档参数)
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": "Windows 95 style glitch art, human portrait as a cheap supermarket product, pixelated, yellow price tag on top",
            "image_size": "512x512",
            "batch_size": 1
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(sf_url, json=payload, headers=headers)
        
        # 2. 健壮的错误处理：解决 'str' object has no attribute 'get'
        try:
            res_json = response.json()
        except Exception:
            res_json = response.text

        if response.status_code != 200:
            # 这里的逻辑确保了无论 API 返回什么格式，都能提取出错误文字
            error_msg = res_json.get("message", str(res_json)) if isinstance(res_json, dict) else str(res_json)
            print(f"AI 接口报错详情: {error_msg}")
            return JSONResponse({"status": "error", "message": f"AI服务异常: {error_msg}"}, status_code=500)

        # 3. 提取图片并存档至 GitHub
        ai_img_url = res_json['images'][0]['url']
        final_img_data = requests.get(ai_img_url).content

        g = Github(GH_TOKEN)
        repo = g.get_repo(GH_REPO)
        file_path = f"shelf/item_{uuid.uuid4().hex[:8]}.png"
        repo.create_file(path=file_path, message="New product shelved", content=final_img_data, branch="main")

        return {
            "status": "success", 
            "url": f"https://raw.githubusercontent.com/{GH_REPO}/main/{file_path}"
        }

    except Exception as e:
        print(f"系统运行错误: {str(e)}")
        return JSONResponse({"status": "error", "message": f"执行异常: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
