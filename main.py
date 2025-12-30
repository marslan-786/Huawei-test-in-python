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
# 👇 APNI KEY YAHAN PASTE KAREIN
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
        # Force use 1.5 Flash (Best for speed/vision)
        active_model = genai.GenerativeModel("models/gemini-1.5-flash")
        log_msg("✅ Model Configured: gemini-1.5-flash")
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
        <h1>👁️ GEMINI VISION DIRECT (V2)</h1>
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
    configure_genai()
    if not active_model:
        return {"status": "error", "msg": "No model found"}
    log_msg(">>> Start Command Received")
    bt.add_task(run_vision_agent)
    return {"status": "started"}

# --- AI BRAIN ---
async def ask_gemini(image_path, element):
    try:
        log_msg(f"🧠 Asking AI to find: '{element}'")
        img = Image.open(image_path)
        
        # Strict Prompting
        prompt = f"""
        Look at this screenshot. I need to click the UI element described as: "{element}".
        
        Return valid JSON ONLY with 'x' and 'y' coordinates of the center.
        If you are unsure, guess the most likely position.
        Example: {{"x": 150, "y": 400}}
        Do not write markdown or explanations.
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
            # Extra wait for full load
            await asyncio.sleep(8) 
            
            # --- ACTION HELPER ---
            async def ai_action(desc, step_id, input_text=None, wait_after=3):
                path = f"{CAPTURE_DIR}/{step_id}_scan.jpg"
                await page.screenshot(path=path)
                
                x, y = await ask_gemini(path, desc)
                if x and y:
                    # Draw Target
                    await page.evaluate(f"""
                        var d = document.createElement('div');
                        d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
                        d.style.width='20px';d.style.height='20px';d.style.background='red';
                        d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='2px solid white';
                        document.body.appendChild(d);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/{step_id}_targeted.jpg")
                    
                    await page.mouse.click(x, y)
                    log_msg(f"Clicked at {x}, {y}")
                    
                    # Agar input hai to thora ruk k type karo
                    if input_text:
                        await asyncio.sleep(1)
                        # Ensure focus by clicking again if needed (optional)
                        log_msg(f"Typing: {input_text}")
                        await page.keyboard.type(input_text, delay=100)
                    
                    await asyncio.sleep(wait_after)
                    return True
                return False

            # --- STEP 1: OPEN DROPDOWN (Improved Target) ---
            # Hum arrow (>) ko target karenge taake menu paka khule
            await ai_action("The arrow icon > on the far right of the Country/Region row", "01_open_menu", wait_after=5)
            
            # --- STEP 2: CLICK SEARCH BAR (New Step) ---
            # Type karne se pehle search bar par click karna zaroori hai mobile view main
            await ai_action("The Search input field at the top of the list", "02_click_search", wait_after=1)
            
            # --- STEP 3: TYPE PAKISTAN ---
            log_msg("Typing 'Pakistan'...")
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(3)
            await page.screenshot(path=f"{CAPTURE_DIR}/03_searched.jpg")
            
            # --- STEP 4: SELECT PAKISTAN ---
            # Ab Gemini ko Pakistan list main nazar ana chahiye
            await ai_action("The text 'Pakistan +92' in the list", "04_select_pak", wait_after=5)
            
            # --- STEP 5: PHONE NUMBER ---
            # Input field ko clear karke likhein
            await ai_action("The Phone number input field", "05_click_phone")
            log_msg(f"Typing Number: {TARGET_PHONE}")
            await page.keyboard.type(TARGET_PHONE, delay=100)
            
            # --- STEP 6: GET CODE ---
            await ai_action("The small 'Get code' text button", "06_get_code")

            log_msg("Monitoring...")
            for i in range(5):
                await asyncio.sleep(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")

            log_msg("✅ Sequence Complete.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")
        print(e)