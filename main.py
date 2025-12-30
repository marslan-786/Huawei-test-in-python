import os
import glob
import asyncio
import json
import base64
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
# 👇 Apni Key Yahan Paste Karein
API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ")

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

# --- SMART MODEL SETUP ---
active_model = None

def configure_genai():
    global active_model
    try:
        genai.configure(api_key=API_KEY)
        log_msg("🔍 Checking available Gemini models...")
        
        # List all models
        available_models = [m.name for m in genai.list_models()]
        
        # Priority list (Fastest to Slowest)
        priority = [
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-pro-vision"
        ]
        
        chosen_model = None
        for p in priority:
            if p in available_models:
                chosen_model = p
                break
        
        if not chosen_model:
            # Fallback if exact match not found, take first vision model
            for m in available_models:
                if "vision" in m or "flash" in m:
                    chosen_model = m
                    break
        
        if chosen_model:
            log_msg(f"✅ Connected to Model: {chosen_model}")
            active_model = genai.GenerativeModel(chosen_model)
        else:
            log_msg("❌ ERROR: No suitable Vision model found in your account!")
            
    except Exception as e:
        log_msg(f"❌ API Error: {e}")

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei Vision AI</title>
        <style>
            body { background: #000; color: #00ff00; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 10px; margin: 10px auto; max-width: 900px; background: #111; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border-radius: 5px; border:none; margin:5px;}
            .btn-start { background: #ff4757; color: white; }
            .btn-refresh { background: #2f3542; color: white; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; }
            .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
            .gallery img { width: 100%; border: 2px solid #555; }
        </style>
    </head>
    <body>
        <h1>👁️ GEMINI VISION DIRECT (Auto-Fix)</h1>
        <div class="box">
            <button class="btn-refresh" onclick="refresh()">🔄 REFRESH VIEW</button>
            <button class="btn-start" onclick="startBot()">🚀 START VISION AI</button>
        </div>
        <div class="box logs" id="logs">System Standby...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> START COMMAND SENT...</div>" + document.getElementById('logs').innerHTML;
                setTimeout(refresh, 2000);
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
    # Re-configure on every run to ensure connection
    configure_genai()
    if not active_model:
        return {"status": "error", "msg": "No model found"}
        
    log_msg(">>> Start Command Received")
    bt.add_task(run_vision_agent)
    return {"status": "started"}

# --- AI BRAIN ---
async def ask_gemini(image_path, element):
    """Sends screenshot to Gemini and asks for coordinates"""
    try:
        log_msg(f"🧠 Asking AI to find: '{element}'")
        img = Image.open(image_path)
        
        prompt = f"""
        Look at this screenshot. I need to click the UI element: "{element}".
        Return JSON ONLY with 'x' and 'y' coordinates of the center.
        Example: {{"x": 150, "y": 400}}
        """
        
        response = active_model.generate_content([prompt, img])
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(text)
        log_msg(f"🎯 Coordinates found: {data}")
        return data['x'], data['y']
    except Exception as e:
        log_msg(f"⚠️ Vision Error: {e}")
        return None, None

# --- MAIN AUTOMATION ---
async def run_vision_agent():
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

            log_msg("Navigating to Huawei...")
            await page.goto("https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone")
            await asyncio.sleep(5)
            
            # --- ACTION HELPER ---
            async def ai_action(desc, step_id):
                path = f"{CAPTURE_DIR}/{step_id}_scan.jpg"
                await page.screenshot(path=path)
                
                x, y = await ask_gemini(path, desc)
                if x and y:
                    # Draw Target
                    await page.evaluate(f"""
                        var d = document.createElement('div');
                        d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
                        d.style.width='20px';d.style.height='20px';d.style.background='rgba(255,0,0,0.5)';
                        d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='2px solid white';
                        document.body.appendChild(d);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/{step_id}_targeted.jpg")
                    
                    await page.mouse.click(x, y)
                    log_msg(f"Clicked at {x}, {y}")
                    await asyncio.sleep(3)
                    return True
                return False

            # --- STEPS ---
            await ai_action("The Country/Region dropdown (usually Hong Kong)", "01_country")
            
            log_msg("Typing 'Pakistan'...")
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_typed.jpg")
            
            await ai_action("The list item 'Pakistan +92'", "03_select_pak")
            
            await ai_action("Phone number input field", "04_phone_input")
            log_msg(f"Typing Number: {TARGET_PHONE}")
            await page.keyboard.type(TARGET_PHONE, delay=100)
            
            await ai_action("The 'Get code' button", "05_get_code")

            log_msg("Monitoring...")
            for i in range(5):
                await asyncio.sleep(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")

            log_msg("✅ Sequence Complete.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")
        print(e)