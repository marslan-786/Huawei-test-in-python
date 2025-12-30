import os
import glob
import asyncio
import random
import time
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# IMPORT SOLVER
from captcha_solver import solve_captcha

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
    "password": "582ygxexguhx"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 200: logs.pop()

def get_next_number():
    if not os.path.exists(NUMBERS_FILE): return None
    with open(NUMBERS_FILE, "r") as f: lines = f.readlines()
    numbers = [line.strip() for line in lines if line.strip()]
    if not numbers: return None
    current_number = numbers[0]
    new_lines = numbers[1:] + [current_number]
    with open(NUMBERS_FILE, "w") as f: f.write("\n".join(new_lines))
    return current_number

def generate_hk_number():
    prefix = random.choice(['5', '6', '9'])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{rest}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Grid Solver</title>
        <style>
            body { background: #111; color: #ffeb3b; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d50000; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #000; margin-bottom: 20px; font-size: 13px; color: #ddd; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 100px; border: 1px solid #444; }
        </style>
    </head>
    <body>
        <h1>🧩 HUAWEI GRID SWAPPER</h1>
        <p>Analyzing Grid 4x2 | Swapping Tile 0 <-> 4</p>
        <button onclick="startBot()">🚀 START SOLVER BOT</button>
        <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH</button>
        <div class="logs" id="logs">Waiting...</div>
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>
        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }
            function logUpdate(msg) { document.getElementById('logs').innerHTML = "<div>" + msg + "</div>" + document.getElementById('logs').innerHTML; }
            setInterval(refreshData, 2000);
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
    bt.add_task(run_hk_flow)
    return {"status": "started"}

async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '20px'; height = '20px'; background = 'red';
                dot.style.borderRadius = '50%'; zIndex = '999999'; document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

async def wait_and_capture(page, seconds, session_id, step_name):
    log_msg(f"⏳ Waiting {seconds}s ({step_name})...")
    for i in range(seconds):
        await asyncio.sleep(1)
        filename = f"{session_id}_{step_name}_{i:02d}.jpg"
        await page.screenshot(path=f"{CAPTURE_DIR}/{filename}")
    log_msg("✅ Wait Complete.")

# --- MAIN FLOW ---
async def run_hk_flow():
    for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
    session_id = int(time.time())
    current_number = get_next_number()
    if not current_number: current_number = generate_hk_number()
    
    log_msg(f"🎬 Session {session_id} | Number: {current_number}")

    async with async_playwright() as p:
        pixel_5 = p.devices['Pixel 5'].copy()
        pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
        pixel_5['viewport'] = {'width': 412, 'height': 950} 

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            proxy=PROXY_CONFIG
        )

        context = await browser.new_context(**pixel_5, locale="en-US")
        page = await context.new_page()

        try:
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=90000)
            await wait_and_capture(page, 4, session_id, "01_loading")
            
            # Cookie
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0: await visual_tap(page, cookie_close, "Cookie")
            
            # Register
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await wait_and_capture(page, 5, session_id, "02_registering")
            
            # Terms
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0: await visual_tap(page, agree_text, "Terms")
            await asyncio.sleep(1)

            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree/Next")
                await wait_and_capture(page, 4, session_id, "03_terms_done")

            # DOB
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            await asyncio.sleep(2)
            
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB Next")
            await wait_and_capture(page, 3, session_id, "04_dob_done")

            # Phone
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "Use Phone")
            await asyncio.sleep(2)

            # Input
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.2)
                
                await page.touchscreen.tap(350, 100) # Close Keyboard
                await asyncio.sleep(1)
                
                # GET CODE (Aggressive)
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE (1)")
                    await asyncio.sleep(2)
                    
                    if len(page.frames) == 1:
                        log_msg("⚠️ Retrying Force Click...")
                        await visual_tap(page, get_code, "GET CODE (2)")
                    
                    log_msg("⏳ Waiting 10s for Captcha Load...")
                    await wait_and_capture(page, 10, session_id, "05_captcha_loading")
                    
                    # --- CALL SOLVER IF LOADED ---
                    if len(page.frames) > 1:
                        log_msg("🧩 CAPTCHA DETECTED! Running Grid Solver...")
                        
                        # Call the imported function
                        await solve_captcha(page, session_id)
                        
                        # Capture result after swap
                        await wait_and_capture(page, 5, session_id, "07_post_swap")
                    else:
                        log_msg("❓ Still no Captcha. Screenshot saved.")
            
            await browser.close()
        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await browser.close()