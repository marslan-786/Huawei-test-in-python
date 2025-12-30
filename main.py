import os
import glob
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"
# 👇 YAHAN KEY DALEIN
API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ")

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING ---
logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 100: logs.pop()

# --- SMART MODEL SELECTION (PRO FIRST) ---
active_model = None

def configure_model():
    global active_model
    try:
        genai.configure(api_key=API_KEY)
        log_msg("🔍 Scanning for PRO Vision Models...")
        
        # Get all models available to your API Key
        all_models = list(genai.list_models())
        
        # Priority: PRO > LATEST PRO > FLASH (Fallback)
        priority_names = [
            "gemini-1.5-pro",          # First Choice (Best)
            "gemini-1.5-pro-latest",   # Second Choice
            "gemini-1.5-pro-001",      # Older Pro
            "gemini-pro-vision",       # Legacy Pro
            "gemini-1.5-flash"         # Fallback only
        ]
        
        chosen_name = None
        
        # 1. Check Priority List
        for p in priority_names:
            for m in all_models:
                if p in m.name:
                    chosen_name = m.name
                    break
            if chosen_name: break
            
        # 2. Fallback: Any model that supports Vision
        if not chosen_name:
            for m in all_models:
                if 'vision' in m.supported_generation_methods:
                    chosen_name = m.name
                    break
        
        if chosen_name:
            log_msg(f"✅ Connected to POWER MODEL: {chosen_name}")
            active_model = genai.GenerativeModel(chosen_name)
        else:
            log_msg("❌ CRITICAL: No suitable Vision model found!")
            
    except Exception as e:
        log_msg(f"❌ API Connection Failed: {e}")

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <style>
            body { background: #111; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #444; padding: 10px; margin: 10px auto; max-width: 900px; background: #222; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin: 5px; border-radius: 4px; }
            .btn-blue { background: #2979ff; color: white; }
            .btn-red { background: #ff1744; color: white; }
            .logs { 
                height: 350px; overflow-y: auto; text-align: left; 
                border: 1px solid #555; padding: 10px; color: #ccc; 
                background: black; font-size: 13px; white-space: pre-wrap;
            }
            .gallery img { height: 120px; border: 1px solid #666; margin: 5px; }
        </style>
    </head>
    <body>
        <h1>💎 HUAWEI PRO AGENT (Gemini 1.5 Pro)</h1>
        
        <div class="box">
            <button class="btn-blue" onclick="refreshData()">🔄 Refresh Logs</button>
            <button class="btn-red" onclick="startBot()">🚀 Launch PRO Mission</button>
        </div>

        <div class="box logs" id="logs">System Standby...</div>
        <div class="box gallery" id="gallery"></div>

        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = ">>> INITIALIZING PRO ENGINE...\n" + document.getElementById('logs').innerHTML;
                setTimeout(refreshData, 3000);
            }

            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    const logContainer = document.getElementById('logs');
                    logContainer.innerText = d.logs.join('\\n');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    configure_model() 
    log_msg(">>> COMMAND RECEIVED: Start Sequence")
    bt.add_task(run_agent)
    return {"status": "started"}

# --- VISION FUNCTIONS ---
async def ask_gemini(image_path, prompt):
    if not active_model:
        log_msg("❌ Model not initialized!")
        return None
    try:
        img = Image.open(image_path)
        # Using Pro model needs slightly cleaner prompts
        response = active_model.generate_content([prompt, img])
        return response.text.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        log_msg(f"⚠️ API Error: {e}")
        return None

async def get_coordinates(image_path, element):
    prompt = f"""
    Analyze the UI screenshot accurately. Find the element: "{element}".
    Return valid JSON ONLY with 'x' and 'y' (center coordinates).
    Example: {{"x": 100, "y": 200}}
    """
    res = await ask_gemini(image_path, prompt)
    try:
        data = json.loads(res)
        return data['x'], data['y']
    except:
        return None, None

async def verify_screen(image_path, verification_clue):
    prompt = f"""
    Look at this screenshot. Do you see "{verification_clue}" clearly visible?
    Return valid JSON ONLY: {{"found": true}} or {{"found": false}}.
    """
    res = await ask_gemini(image_path, prompt)
    try:
        return json.loads(res).get("found", False)
    except:
        return False

# --- MAIN LOGIC ---
async def run_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={"width": 412, "height": 915},
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()

            log_msg("Navigating...")
            await page.goto("https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone")
            await asyncio.sleep(6)

            # --- SMART ACTION FUNCTION ---
            async def smart_click_verify(target_desc, verification_clue, step_name):
                log_msg(f"🔵 Attempting Step: {step_name}")
                
                for attempt in range(1, 4):
                    path = f"{CAPTURE_DIR}/{step_name}_try{attempt}.jpg"
                    await page.screenshot(path=path)
                    
                    x, y = await get_coordinates(path, target_desc)
                    
                    if x and y:
                        # Visual Debug
                        await page.evaluate(f"""
                            var d = document.createElement('div');
                            d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
                            d.style.width='20px';d.style.height='20px';d.style.background='red';
                            d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='2px solid yellow';
                            document.body.appendChild(d);
                        """)
                        await page.screenshot(path=f"{CAPTURE_DIR}/{step_name}_click_{attempt}.jpg")
                        
                        await page.mouse.click(x, y)
                        log_msg(f"   Click at {x},{y}")
                        await asyncio.sleep(4)
                        
                        # Verify
                        v_path = f"{CAPTURE_DIR}/{step_name}_verify_{attempt}.jpg"
                        await page.screenshot(path=v_path)
                        if await verify_screen(v_path, verification_clue):
                            log_msg(f"✅ Verified: Found '{verification_clue}'")
                            return True
                        else:
                            log_msg(f"⚠️ Verification failed. Retrying...")
                    else:
                        log_msg("⚠️ AI could not locate element.")
                
                log_msg(f"❌ Step Failed: {step_name}")
                return False

            # --- FLOW ---
            
            # Step 1: Open Menu (Using Arrow)
            if not await smart_click_verify(
                "The small arrow icon > on the right side of the Country/Region row", 
                "Search", 
                "01_open_menu"
            ): return

            log_msg("Typing 'Pakistan'...")
            # Focus search bar
            await page.mouse.click(100, 100) 
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_typed.jpg")

            # Step 2: Select Pakistan
            if not await smart_click_verify(
                "The text 'Pakistan +92' in the list", 
                "+92", 
                "03_select_pak"
            ): return

            log_msg("Typing Phone Number...")
            # Step 3: Focus Phone Input explicitly
            x, y = await get_coordinates(f"{CAPTURE_DIR}/03_select_pak_verify_1.jpg", "Phone number input field")
            if x: await page.mouse.click(x, y)
            
            await page.keyboard.type(TARGET_PHONE, delay=100)
            await page.screenshot(path=f"{CAPTURE_DIR}/04_filled.jpg")

            # Step 4: Get Code
            await smart_click_verify("The 'Get code' button", "sent", "05_get_code")

            log_msg("✅ Workflow Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")