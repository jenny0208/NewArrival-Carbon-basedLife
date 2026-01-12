import os
import uuid
import requests
from http import HTTPStatus
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from github import Github 
from starlette.middleware.cors import CORSMiddleware
import dashscope 

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 1. 环境变量配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
GITHUB_REPO = "Jenny0208/NewArrival-Carbon-basedLife"
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/upload")
async def upload_to_shelf(file: UploadFile = File(...)):
    temp_filename = None
    try:
        if not GITHUB_TOKEN:
            return JSONResponse({"status": "error", "message": "GITHUB_TOKEN Missing"}, status_code=401)

        # 1. 保存临时文件 (阿里云需要读取本地路径)
        file_content = await file.read()
        temp_filename = f"temp_{uuid.uuid4()}.png"
        with open(temp_filename, "wb") as f:
            f.write(file_content)

        # 2. 准备提示词 (高清监控风格)
        final_prompt = (
            "(masterpiece), (clear face:1.5), (detailed facial features:1.4), (sharp focus:1.3), "
            "(hanging from a horizontal metal bar:1.4), (arms STRAIGHT UP over head:1.4), "
            "body suspended in air, limp body posture, "
            "(simple pure white background:1.6), (flat lighting), (no shadows), "
            "surveillance camera style, cold atmosphere, "
            "pale skin, lifeless expression, realistic photo."
        )

        # 3. 🔴 关键修改：使用 MultiModalConversation 调用 Qwen-Image-Edit
        # 通义千问-Image-Edit 的调用方式是“对话”式的
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"file://{os.path.abspath(temp_filename)}"}, # 传入本地图片路径
                    {"text": final_prompt} # 传入提示词
                ]
            }
        ]

        rsp = dashscope.MultiModalConversation.call(
            model='qwen-image-edit',  # 修正后的正确模型 ID
            messages=messages
        )

        # 4. 处理返回结果
        if rsp.status_code == HTTPStatus.OK:
            # Qwen 的返回结构通常在 output.choices[0].message.content 里的 image 字段
            # 或者直接是 output.choices[0].message.content[0]['image']
            # 我们先尝试通用的解析方式
            try:
                # 尝试获取图片内容
                content_list = rsp.output.choices[0].message.content
                ai_img_url = ""
                for item in content_list:
                    if 'image' in item:
                        ai_img_url = item['image']
                        break
                
                if not ai_img_url:
                     raise Exception("No image URL in response")

                print(f"AI Success: {ai_img_url}")
                img_content = requests.get(ai_img_url).content
            except Exception as parse_err:
                 print(f"Parse Error: {rsp}")
                 return JSONResponse({"status": "error", "message": f"Parse Error: {str(parse_err)}"}, status_code=500)
        else:
            return JSONResponse({"status": "error", "message": f"AI Error: {rsp.message}"}, status_code=500)

        # 5. 上传 GitHub (保持不变)
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        item_id = uuid.uuid4().hex[:8]
        file_path = f"shelf/item_{item_id}.png"
        repo.create_file(path=file_path, message=f"Shelved {item_id}", content=img_content, branch="main")

        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
        return {"status": "success", "url": raw_url}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
        
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
