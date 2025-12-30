import os
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr

# --- SMART IMPORT LOGIC ---
Browser = None
BrowserConfig = None
try:
    from browser_use.browser.browser import Browser, BrowserConfig
except ImportError:
    try:
        from browser_use.browser.service import Browser
        from browser_use.browser.config import BrowserConfig
    except ImportError:
        pass

# --- API KEY ---
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

# --- 🛠️ THE REAL FIX (Subclassing) ---
# Hum Google ki class ko "Extend" kar rahe hain taake Pydantic error na de
class FixedGoogleLLM(ChatGoogleGenerativeAI):
    provider: str = "google"  # Ab ye field legally exist karti hai

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

bot_status = "System Ready. Waiting for Command."

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background-color: #121212; color: #fff; font-family: monospace; text-align: center; padding: 50px; }
            .box { border: 1px solid #333; padding: 20px; max-width: 600px; margin: auto; background: #1e1e1e; }
            button { padding: 15px 30px; font-size: 18px; cursor: pointer; margin: 10px; border-radius: 5px; border:none; }
            .start { background: #ff4757; color: white; }
            .refresh { background: #1e90ff; color: white; }
            .status-text { color: #00ff00; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🤖 Huawei AI Agent (Patched)</h1>
        <div class="box">
            <h3>Status: <span id="status" class="status-text">Idle</span></h3>
            <button class="refresh" onclick="checkStatus()">🔄 Refresh Status</button>
            <br>
            <button class="start" onclick="startBot()">🚀 Launch AI</button>
        </div>
        <script>
            function checkStatus() {
                fetch('/status').then(r => r.json()).then(d => {
                    document.getElementById('status').innerText = d.status;
                });
            }
            function startBot() {
                document.getElementById('status').innerText = "Request Sent...";
                fetch('/start', {method: 'POST'});
            }
            checkStatus();
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
        bot_status = "AI Initializing (Fixing LLM)..."
        
        # 1. Setup LLM using our FIXED Class
        # Hamari apni class use hogi jisme 'provider' field majood hai
        api_key = os.environ["GOOGLE_API_KEY"]
        llm = FixedGoogleLLM(
            model="gemini-1.5-flash", 
            google_api_key=SecretStr(api_key)
        )

        # 2. Setup Browser
        agent = None
        if Browser and BrowserConfig:
            # Headless mode for Server
            browser = Browser(config=BrowserConfig(headless=True, disable_security=True))
            agent = Agent(
                task=get_task_prompt(),
                llm=llm,
                browser=browser
            )
            bot_status = "AI Running (Custom Browser)..."
        else:
            # Fallback
            agent = Agent(task=get_task_prompt(), llm=llm)
            bot_status = "AI Running (Default Browser)..."

        # 3. Run
        await agent.run()
        bot_status = "Mission Completed. Check logs/video."

    except Exception as e:
        bot_status = f"Error: {str(e)}"
        print(f"CRASH: {e}")

def get_task_prompt():
    return f"""
    1. Navigate to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
    2. Wait for the page to load.
    3. Click on the Country/Region selector.
    4. Type 'Pakistan' in the search and select it.
    5. Enter phone number '{TARGET_PHONE}'.
    6. Click 'Get code'.
    7. Wait 10 seconds.
    """