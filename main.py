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

        # 1. 保存用户上传的图片为临时文件
        file_content = await file.read()
        temp_filename = f"temp_{uuid.uuid4()}.png"
        with open(temp_filename, "wb") as f:
            f.write(file_content)

        # 2. 准备提示词 (保留了高清、监控风格、白色背景的设定)
       # 2. 准备提示词 (加强版：强制把手举起来)
        final_prompt = (
            "(change pose:1.6), (arms reaching straight UP:1.7), (grabbing a horizontal bar above head:1.6), "
            "(arms vertical), (hanging by hands), "
            "body suspended in air, feet off the ground, limp legs, "
            "(masterpiece), (clear face:1.5), (simple pure white background:1.6), "
            "(flat lighting), surveillance camera style, realistic photo."
        )

        # 3. 🔴 核心修改：使用你指定的模型 ID
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"file://{os.path.abspath(temp_filename)}"}, 
                    {"text": final_prompt} 
                ]
            }
        ]

        # 根据你提供的文档，该模型属于 qwen-image-edit-plus 系列
        rsp = dashscope.MultiModalConversation.call(
            model='qwen-image-edit-plus-2025-12-15',  # 📍 已锁定为你提供的版本
            messages=messages
        )

        # 4. 处理返回结果
        if rsp.status_code == HTTPStatus.OK:
            try:
                # 解析 Qwen 的返回结构
                content = rsp.output.choices[0].message.content
                ai_img_url = ""
                # 遍历返回内容找到图片链接
                for item in content:
                    if isinstance(item, dict) and 'image' in item:
                        ai_img_url = item['image']
                        break
                
                if not ai_img_url:
                     raise Exception("No image URL found in AI response")

                print(f"AI Success: {ai_img_url}")
                img_content = requests.get(ai_img_url).content
                
            except Exception as parse_err:
                 print(f"Parse Error: {rsp}")
                 return JSONResponse({"status": "error", "message": f"AI Response Parse Error: {str(parse_err)}"}, status_code=500)
        else:
            print(f"AI Error: {rsp.code}, {rsp.message}")
            return JSONResponse({"status": "error", "message": f"Aliyun Error: {rsp.message}"}, status_code=500)

        # 5. 上传 GitHub
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
