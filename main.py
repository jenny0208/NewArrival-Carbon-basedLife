import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域请求，确保前端能连通
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 配置区域 (关键：不再硬编码 Token) ---
# 请在 Render 后台的环境变量 (Environment) 中添加一个 Key 叫 GITHUB_TOKEN
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"

@app.get("/")
@app.head("/")
async def read_index():
    # 确保 index.html 在根目录
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 验证 Token 是否加载成功
        if not GITHUB_TOKEN:
            return JSONResponse({
                "status": "error", 
                "message": "GITHUB_TOKEN 缺失。原因：GitHub 自动封禁了代码中的 Token。解决：请在 Render 的 Environment 页面手动设置 GITHUB_TOKEN 变量。"
            }, status_code=401)

        # 2. 调用 SiliconFlow AI 接口
        # 提示词融入了你的“悬挂”和“商品化”语境
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": "Full body realistic photography of a person hanging from a bar, arms raised, pull-up posture, professional studio lighting, pure white background, low-fi meme aesthetic",
            "image_size": "512x512",
            "batch_size": 1
        }
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }

        log_msg = "正在异化样本..."
        sf_res = requests.post(sf_url, json=payload, headers=headers)
        
        if sf_res.status_code != 200:
            return JSONResponse({"status": "error", "message": f"AI 引擎响应错误: {sf_res.text}"}, status_code=500)

        ai_img_url = sf_res.json()['images'][0]['url']
        
        # 3. 下载 AI 生成的图片内容
        img_content = requests.get(ai_img_url).content

        # 4. 存档至 GitHub (实现云存储)
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # 生成一个唯一的货位 ID
        item_id = uuid.uuid4().hex[:8]
        file_path = f"shelf/item_{item_id}.png"
        
        # 提交文件到仓库
        repo.create_file(
            path=file_path, 
            message=f"Archive: item {item_id} shelved", 
            content=img_content, 
            branch="main"
        )

        # 5. 返回 Raw 图片地址给前端展示
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
        
        return {
            "status": "success", 
            "url": raw_url,
            "id": item_id
        }

    except Exception as e:
        return JSONResponse({"status": "error", "message": f"系统崩溃: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Render 默认端口通常为 10000
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
