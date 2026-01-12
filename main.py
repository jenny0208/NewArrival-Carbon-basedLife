import os
import uuid
import requests
from http import HTTPStatus
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware
import dashscope # 新增：阿里云SDK

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 1. 环境变量配置 ---
# 动态读取 Render 环境变量
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"

# 🔴 改动点：读取阿里云 API Key (请确保在 Render 环境变量中设置了 DASHSCOPE_API_KEY)
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

@app.get("/")
async def read_index():
    # 保持原样：返回前端页面
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    temp_filename = None # 初始化临时文件名变量
    try:
        # 保持原样：检查 GitHub Token
        if not GITHUB_TOKEN:
            return JSONResponse({"status": "error", "message": "GITHUB_TOKEN Missing"}, status_code=401)

        # 🔴 改动点：保存用户上传的文件到本地 (图生图必须步骤)
        # 阿里云 SDK 需要读取本地文件路径，不能直接传内存流
        file_content = await file.read()
        temp_filename = f"temp_{uuid.uuid4()}.png"
        with open(temp_filename, "wb") as f:
            f.write(file_content)

        # --- 提示词优化 (使用我们在对话中确认的【高清保脸版】) ---
        # 这一版去掉了 pixelated 等模糊词，强调了 clear face 和 white background
        final_prompt = (
            "(masterpiece), (clear face:1.5), (detailed facial features:1.4), (sharp focus:1.3), "
            "(hanging from a horizontal metal bar:1.4), (arms STRAIGHT UP over head:1.4), "
            "body suspended in air, limp body posture, "
            "(simple pure white background:1.6), (flat lighting), (no shadows), "
            "surveillance camera style, cold atmosphere, "
            "pale skin, lifeless expression, realistic photo."
        )

        # 🔴 改动点：调用阿里云 DashScope API
        # 模型说明：API 中 'wanx-style-repainting-v1' 对应控制台的 '通义万相-风格重绘'
        # 这是实现 '通义千问-Image-Edit' 功能的标准 SDK 接口
        rsp = dashscope.ImageSynthesis.call(
            model='wanx-style-repainting-v1', 
            input_image=temp_filename, # 传入刚才保存的图片
            prompt=final_prompt,
            style_strength_ratio=0.6, # 相似度控制：0.6 是平衡点，既改动作又保轮廓
            n=1,
            size='1024*1024'
        )

        # 🔴 改动点：处理阿里云的返回结果
        if rsp.status_code == HTTPStatus.OK:
            # 获取生成图片的 URL
            ai_img_url = rsp.output.results[0].url
            
            # 下载图片内容 (保持原逻辑：下载后传给 GitHub)
            img_content = requests.get(ai_img_url).content
        else:
            # 如果出错，返回错误信息
            return JSONResponse({"status": "error", "message": f"AI Error: {rsp.message}"}, status_code=500)

        # --- 以下 GitHub 上传逻辑完全保持原样 ---
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
        
    finally:
        # 🔴 改动点：清理临时文件
        # 每次请求结束后，删除服务器上的临时图片，防止空间占满
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
