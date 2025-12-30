import os
import glob
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr

# --- IMPORTS CHECK ---
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
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ"

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
if not os.path.exists(CAPTURE_DIR):
    os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- GLOBAL LOGS (Terminal Data) ---
logs = []

def log_msg(message):
    """Adds a timestamped message to the logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry) # Server logs main bhi aye
    logs.insert(0, entry) # List main sab se upar aye
    # Keep only last 50 logs to save memory
    if len(logs) > 50:
        logs.pop()

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background-color: #121212; color: #e0e0e0; font-family: monospace; padding: 20px; }
            h1 { color: #ff4757; text-align: center; }
            
            /* Controls Container */
            .controls { text-align: center; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 20px; }
            button { padding: 15px 30px; font-size: 18px; cursor: pointer; margin: 10px; border-radius: 5px; border:none; font-weight: bold; }
            .btn-start { background: #ff4757; color: white; }
            .btn-refresh { background: #2ed573; color: black; }
            
            /* Terminal View */
            .terminal-box { 
                background-color: black; 
                border: 2px solid #333; 
                padding: 15px; 
                height: 300px; 
                overflow-y: auto; 
                font-family: 'Courier New', monospace;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.5);
            }
            .log-entry { margin-bottom: 5px; border-bottom: 1px solid #222; padding-bottom: 2px; }
            .log-entry:first-child { color: #00ff00; font-weight: bold; } /* Latest log green */

            /* Gallery View */
            .gallery { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
            .gallery img { 
                height: 150px; 
                border: 2px solid #555; 
                border-radius: 5px; 
                transition: transform 0.2s;
            }
            .gallery img:hover { transform: scale(1.5); border-color: #fff; z-index: 10; }
        </style>
    </head>
    <body>
        <h1>🤖 Huawei AI Command Center</h1>
        
        <div class="controls">
            <button class="btn-refresh" onclick="refreshData()">🔄 Refresh Status & Gallery</button>
            <button class="btn-start" onclick="startBot()">🚀 Launch AI</button>
        </div>

        <h3>📝 Live Terminal Logs</h3>
        <div class="terminal-box" id="terminal">
            <div class="log-entry">Waiting for system start...</div>
        </div>

        <h3>📸 Captured Frames</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() {
                // Pehle UI update karein
                const term = document.getElementById('terminal');
                term.innerHTML = '<div class="log-entry" style="color:yellow;">>>> Sending Launch Command...</div>' + term.innerHTML;
                
                fetch('/start', {method: 'POST'})
                .then(r => r.json())
                .then(d => {
                    if(d.msg === "Busy") alert("Bot is already running!");
                });
                
                // Auto refresh shuru kar dein
                setTimeout(refreshData, 2000);
            }

            function refreshData() {
                fetch('/status').then(r => r.json()).then(data => {
                    // Update Logs
                    const term = document.getElementById('terminal');
                    term.innerHTML = "";
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = 'log-entry';
                        div.innerText = log;
                        term.appendChild(div);
                    });

                    // Update Gallery
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
    # Get all images, sort by modification time (newest first)
    list_of_files = glob.glob(f'{CAPTURE_DIR}/*.jpg')
    list_of_files.sort(key=os.path.getmtime, reverse=True)
    
    # Image URLs banayein
    image_urls = [f"/captures/{os.path.basename(f)}" for f in list_of_files]
    
    return JSONResponse({
        "logs": logs,
        "images": image_urls
    })

@app.post("/start")
async def start_bot_endpoint(background_tasks: BackgroundTasks):
    global logs
    if any("Running" in s for s in logs[:1]): # Simple check if running
        return {"msg": "Busy"}
    
    log_msg(">>> COMMAND RECEIVED: Launch AI")
    background_tasks.add_task(run_ai_task)
    return {"msg": "Started"}

# --- AI LOGIC ---
async def run_ai_task():
    try:
        log_msg("Initializing Gemini 1.5 Flash Model...")
        
        api_key = os.environ["GOOGLE_API_KEY"]
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=SecretStr(api_key))
        
        # --- THE FIX: Inject Provider Safely ---
        # Subclassing nahi, direct injection taake 'ainvoke' na toote.
        try:
            # Pydantic models par kabhi kabhi setattr kaam nahi karta, is liye __dict__ use kar rahe hain
            object.__setattr__(llm, 'provider', 'google')
        except:
            # Fallback
            llm.provider = "google"
        
        log_msg("LLM Initialized. Provider set to 'google'.")

        # Setup Browser
        log_msg("Configuring Headless Browser...")
        agent = None
        if Browser and BrowserConfig:
            browser = Browser(config=BrowserConfig(headless=True, disable_security=True))
            agent = Agent(
                task=get_task_prompt(),
                llm=llm,
                browser=browser
            )
        else:
            log_msg("WARNING: Using default browser config (Imports issue).")
            agent = Agent(task=get_task_prompt(), llm=llm)

        log_msg("AI Agent Created. Starting Execution...")
        
        # --- EXECUTION WITH FEEDBACK ---
        # Browser-use logs print karta hai, hum unhein capture nahi kar sakte easily
        # lekin hum start/end track kar sakte hain.
        
        log_msg("AI is analyzing the page... (Step 1)")
        history = await agent.run()
        
        log_msg("✅ Mission Completed Successfully!")
        log_msg("Check the Gallery for results.")

    except Exception as e:
        log_msg(f"❌ CRITICAL ERROR: {str(e)}")
        print(f"CRASH: {e}")

def get_task_prompt():
    return f"""
    1. Navigate to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
    2. Wait for the page to load completely.
    3. Take a screenshot instantly.
    4. Click on the 'Country/Region' dropdown selector.
    5. Type 'Pakistan' in search and select 'Pakistan +92'.
    6. Take a screenshot.
    7. Enter phone number '{TARGET_PHONE}'.
    8. Click 'Get code'.
    9. Take a screenshot.
    10. Wait 10 seconds.
    """