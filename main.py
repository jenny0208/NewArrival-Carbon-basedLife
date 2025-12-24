import os
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 动态读取 Render 环境变量
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
SILICONFLOW_API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        if not GITHUB_TOKEN:
            return JSONResponse({"status": "error", "message": "GITHUB_TOKEN Missing"}, status_code=401)

        # --- 核心提示词优化 ---
        # 1. 移除了 high resolution, highly detailed 等词汇
        # 2. 加入了 low quality, cctv, amateur photography, pixelated 等词汇来压低画质
        # 3. 强化正面和面部特征保留的暗示
        low_fi_prompt = (
            "Full body front view of the person from the photo, facing camera directly, "
            "arms raised hanging from a horizontal bar, pull-up posture, straight legs, "
            "keep the same face and identity, basic facial features, neutral expression, "
            "pure white background, amateur CCTV photography, low quality, low resolution, "
            "slightly blurry, 2010s internet meme aesthetic, overexposed lighting"
        )

        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": low_fi_prompt,
            "image_size": "512x512", # 保持 512 分辨率，不向上扩图
            "batch_size": 1
        }
        headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }

        # 生成影像
        sf_res = requests.post(sf_url, json=payload, headers=headers)
        if sf_res.status_code != 200:
            return JSONResponse({"status": "error", "message": "AI Error"}, status_code=500)

        ai_img_url = sf_res.json()['images'][0]['url']
        img_content = requests.get(ai_img_url).content

        # 2. 存档至 GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        item_id = uuid.uuid4().hex[:8]
        file_path = f"shelf/item_{item_id}.png"
        
        repo.create_file(path=file_path, message=f"Shelved {item_id}", content=img_content, branch="main")

        # 3. 返回 Raw 链接
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
        return {"status": "success", "url": raw_url}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
