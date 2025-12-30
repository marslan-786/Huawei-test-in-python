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

# --- API KEY ---
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

app = FastAPI()
if not os.path.exists(CAPTURE_DIR):
    os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING ---
logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 50: logs.pop()

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei AI Agent</title>
        <style>
            body { background: #000; color: #0f0; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 10px; margin: 10px auto; max-width: 800px; background: #111; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; font-size:14px; }
            .gallery img { height: 100px; border: 1px solid #555; margin: 2px; }
        </style>
    </head>
    <body>
        <h1>🤖 FINAL FIXED AGENT</h1>
        <div class="box">
            <button onclick="startBot()" style="background:red;color:white;">🚀 START MISSION</button>
            <button onclick="refresh()" style="background:blue;color:white;">🔄 REFRESH LOGS</button>
        </div>
        <div class="box logs" id="logs">Waiting...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> Sending Command...</div>" + document.getElementById('logs').innerHTML;
            }
            function refresh() {
                fetch('/status').then(r => r.json()).then(d => {
                    let logHtml = "";
                    d.logs.forEach(l => logHtml += `<div>${l}</div>`);
                    document.getElementById('logs').innerHTML = logHtml;
                    
                    let galHtml = "";
                    d.images.forEach(i => galHtml += `<a href="${i}" target="_blank"><img src="${i}"></a>`);
                    document.getElementById('gallery').innerHTML = galHtml;
                });
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = glob.glob(f'{CAPTURE_DIR}/*.jpg')
    files.sort(key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    log_msg(">>> Start Command Received")
    bt.add_task(run_agent)
    return {"status": "started"}

# --- 🛠️ THE REAL FIX IS HERE ---
# Hum ek nayi class bana rahe hain jo Google ki class se sab kuch leti hai
# lekin 'provider' field ko Pydantic Schema main legally add karti hai.
class FixedGemini(ChatGoogleGenerativeAI):
    provider: str = "google" # This fixes the 'no attribute' error

# --- MAIN LOGIC ---
async def run_agent():
    try:
        log_msg("1. Setting up Gemini LLM (Patched Class)...")
        api_key = os.environ.get("GOOGLE_API_KEY")
        
        # Use our FIXED class instead of the standard one
        llm = FixedGemini(
            model="gemini-1.5-flash", 
            google_api_key=SecretStr(api_key),
            temperature=0
        )
        
        log_msg("2. Initializing Browser Agent...")
        
        task_text = f"""
        Go to 'https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone'
        Wait for network idle.
        Find and Click on 'Country/Region'.
        Type 'Pakistan' and select 'Pakistan +92'.
        Fill the phone input with '{TARGET_PHONE}'.
        Click the 'Get code' button.
        """

        # Agent ko sirf LLM aur Task dein, Browser wo khud sambhal lega
        agent = Agent(
            task=task_text,
            llm=llm,
        )

        log_msg("3. AI Agent Running (Watching screen)...")
        
        # Ab ye crash nahi karega
        history = await agent.run()
        
        log_msg("✅ Mission Finished.")

    except Exception as e:
        log_msg(f"❌ ERROR: {str(e)}")
        print(f"FULL ERROR: {e}")