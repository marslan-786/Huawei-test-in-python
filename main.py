import os
import glob
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

# آپ کا دیا ہوا لنک (جس میں پاکستان پہلے سے سلیکٹڈ ہے)
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=61&loginChannel=61000000&regionCode=pk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei&clientID=101476933&service=https%3A%2F%2Foauth-login.cloud.huawei.com%2Foauth2%2Fv2%2Fauthorize%3Faccess_type%3Doffline&from=login/wapRegister/regByPhone#/wapRegister/regByPhone"

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

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Precision Bot</title>
        <style>
            body { background: #000; color: #00ff00; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 10px auto; max-width: 800px; background: #111; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #e74c3c; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; font-size: 14px; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🎯 HUAWEI PRECISION BOT</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START ACCURATE MODE</button>
            <button onclick="refreshData()" style="background: #3498db;">🔄 REFRESH</button>
        </div>
        <div class="box logs" id="logs">Waiting for command...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> STARTING SEQUENCE...</div>" + document.getElementById('logs').innerHTML;
                setTimeout(refreshData, 2000);
            }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
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
    log_msg(">>> COMMAND: Start Precision Mode (No AI)")
    bt.add_task(run_precision_agent)
    return {"status": "started"}

# --- HELPER: SHOW RED DOT ---
async def show_red_dot(page, selector=None, x=None, y=None):
    """Draws a red dot on the clicked element or coordinates"""
    if selector:
        # Get element center
        box = await selector.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
    
    if x and y:
        await page.evaluate(f"""
            var d = document.createElement('div');
            d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
            d.style.width='20px';d.style.height='20px';d.style.background='red';
            d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='2px solid white';
            document.body.appendChild(d);
        """)

# --- MAIN LOGIC ---
async def run_precision_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # Mobile Emulation Setup
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={"width": 412, "height": 915},
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()

            log_msg("🚀 Loading Page...")
            await page.goto(MAGIC_URL)
            
            # Wait for specific text "Phone number" to ensure load
            try:
                await page.wait_for_selector("text=Phone number", timeout=15000)
                log_msg("✅ Page Loaded. Text 'Phone number' found.")
            except:
                log_msg("⚠️ Warning: Text load timeout, proceeding anyway...")
            
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

            # --- STEP 1: FIND PHONE INPUT ---
            log_msg("🔍 Finding 'Phone number' field...")
            
            # Strategy: Find label "Phone number" or placeholder
            # Playwright ka smart locator jo input dhoondta hai
            phone_input = page.locator("input[type='tel']") 
            
            # Agar input mil jaye to Red Dot lagao aur click karo
            if await phone_input.count() > 0:
                await show_red_dot(page, selector=phone_input.first)
                await page.screenshot(path=f"{CAPTURE_DIR}/02_target_phone.jpg")
                
                await phone_input.first.click()
                log_msg("✅ Clicked Input Field")
                await asyncio.sleep(1)
                
                log_msg(f"⌨️ Typing: {TARGET_PHONE}")
                await page.keyboard.type(TARGET_PHONE, delay=100)
                await asyncio.sleep(1)
                await page.screenshot(path=f"{CAPTURE_DIR}/03_filled.jpg")
            else:
                log_msg("❌ ERROR: Could not find Phone Input field!")
                return

            # --- STEP 2: FIND GET CODE BUTTON ---
            log_msg("🔍 Finding 'Get code' button...")
            
            # Text based locator - 100% Accurate
            get_code_btn = page.get_by_text("Get code")
            
            if await get_code_btn.count() > 0:
                await show_red_dot(page, selector=get_code_btn.first)
                await page.screenshot(path=f"{CAPTURE_DIR}/04_target_button.jpg")
                
                await get_code_btn.first.click()
                log_msg("✅ Clicked 'Get code'")
            else:
                log_msg("❌ ERROR: 'Get code' text not found!")

            # --- MONITORING ---
            log_msg("👀 Monitoring Response...")
            for i in range(5):
                await asyncio.sleep(2)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")

            log_msg("✅ Mission Accomplished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")