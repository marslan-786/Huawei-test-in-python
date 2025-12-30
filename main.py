import os
import glob
import asyncio
import random
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

# Desktop URL
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?service=https%3A%2F%2Foauth-login.cloud.huawei.com%2Foauth2%2Fv2%2Fauthorize%3Faccess_type%3Doffline&loginChannel=61000000&reqClientType=61&lang=en-us"

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
        <title>Huawei Human Bot</title>
        <style>
            body { background: #1a1a1a; color: #fff; font-family: sans-serif; padding: 20px; text-align: center; }
            .box { border: 1px solid #444; padding: 15px; margin: 10px auto; max-width: 800px; background: #222; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #00bcd4; color: black; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; font-size: 14px; background: black; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🖱️ HUAWEI HUMAN CLICKER (Manual Stealth)</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START HUMAN MODE</button>
            <button onclick="refreshData()" style="background: #4caf50; color: white;">🔄 REFRESH</button>
        </div>
        <div class="box logs" id="logs">Waiting...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> STARTING...</div>" + document.getElementById('logs').innerHTML;
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
    log_msg(">>> COMMAND: Human Mode (Desktop)")
    bt.add_task(run_human_agent)
    return {"status": "started"}

# --- MANUAL STEALTH (No Library Needed) ---
async def apply_stealth(page):
    # Ye script browser ko batata hai k "Main Robot nahi hun"
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        window.navigator.chrome = {
            runtime: {},
            // etc.
        };
    """)

# --- HUMAN MOVEMENT HELPER ---
async def human_click(page, element):
    """Moves mouse naturally to element and clicks with realistic timing"""
    # 1. Get Element Position
    box = await element.bounding_box()
    if not box: return False
    
    start_x = box['x'] + (box['width'] / 2)
    start_y = box['y'] + (box['height'] / 2)
    
    # Randomize exact click point
    target_x = start_x + random.uniform(-10, 10)
    target_y = start_y + random.uniform(-5, 5)
    
    # 2. Move Mouse (Hover)
    log_msg(f"🖱️ Moving mouse to {int(target_x)}, {int(target_y)}...")
    await page.mouse.move(target_x, target_y, steps=25) # Slower movement (25 steps)
    await asyncio.sleep(random.uniform(0.3, 0.7)) # Pause before clicking
    
    # 3. Press Down
    log_msg("🖱️ Mouse Down...")
    await page.mouse.down()
    
    # 4. Wait (Human press duration)
    await asyncio.sleep(random.uniform(0.1, 0.2))
    
    # 5. Release
    log_msg("🖱️ Mouse Up (Click Complete)")
    await page.mouse.up()
    
    return True

# --- MAIN LOGIC ---
async def run_human_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # DESKTOP SETUP
            # We hide automation flags manually via arguments
            args = [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
            
            browser = await p.chromium.launch(headless=True, args=args)
            
            # Standard Desktop Viewport
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Apply our Manual Stealth Script
            await apply_stealth(page)

            log_msg("🚀 Loading Desktop Page...")
            await page.goto(MAGIC_URL)
            await asyncio.sleep(5)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

            # --- STEP 1: FILL PHONE (DESKTOP) ---
            log_msg("🔍 Finding Phone Input...")
            
            # Desktop strategy: Try finding generic input first
            phone_input = page.locator("input[type='text']").first
            
            if await phone_input.count() == 0:
                 # Fallback
                 phone_input = page.locator(".huawei-input").first

            if await phone_input.count() > 0:
                # Click to focus
                await human_click(page, phone_input)
                
                # Human Typing
                log_msg(f"⌨️ Typing {TARGET_PHONE}...")
                await page.keyboard.type(TARGET_PHONE, delay=random.randint(60, 140))
                
                await asyncio.sleep(1)
                await page.screenshot(path=f"{CAPTURE_DIR}/02_filled.jpg")
                
                # Blur out by clicking empty space
                await page.mouse.click(10, 10)
            else:
                log_msg("❌ Phone input not found!")
                await page.screenshot(path=f"{CAPTURE_DIR}/debug_no_input.jpg")
                return

            # --- STEP 2: GET CODE (HUMAN CLICK) ---
            log_msg("🔍 Looking for 'Get code'...")
            
            # Text based locator is best
            get_code_btn = page.get_by_text("Get code")
            
            if await get_code_btn.count() == 0:
                 # Try capitalized
                 get_code_btn = page.get_by_text("GET CODE")
            
            if await get_code_btn.count() > 0:
                # Scroll carefully
                await get_code_btn.first.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                
                # Highlight
                box = await get_code_btn.first.bounding_box()
                if box:
                    await page.evaluate(f"""
                        var d = document.createElement('div');
                        d.style.position='absolute';d.style.left='{box['x']}px';d.style.top='{box['y']}px';
                        d.style.width='{box['width']}px';d.style.height='{box['height']}px';
                        d.style.border='3px solid red'; d.style.zIndex='9999'; d.style.pointerEvents='none';
                        document.body.appendChild(d);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/03_target_found.jpg")
                
                log_msg("🖱️ Performing Human Click...")
                await human_click(page, get_code_btn.first)
                log_msg("✅ Click Executed.")
            else:
                log_msg("❌ 'Get Code' button not found!")
                await page.screenshot(path=f"{CAPTURE_DIR}/debug_no_button.jpg")

            # --- MONITORING ---
            log_msg("👀 Watching (60s)...")
            for i in range(1, 16):
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")
                
            log_msg("✅ Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")