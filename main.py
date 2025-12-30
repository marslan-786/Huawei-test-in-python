import os
import glob
import sys
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr

# --- GLOBAL LOGS CONFIG ---
logs = []

def log_msg(message):
    """Adds a timestamped message to the logs and prints to console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 100:
        logs.pop()

# --- SMART IMPORT LOGIC WITH LOGGING ---
Browser = None
BrowserConfig = None

log_msg("Attempting to load Browser modules...")

# Method 1: Standard (Latest)
try:
    from browser_use.browser.browser import Browser, BrowserConfig
    log_msg("✅ Loaded Browser from 'browser_use.browser.browser'")
except ImportError as e1:
    log_msg(f"Method 1 failed: {e1}")
    # Method 2: Fallback (Older versions)
    try:
        from browser_use.browser.service import Browser
        from browser_use.browser.config import BrowserConfig
        log_msg("✅ Loaded Browser from 'browser_use.browser.service'")
    except ImportError as e2:
        log_msg(f"Method 2 failed: {e2}")
        log_msg("⚠️ WARNING: Could not load 'Browser' class. Will use Default Agent.")

# --- API KEY ---
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
if not os.path.exists(CAPTURE_DIR):
    os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background-color: #0d0d0d; color: #00ff00; font-family: 'Courier New', monospace; padding: 20px; text-align: center; }
            h1 { color: #ff3b30; border-bottom: 2px solid #333; padding-bottom: 10px; }
            
            .controls { margin: 20px 0; padding: 20px; background: #1a1a1a; border-radius: 10px; }
            button { 
                padding: 15px 30px; font-size: 18px; cursor: pointer; margin: 10px; 
                border-radius: 5px; border:none; font-weight: bold; font-family: monospace;
            }
            .btn-start { background: #ff4757; color: white; }
            .btn-refresh { background: #2ed573; color: black; }
            
            .terminal { 
                background-color: black; border: 1px solid #333; padding: 15px; 
                height: 400px; overflow-y: auto; text-align: left; 
                font-size: 14px; line-height: 1.5; margin-bottom: 20px;
            }
            .log-entry { border-bottom: 1px solid #222; }
            .log-entry:first-child { color: #eebb00; font-weight: bold; } 

            .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
            .gallery img { width: 100%; border: 1px solid #444; }
        </style>
    </head>
    <body>
        <h1>🤖 Huawei AI Terminal</h1>
        
        <div class="controls">
            <button class="btn-refresh" onclick="refreshData()">🔄 Refresh Logs & View</button>
            <button class="btn-start" onclick="startBot()">🚀 Execute AI Mission</button>
        </div>

        <div class="terminal" id="terminal">
            <div class="log-entry">System Standby...</div>
        </div>

        <h3>Captured Intelligence</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() {
                const term = document.getElementById('terminal');
                term.innerHTML = '<div class="log-entry">>>> COMMAND SENT...</div>' + term.innerHTML;
                fetch('/start', {method: 'POST'});
                setTimeout(refreshData, 1500);
            }

            function refreshData() {
                fetch('/status').then(r => r.json()).then(data => {
                    const term = document.getElementById('terminal');
                    term.innerHTML = "";
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.innerText = log;
                        term.appendChild(div);
                    });

                    const gal = document.getElementById('gallery');
                    gal.innerHTML = "";
                    data.images.forEach(src => {
                        const img = document.createElement('img');
                        img.src = src;
                        gal.appendChild(img);
                    });
                });
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    list_of_files = glob.glob(f'{CAPTURE_DIR}/*.jpg')
    list_of_files.sort(key=os.path.getmtime, reverse=True)
    image_urls = [f"/captures/{os.path.basename(f)}" for f in list_of_files]
    return JSONResponse({"logs": logs, "images": image_urls})

@app.post("/start")
async def start_bot_endpoint(background_tasks: BackgroundTasks):
    global logs
    if any("Running" in s for s in logs[:1]):
        return {"msg": "Busy"}
    log_msg(">>> INITIALIZING AI SEQUENCE...")
    background_tasks.add_task(run_ai_task)
    return {"msg": "Started"}

# --- AI CORE ---
async def run_ai_task():
    try:
        log_msg("Step 1: Setting up LLM (Google Gemini)...")
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            log_msg("❌ ERROR: API Key missing!")
            return

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=SecretStr(api_key))
        
        # PROVIDER FIX (Injecting attribute to fool the library)
        try:
            object.__setattr__(llm, 'provider', 'google')
        except:
            llm.provider = "google"
        
        log_msg("Step 2: Configuring Browser...")
        agent = None
        
        # Browser Setup Logic
        if Browser and BrowserConfig:
            log_msg("Using CUSTOM Browser Config (Headless)...")
            browser = Browser(config=BrowserConfig(headless=True, disable_security=True))
            agent = Agent(task=get_task(), llm=llm, browser=browser)
        else:
            log_msg("⚠️ Using DEFAULT Browser Config (Imports Failed)...")
            # Default agent might try to open GUI, which fails on server.
            # But let's try it as last resort.
            agent = Agent(task=get_task(), llm=llm)

        log_msg("Step 3: Launching Agent...")
        
        # --- EXECUTION ---
        history = await agent.run()
        
        log_msg("✅ Sequence Finished Successfully.")

    except Exception as e:
        log_msg(f"❌ CRITICAL FAILURE: {str(e)}")
        print(f"Exception Trace: {e}")

def get_task():
    return f"""
    1. Go to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
    2. Wait for page load.
    3. Click 'Country/Region'.
    4. Search 'Pakistan' & select it.
    5. Type '{TARGET_PHONE}' in phone field.
    6. Click 'Get code'.
    7. Wait 10 seconds.
    """