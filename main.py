import os
import glob
import asyncio
import random
import math
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

# 🇵🇰 OUR CLEAN DESKTOP URL
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=pk&countryCode=pk&lang=en-us"

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
            body { background: #111; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 10px auto; max-width: 800px; background: #222; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #e91e63; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ccc; font-size: 13px; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🖱️ ULTRA HUMAN CLICKER</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START HUMAN SEQUENCE</button>
            <button onclick="refreshData()" style="background: #2196f3;">🔄 REFRESH</button>
        </div>
        <div class="box logs" id="logs">Ready...</div>
        <div class="box gallery" id="gallery"></div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> STARTING ENGINE...</div>" + document.getElementById('logs').innerHTML;
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
    log_msg(">>> COMMAND: Start Human Clicker Mode")
    bt.add_task(run_human_agent)
    return {"status": "started"}

# --- HUMAN MOUSE MOVEMENT (BEZIER CURVE) ---
# Ye function mouse ko seedha nahi balki insan ki tarah ghumata hai
async def human_move_to(page, x, y):
    # Current position (Assume start 0,0 or last pos)
    # Playwright doesn't give current pos easily, so we simulate steps
    steps = 25 # jitne zyada steps, utna smooth aur slow movement
    await page.mouse.move(x, y, steps=steps)

async def human_click_element(page, element, desc):
    box = await element.bounding_box()
    if box:
        # Random point inside the button (Not dead center)
        target_x = box['x'] + (box['width'] / 2) + random.uniform(-10, 10)
        target_y = box['y'] + (box['height'] / 2) + random.uniform(-5, 5)
        
        log_msg(f"🖱️ Moving to {desc}...")
        await human_move_to(page, target_x, target_y)
        
        # Pause before clicking (Thinking time)
        await asyncio.sleep(random.uniform(0.3, 0.6))
        
        log_msg(f"🖱️ Clicking {desc}...")
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.15)) # Click duration
        await page.mouse.up()
        return True
    return False

# --- MAIN LOGIC ---
async def run_human_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # 1. LAUNCH BROWSER (Stealth Config)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled", # Hide Automation
                    "--start-maximized"
                ]
            )
            
            # Desktop Context
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # 2. INJECT STEALTH SCRIPTS (Anti-Detection)
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            log_msg("🚀 Navigating to Clean Desktop Link...")
            await page.goto(MAGIC_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

            # --- STEP 1: PHONE INPUT ---
            log_msg("🔍 Finding Phone Input...")
            
            # Desktop Input Locators
            phone_input = page.locator("input.huawei-input").first
            if await phone_input.count() == 0:
                phone_input = page.locator("input[type='text']").first
            
            if await phone_input.count() > 0:
                # Human Click to Focus
                await human_click_element(page, phone_input.first, "Phone Input")
                
                # Human Typing
                log_msg(f"⌨️ Typing {TARGET_PHONE}...")
                await page.keyboard.type(TARGET_PHONE, delay=random.randint(80, 150))
                await asyncio.sleep(1)
                
                # Blur (Click outside)
                log_msg("🖱️ Clicking outside (Blur)...")
                await page.mouse.move(500, 500, steps=10)
                await page.mouse.click(500, 500)
                await asyncio.sleep(1)
                
                await page.screenshot(path=f"{CAPTURE_DIR}/02_filled.jpg")
            else:
                log_msg("❌ Input not found!")
                return

            # --- STEP 2: GET CODE (THE BIG CLICK) ---
            log_msg("🔍 Finding 'Get Code' Button...")
            
            # Huawei Desktop Button Locators
            get_code_btn = page.locator(".get-code-btn").first
            if await get_code_btn.count() == 0:
                 get_code_btn = page.get_by_text("Get code").first
            
            if await get_code_btn.count() > 0:
                # Highlight Target
                box = await get_code_btn.bounding_box()
                if box:
                    await page.evaluate(f"""
                        var d = document.createElement('div');
                        d.style.position='absolute';d.style.left='{box['x']}px';d.style.top='{box['y']}px';
                        d.style.width='{box['width']}px';d.style.height='{box['height']}px';
                        d.style.border='3px solid red'; d.style.zIndex='9999'; d.style.pointerEvents='none';
                        document.body.appendChild(d);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/03_target_locked.jpg")
                
                # EXECUTE HUMAN CLICK
                await human_click_element(page, get_code_btn, "Get Code Button")
                log_msg("✅ Click Action Completed.")
            else:
                log_msg("❌ Button not found!")

            # --- MONITORING (60s) ---
            log_msg("👀 Monitoring Result (60s)...")
            for i in range(1, 16):
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")
                
                # Check for popups/captchas
                if len(page.frames) > 1:
                    log_msg(f"⚠️ CAPTCHA/IFRAME DETECTED (Frame {i})")
            
            log_msg("✅ Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")