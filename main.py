import os
import glob
import asyncio
import random
import time
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- IMPORT CAPTCHA SOLVER ---
from captcha_solver import solve_captcha

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"

# 👇 PROXY CONFIG (Webshare)
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

# --- HK NUMBER GENERATOR (Agar file khali ho to) ---
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
        <title>Huawei Captcha Solver</title>
        <style>
            body { background: #1a1a1a; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #000; margin-bottom: 20px; font-size: 13px; color: #ccc; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 100px; border: 1px solid #444; }
        </style>
    </head>
    <body>
        <h1>🧩 HUAWEI CAPTCHA SYSTEM</h1>
        <p>Target: Hong Kong (Default) | Solver: Active</p>
        <button onclick="startBot()">🚀 START SOLVER</button>
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
            setInterval(refreshData, 3000);
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

async def wait_and_log(seconds):
    log_msg(f"⏳ Waiting {seconds}s...")
    await asyncio.sleep(seconds)

# --- MAIN FLOW ---
async def run_hk_flow():
    session_id = int(time.time())
    current_number = generate_hk_number() # Using Random HK number for Captcha Test
    
    log_msg(f"🎬 Session {session_id} | HK Number: {current_number}")

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
            await wait_and_log(4)
            
            # Cookie
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0: await visual_tap(page, cookie_close, "Cookie")
            
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_01_loaded.jpg")

            # Register
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await wait_and_log(5)
            
            # --- SKIP COUNTRY CHANGE (Keep HK) ---
            log_msg("ℹ️ Keeping Default Country (Hong Kong) for Captcha Test")

            # Agree Terms
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0: await visual_tap(page, agree_text, "Terms")
            await wait_and_log(1)

            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree/Next")
                await wait_and_log(4)

            # DOB
            log_msg("📅 DOB Scroll...")
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            await wait_and_log(2)
            
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB Next")
            await wait_and_log(3)

            # Phone Option
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "Use Phone")
            await wait_and_log(2)

            # Input & Code
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.2)
                await page.touchscreen.tap(20, 100) # Blur
                await wait_and_log(1)
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting for Captcha/Result...")
                    
                    # --- CAPTCHA DETECTION & SOLVING ---
                    captcha_detected = False
                    for _ in range(10): # Check for 10 seconds
                        await asyncio.sleep(1)
                        if len(page.frames) > 1:
                            captcha_detected = True
                            break
                    
                    if captcha_detected:
                        log_msg("🧩 CAPTCHA POPUP DETECTED! Calling Solver...")
                        await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_captcha_detected.jpg")
                        
                        # CALL THE SOLVER
                        success = await solve_captcha(page)
                        
                        if success:
                            log_msg("✅ Solver Finished. Checking result...")
                            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_after_solve.jpg")
                        else:
                            log_msg("❌ Solver Failed.")
                    else:
                        log_msg("❓ No Captcha detected.")
                        await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_no_captcha.jpg")

            await browser.close()
        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await browser.close()