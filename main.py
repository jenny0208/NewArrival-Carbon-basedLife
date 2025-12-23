import os
import uuid
import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from github import Github
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许跨域（防止前端调用报错）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 环境变量配置 (请在 Render 的 Environment 面板设置) ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO") # 格式: "用户名/仓库名"

# 静态文件托管：确保你的 index.html, style.css 等在根目录
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def read_index():
    # 访问根域名时直接返回你的 Win95 首页
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    try:
        # 1. 接收并处理上传图片
        contents = await file.read()
        
        # 2. 调用 SiliconFlow AI 接口进行“数字化变异”
        # 我们使用 FLUX 这种强力模型来生成带 Meme 感的图像
        sf_url = "https://api.siliconflow.cn/v1/images/generations"
        
        # 这里是针对《当代影像的语言表达》设计的提示词
        # 强调：Win95 风格、低画质、像素感、带价格标签、被消费的碳基生命
        prompt = (
            "A low-resolution Windows 95 style digital artifact, "
            "glitch art aesthetic, a human face transformed into a cheap commodity, "
            "with a red price tag saying '$0.50', lo-fi photography, "
            "dithered pixels, internet meme culture vibe."
        )

        sf_payload = {
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt,
            "num_inference_steps": 4, # Schnell 模型 4 步即可，速度快
            "width": 512,
            "height": 512
        }
        
        sf_headers = {
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }

        # 发送请求给 AI
        sf_response = requests.post(sf_url, json=sf_payload, headers=sf_headers)
        sf_response.raise_for_status()
        result = sf_response.json()
        
        # 获取 AI 生成后的图片
        generated_image_url = result['images'][0]['url']
        final_img_data = requests.get(generated_image_url).content

        # 3. 将影像“上架”至 GitHub 仓库
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # 自动生成文件名，存放在 shelf 文件夹下
        file_path = f"shelf/carbon_life_{uuid.uuid4().hex[:8]}.png"
        
        # 提交到 GitHub (这步就是你说的“上架”)
        repo.create_file(
            path=file_path,
            message=f"New Arrival: {file_path} put on shelf",
            content=final_img_data,
            branch="main"
        )

        # 4. 返回结果给前端
        # 这样你的 Win95 弹窗就能显示出“上架成功”和对应的图片了
        return JSONResponse({
            "status": "success",
            "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}",
            "original_filename": file.filename,
            "price": "￥0.50",
            "message": "碳基生命数字化完成，已存入云端仓库。"
        })

    except Exception as e:
        print(f"Deployment Error: {str(e)}")
        return JSONResponse({
            "status": "error", 
            "message": "服务器正在打瞌睡（超时或配置错误），请稍后再试。"
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Render 要求的启动方式
    uvicorn.run(app, host="0.0.0.0", port=10000)
