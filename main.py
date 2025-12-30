import os
import sys
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent

# --- SMART IMPORT LOGIC (No Guessing) ---
Browser = None
BrowserConfig = None

# Attempt 1: Standard Path
try:
    from browser_use.browser.browser import Browser, BrowserConfig
    print("✅ Loaded Browser from standard path")
except ImportError:
    pass

# Attempt 2: Short Path
if Browser is None:
    try:
        from browser_use.browser import Browser, BrowserConfig
        print("✅ Loaded Browser from short path")
    except ImportError:
        pass

# Attempt 3: Service Path (Old versions)
if Browser is None:
    try:
        from browser_use.browser.service import Browser
        from browser_use.browser.config import BrowserConfig
        print("✅ Loaded Browser from service path")
    except ImportError:
        pass

# Final Check
if Browser is None:
    print("⚠️ WARNING: Could not find Browser class. Agent will run with DEFAULTS.")

# --- API KEY ---
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ"

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

bot_status = "System Ready. Waiting..."

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
        </style>
    </head>
    <body>
        <h1>🤖 AI Agent Dashboard</h1>
        <div class="box">
            <h3>Status: <span id="status">Idle</span></h3>
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
                document.getElementById('status').innerText = "Starting...";
                fetch('/start', {method: 'POST'});
            }
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
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        
        # Configure Browser if class was found
        agent = None
        if Browser and BrowserConfig:
            # We explicitly set headless=True for Railway
            browser = Browser(config=BrowserConfig(headless=True, disable_security=True))
            agent = Agent(
                task=get_task_prompt(),
                llm=llm,
                browser=browser
            )
            bot_status = "AI Running (Custom Browser Config)..."
        else:
            # Fallback to default (Might fail on server if it tries to open GUI)
            agent = Agent(
                task=get_task_prompt(),
                llm=llm
            )
            bot_status = "AI Running (Default Config)..."

        await agent.run()
        bot_status = "Mission Completed."

    except Exception as e:
        bot_status = f"Error: {str(e)}"
        print(f"CRASH: {e}")

def get_task_prompt():
    return f"""
    1. Go to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
    2. Wait for page load.
    3. Click 'Country/Region' -> Select 'Pakistan'.
    4. Enter number '{TARGET_PHONE}'.
    5. Click 'Get code'.
    6. Wait 10 seconds.
    """