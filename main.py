import base64
import os
import time
import requests
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from github import Github  # 确保已执行 pip install PyGithub

# --- 核心配置区 ---
API_KEY = "sk-qrzogtjfeldbgjyntrdavnbbqmwewybqxlqzdffbswdxhtrm"
MODEL_ID = "Qwen/Qwen-Image-Edit" 

# GitHub 免费存储配置
GH_TOKEN = "你的GitHub_Token" # 记得填入你的 Token
GH_REPO_NAME = "你的用户名/my-racked-assets" # 你的仓库名

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 初始化 GitHub 客户端
g = Github(GH_TOKEN)
repo = g.get_repo(GH_REPO_NAME)

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    try:
        # 1. 读取并转换图片
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # 2. 艺术指令
        prompt = (
            "A realistic studio photography of the person hanging from a shelf rack. "
            "Arms are spread wide and raised high, hands grasping hooks. "
            "Pull-up posture, legs dangling. Pure white background."
        )

        # 3. 请求 SiliconFlow
        payload = {
            "model": MODEL_ID,
            "prompt": prompt,
            "image": f"data:{file.content_type};base64,{base64_image}"
        }
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

        # 尝试标准编辑路径
        target_url = "https://api.siliconflow.cn/v1/image/editing"
        response = requests.post(target_url, json=payload, headers=headers, timeout=60)

        if response.status_code == 200:
            res_data = response.json()
            img_url = res_data.get('images', [{}])[0].get('url') or res_data.get('data', [{}])[0].get('url')
            
            if img_url:
                # 4. 下载并同步到 GitHub 仓库（实现免费云端化）
                img_content = requests.get(img_url).content
                filename = f"asset_{int(time.time())}.png"
                
                # 提交文件到仓库根目录
                repo.create_file(filename, f"Add asset {filename}", img_content)
                
                # 构造 CDN 访问链接
                cloud_url = f"https://raw.githubusercontent.com/{GH_REPO_NAME}/main/{filename}"
                
                print(f"✅ 上架成功！云端地址: {cloud_url}")
                return {"url": cloud_url}
        
        print(f"❌ 调用失败: {response.text}")
        return {"error": True, "message": "API 响应异常"}

    except Exception as e:
        print(f"❌ 系统错误: {str(e)}")
        return {"error": True, "message": str(e)}

# --- 新增：获取所有已上架货物列表的接口 ---
@app.get("/gallery")
async def get_gallery():
    try:
        # 从 GitHub 获取所有 png 文件
        contents = repo.get_contents("")
        images = []
        for content in contents:
            if content.name.endswith('.png'):
                images.append({
                    "url": f"https://raw.githubusercontent.com/{GH_REPO_NAME}/main/{content.name}",
                    "name": content.name
                })
        # 按时间倒序（最新的在前面）
        return images[::-1]
    except Exception as e:
        print(f"❌ 读取货架失败: {e}")
        return []

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
