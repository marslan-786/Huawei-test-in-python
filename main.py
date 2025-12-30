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
API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCz-X24ZgEZ79YRcg8ym9ZtuQHup1AVgJQ")

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING ---
logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")
    logs.insert(0, f"[{timestamp}] {message}")
    if len(logs) > 50: logs.pop()

# --- GEMINI SETUP ---
active_model = None
def configure_model():
    global active_model
    genai.configure(api_key=API_KEY)
    active_model = genai.GenerativeModel("models/gemini-1.5-flash")

# --- DASHBOARD (UI) ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background: #000; color: #0f0; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 10px; margin: 10px auto; max-width: 800px; background: #111; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; }
            .gallery img { height: 150px; border: 1px solid #555; margin: 5px; }
        </style>
    </head>
    <body>
        <h1>🧠 SELF-CORRECTING AI AGENT</h1>
        <div class="box">
            <button onclick="fetch('/start', {method:'POST'})" style="padding:10px;background:red;color:white;cursor:pointer;">🚀 START INTELLIGENT MODE</button>
        </div>
        <div class="box logs" id="logs">Waiting...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            fetch('/status').then(r=>r.json()).then(d=>{
                document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
            });
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
    log_msg(">>> COMMAND RECEIVED: Intelligent Mode")
    bt.add_task(run_agent)
    return {"status": "started"}

# --- INTELLIGENT VISION FUNCTIONS ---

async def ask_gemini(image_path, prompt):
    """Generic function to talk to Gemini"""
    try:
        img = Image.open(image_path)
        response = active_model.generate_content([prompt, img])
        return response.text.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        log_msg(f"⚠️ Gemini Error: {e}")
        return None

async def get_coordinates(image_path, element):
    """Finds X,Y for an element"""
    prompt = f"""
    Find the UI element: "{element}".
    Return valid JSON ONLY with 'x' and 'y' (center).
    Example: {{"x": 100, "y": 200}}
    """
    res = await ask_gemini(image_path, prompt)
    try:
        data = json.loads(res)
        return data['x'], data['y']
    except:
        return None, None

async def verify_screen(image_path, verification_clue):
    """Checks if a specific element is visible on screen"""
    prompt = f"""
    Look at this image. Do you see "{verification_clue}"?
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
        # Cleanup
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
                log_msg(f"🔵 STEP: Clicking '{target_desc}'...")
                
                # Try up to 3 times
                for attempt in range(1, 4):
                    # 1. Capture
                    path = f"{CAPTURE_DIR}/{step_name}_try{attempt}.jpg"
                    await page.screenshot(path=path)
                    
                    # 2. Locate
                    x, y = await get_coordinates(path, target_desc)
                    
                    if x and y:
                        # Draw Red Dot
                        await page.evaluate(f"""
                            var d = document.createElement('div');
                            d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
                            d.style.width='20px';d.style.height='20px';d.style.background='red';
                            d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='3px solid yellow';
                            document.body.appendChild(d);
                        """)
                        await page.screenshot(path=f"{CAPTURE_DIR}/{step_name}_aim_{attempt}.jpg")
                        
                        # 3. Click
                        await page.mouse.click(x, y)
                        log_msg(f"   Clicking at {x},{y} (Attempt {attempt})")
                        await asyncio.sleep(4) # Wait for UI to change
                        
                        # 4. Verify
                        verify_path = f"{CAPTURE_DIR}/{step_name}_result_{attempt}.jpg"
                        await page.screenshot(path=verify_path)
                        
                        success = await verify_screen(verify_path, verification_clue)
                        if success:
                            log_msg(f"✅ Success! Found '{verification_clue}'.")
                            return True
                        else:
                            log_msg(f"⚠️ Verification Failed. Did not see '{verification_clue}'. Retrying...")
                    else:
                        log_msg("⚠️ Gemini couldn't find the element.")
                
                log_msg(f"❌ Failed to complete step: {step_name}")
                return False

            # --- EXECUTION ---

            # Step 1: Open Country Menu
            # Target: Arrow | Verify: "Search" input or list
            if not await smart_click_verify(
                "The small arrow icon > on the right side of the Country/Region row", 
                "Search", 
                "01_open_menu"
            ): return

            # Step 2: Search Pakistan
            # Target: Search box | Verify: Keyboard or typed text
            log_msg("Typing 'Pakistan'...")
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_typed.jpg")

            # Step 3: Select Pakistan
            # Target: Pakistan +92 | Verify: Main page with +92 code
            if not await smart_click_verify(
                "The text 'Pakistan +92' in the list", 
                "+92", 
                "03_select_pak"
            ): return

            # Step 4: Phone Number
            log_msg("Typing Number...")
            # Click Input first just in case
            x, y = await get_coordinates(f"{CAPTURE_DIR}/03_select_pak_result_1.jpg", "Phone number input field")
            if x: await page.mouse.click(x, y)
            
            await page.keyboard.type(TARGET_PHONE, delay=100)
            await page.screenshot(path=f"{CAPTURE_DIR}/04_filled.jpg")

            # Step 5: Get Code
            # Target: Get code | Verify: Loading or OTP sent message
            await smart_click_verify("The 'Get code' button", "sent", "05_get_code")

            log_msg("✅ Workflow Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")