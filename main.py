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
API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ") # Yahan Key Dalein

# Setup Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Flash is faster & cheaper, Pro is smarter

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
        <h1>👁️ GEMINI VISION AGENT</h1>
        <div class="box">
            <button class="btn-refresh" onclick="refresh()">🔄 REFRESH VIEW</button>
            <button class="btn-start" onclick="startBot()">🚀 START VISION AI</button>
        </div>
        <div class="box logs" id="logs">System Standby...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> AI INITIALIZED...</div>" + document.getElementById('logs').innerHTML;
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
    log_msg(">>> Start Command Received")
    bt.add_task(run_vision_agent)
    return {"status": "started"}

# --- AI HELPER FUNCTION ---
async def ask_gemini_for_coordinates(image_path, element_description):
    """Sends image to Gemini and asks for X,Y coordinates"""
    try:
        log_msg(f"🧠 Asking Gemini: Where is '{element_description}'?")
        
        # Load Image
        img = Image.open(image_path)
        
        # Prompt Engineering
        prompt = f"""
        Look at this mobile screenshot. I need to click on the UI element described as: "{element_description}".
        
        Return the X and Y coordinates of the CENTER of that element.
        The image size is {img.width}x{img.height}.
        
        IMPORTANT: Return ONLY valid JSON format like this: {{"x": 123, "y": 456}}.
        Do not write any other text.
        """
        
        response = model.generate_content([prompt, img])
        text = response.text.strip().replace("```json", "").replace("```", "")
        
        coords = json.loads(text)
        log_msg(f"🎯 Gemini found it at: {coords}")
        return coords['x'], coords['y']
    except Exception as e:
        log_msg(f"⚠️ Gemini Vision Error: {e}")
        return None, None

# --- MAIN AUTOMATION ---
async def run_vision_agent():
    try:
        # Cleanup
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # Launch with Mobile Viewport (Critical for WAP site)
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={"width": 412, "height": 915}, # Pixel Mobile Size
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()

            # 1. Load Page
            log_msg("Navigating to URL...")
            await page.goto("https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone")
            await asyncio.sleep(5)
            
            # Function to Process a Step using AI
            async def ai_click(desc, step_num):
                # Screenshot Capture
                path = f"{CAPTURE_DIR}/{step_num}_before_{desc.replace(' ','_')}.jpg"
                await page.screenshot(path=path)
                
                # Ask Gemini
                x, y = await ask_gemini_for_coordinates(path, desc)
                
                if x and y:
                    # Visual Indicator (Red Dot)
                    await page.evaluate(f"""
                        var dot = document.createElement('div');
                        dot.style.position = 'absolute';
                        dot.style.left = '{x-10}px';
                        dot.style.top = '{y-10}px';
                        dot.style.width = '20px';
                        dot.style.height = '20px';
                        dot.style.background = 'red';
                        dot.style.borderRadius = '50%';
                        dot.style.zIndex = '10000';
                        dot.style.border = '2px solid white';
                        document.body.appendChild(dot);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/{step_num}_targeting_{desc}.jpg")
                    
                    # Click
                    await page.mouse.click(x, y)
                    log_msg(f"Clicked on {x},{y}")
                    await asyncio.sleep(3) # Wait for UI update
                    return True
                return False

            # --- EXECUTION STEPS ---
            
            # 2. Click Country Dropdown
            await ai_click("The Country/Region selector dropdown (usually showing Hong Kong)", "01")
            
            # 3. Search Bar
            # Yahan hum try karte hain seedha type karne ki, agar fail hua to click karenge
            log_msg("Typing 'Pakistan'...")
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_typed.jpg")
            
            # 4. Select Pakistan
            await ai_click("The list item that says Pakistan +92", "03")
            
            # 5. Input Number
            # Sometimes explicit click helps focus
            await ai_click("The Phone Number input field", "04")
            log_msg(f"Typing Number: {TARGET_PHONE}")
            await page.keyboard.type(TARGET_PHONE, delay=100)
            await page.screenshot(path=f"{CAPTURE_DIR}/05_filled.jpg")
            
            # 6. Click Get Code
            await ai_click("The 'Get code' button", "06")

            # 7. Monitor Result
            log_msg("Monitoring for 15 seconds...")
            for i in range(5):
                await asyncio.sleep(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")

            log_msg("✅ AI Session Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")
        print(e)