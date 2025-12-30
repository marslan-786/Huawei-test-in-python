import os
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent

# --- VERIFIED IMPORT FOR VERSION 0.1.4 ---
from browser_use.browser.browser import Browser, BrowserConfig

# --- API KEY ---
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ"

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# Global Status
bot_status = "System Ready."

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background-color: #111; color: #fff; font-family: monospace; text-align: center; padding: 40px; }
            button { padding: 15px 30px; font-size: 18px; cursor: pointer; font-weight: bold; margin: 10px; }
            .btn-start { background: #ff4757; color: white; border: none; }
            .btn-refresh { background: #2ed573; color: black; border: none; }
            .status-box { border: 1px solid #444; padding: 20px; margin: 20px auto; max-width: 600px; }
        </style>
    </head>
    <body>
        <h1>🤖 Huawei AI Agent (v0.1.4)</h1>
        <div class="status-box">
            <h3>Status: <span id="status">Ready</span></h3>
            <button class="btn-refresh" onclick="location.reload()">🔄 Refresh Page</button>
            <br>
            <button class="btn-start" onclick="startBot()">🚀 Start AI</button>
        </div>
        <script>
            function startBot() {
                document.getElementById('status').innerText = "Request Sent...";
                fetch('/start', {method: 'POST'});
            }
            // Load status on open
            fetch('/status').then(r => r.json()).then(d => {
                document.getElementById('status').innerText = d.status;
            });
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    return {"status": bot_status}

@app.post("/start")
async def start_bot_endpoint(background_tasks: BackgroundTasks):
    global bot_status
    if "Running" in bot_status:
        return {"msg": "Busy"}
    
    bot_status = "Running..."
    background_tasks.add_task(run_ai_task)
    return {"msg": "Started"}

# --- AI LOGIC ---
async def run_ai_task():
    global bot_status
    try:
        bot_status = "AI Initializing..."
        
        # 1. Setup LLM
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        
        # 2. Setup Browser (Correct Config for Server)
        browser = Browser(
            config=BrowserConfig(
                headless=True,
                disable_security=True,
            )
        )

        # 3. Task
        task = f"""
        1. Go to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
        2. Wait for page load.
        3. Click on the Country/Region selector.
        4. Search for 'Pakistan' and select it.
        5. Enter the phone number '{TARGET_PHONE}'.
        6. Click 'Get code'.
        7. Wait 10 seconds.
        """

        agent = Agent(task=task, llm=llm, browser=browser)
        
        bot_status = "AI Navigating... (Please wait 1 min)"
        await agent.run()
        
        bot_status = "Mission Completed."

    except Exception as e:
        bot_status = f"Crash Error: {str(e)}"
        print(f"Error: {e}")