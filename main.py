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
from google import genai
from google.genai import types
from PIL import Image

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"
# 👇 YAHAN APNI KEY DALEIN
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

# --- SMART CLIENT SETUP ---
client = None
model_id = "gemini-2.0-flash" # Trying the latest standard

def configure_client():
    global client, model_id
    try:
        client = genai.Client(api_key=API_KEY)
        log_msg("✅ Google GenAI Client Initialized")
        # We will let the code try models dynamically if needed, 
        # but defaulting to 2.0-flash is safer now.
    except Exception as e:
        log_msg(f"❌ Client Init Error: {e}")

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei Vision AI 2.0</title>
        <style>
            body { background: #050505; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 15px auto; max-width: 850px; background: #111; border-radius: 8px; }
            button { padding: 12px 25px; font-weight: bold; cursor: pointer; border:none; margin: 5px; border-radius: 5px; font-size: 16px; }
            .btn-blue { background: #2979ff; color: white; }
            .btn-red { background: #d50000; color: white; }
            .logs { 
                height: 400px; overflow-y: auto; text-align: left; 
                border: 1px solid #444; padding: 15px; color: #ddd; 
                background: black; font-size: 14px; white-space: pre-wrap;
            }
            .gallery img { height: 140px; border: 2px solid #555; margin: 5px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>👁️ GEMINI 2.0 VISION AGENT</h1>
        
        <div class="box">
            <button class="btn-blue" onclick="refreshData()">🔄 Refresh Logs</button>
            <button class="btn-red" onclick="startBot()">🚀 Launch Mission</button>
        </div>

        <div class="box logs" id="logs">System Ready. Waiting for launch...</div>
        <div class="box gallery" id="gallery"></div>

        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = ">>> INITIALIZING...\n" + document.getElementById('logs').innerHTML;
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
    configure_client() 
    log_msg(">>> COMMAND RECEIVED: Start Sequence")
    bt.add_task(run_agent)
    return {"status": "started"}

# --- VISION FUNCTIONS (Updated for New Library) ---
async def ask_gemini(image_path, prompt):
    if not client:
        log_msg("❌ Client not initialized!")
        return None
    try:
        # Load Image
        image = Image.open(image_path)
        
        full_prompt = f"""
        Look at this mobile screenshot. I need to tap the UI element: "{prompt}".
        
        Return valid JSON ONLY with 'x' and 'y' coordinates of the center.
        Example: {{"x": 150, "y": 400}}
        """

        # Generate using the new library syntax
        response = client.models.generate_content(
            model=model_id,
            contents=[full_prompt, image],
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        return response.text.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        log_msg(f"⚠️ API Error: {e}")
        return None

async def get_coordinates(image_path, element):
    res = await ask_gemini(image_path, element)
    try:
        data = json.loads(res)
        return data['x'], data['y']
    except:
        return None, None

async def verify_screen(image_path, verification_clue):
    prompt = f"Can you clearly see '{verification_clue}' in this image? Return JSON: {{'found': true}} or {{'found': false}}"
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
            await asyncio.sleep(8)

            # --- SMART ACTION FUNCTION ---
            async def smart_click_verify(target_desc, verification_clue, step_name):
                log_msg(f"🔵 Attempting: {step_name}")
                
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
                        await asyncio.sleep(5) # Thora extra time diya hai
                        
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
            
            # Step 1: Open Menu (Arrow targeting)
            if not await smart_click_verify(
                "The small arrow icon > on the right side of the Country/Region row", 
                "Search", 
                "01_open_menu"
            ): return

            # Step 2: Search Click (Important for mobile)
            log_msg("Focusing Search Bar...")
            await page.mouse.click(100, 150) # Approx top area click
            await asyncio.sleep(1)
            
            log_msg("Typing 'Pakistan'...")
            await page.keyboard.type("Pakistan", delay=100)
            await asyncio.sleep(3)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_typed.jpg")

            # Step 3: Select Pakistan
            if not await smart_click_verify(
                "The text 'Pakistan +92' in the list", 
                "+92", 
                "03_select_pak"
            ): return

            # Step 4: Phone Input
            log_msg("Typing Phone Number...")
            # Direct coordinates approach for input usually works better if AI fails verify
            x, y = await get_coordinates(f"{CAPTURE_DIR}/03_select_pak_verify_1.jpg", "Phone number input field")
            if x: await page.mouse.click(x, y)
            
            await page.keyboard.type(TARGET_PHONE, delay=100)
            await page.screenshot(path=f"{CAPTURE_DIR}/04_filled.jpg")

            # Step 5: Get Code
            await smart_click_verify("The 'Get code' button", "sent", "05_get_code")

            log_msg("✅ Workflow Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")