import os
import glob
import asyncio
import random
import time
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- IMPORT SOLVER ---
try:
    from captcha_solver import solve_captcha
except ImportError:
    print("❌ ERROR: captcha_solver.py not found!")
    async def solve_captcha(page, session_id, logger=print): return False

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "klxgqgei-rotate", 
    "password": "upjk9roh3rhi"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- GLOBAL STATE ---
BOT_RUNNING = False
logs = []

def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 500: logs.pop()

def get_next_number():
    if os.path.exists(NUMBERS_FILE):
        with open(NUMBERS_FILE, "r") as f:
            lines = f.read().splitlines()
        for num in lines:
            if num.strip(): return num.strip()
    prefix = "9"
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{rest}"

# --- DASHBOARD (UI Unchanged) ---
@app.get("/")
async def read_index(): return FileResponse('index.html')
@app.get("/status")
async def get_status():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls, "running": BOT_RUNNING})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    global BOT_RUNNING
    if not BOT_RUNNING:
        BOT_RUNNING = True
        bt.add_task(master_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    global BOT_RUNNING
    BOT_RUNNING = False
    log_msg("🛑 STOP COMMAND RECEIVED.")
    return {"status": "stopping"}

@app.post("/clear_logs")
async def clear_logs_endpoint():
    global logs
    logs = []
    return {"status": "cleared"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    if not files: return {"status": "error", "error": "No images"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=10, format='FFMPEG', quality=8) as writer:
            for filename in files:
                try: writer.append_data(imageio.imread(filename))
                except: continue
        return {"status": "done"}
    except Exception as e: return {"status": "error", "error": str(e)}

# --- HELPER FUNCTIONS ---
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
                dot.style.width = '15px'; dot.style.height = '15px'; dot.style.background = 'rgba(255,0,0,0.6)';
                dot.style.borderRadius = '50%'; dot.style.zIndex = '999999'; dot.style.pointerEvents='none';
                document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Wait {step_name} ({seconds}s)...")
    frames = int(seconds / 0.2)
    for i in range(frames):
        if not BOT_RUNNING: break
        ts = datetime.now().strftime("%H%M%S%f")
        try: await page.screenshot(path=f"{CAPTURE_DIR}/{ts}_{step_name}.jpg")
        except: pass
        await asyncio.sleep(0.2)

# --- CORE LOGIC LOOP ---
async def master_loop():
    current_number = get_next_number()
    retry_same_number = False

    while BOT_RUNNING:
        if not retry_same_number: current_number = get_next_number()
        
        log_msg(f"🎬 SESSION START | Number: {current_number}")
        result = await run_single_session(current_number)
        
        if result == "success":
            log_msg("🎉 Number Verified! Moving to next...")
            retry_same_number = False
        elif result == "retry":
            log_msg("⚠️ Process Failed (Element Missing). Retrying SAME Number...")
            retry_same_number = True
        else:
            break # Stopped
        
        await asyncio.sleep(2)

async def run_single_session(phone_number):
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
            if not BOT_RUNNING: return "stopped"
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=60000)
            await burst_wait(page, 2, "01_load")

            # --- STRICT NAVIGATION START ---
            
            # 1. REGISTER
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 2, "02_reg")
            else:
                log_msg("❌ CRITICAL: Register button not found! Retrying...")
                await browser.close()
                return "retry"

            # 2. TERMS
            agree = page.get_by_text("Agree", exact=True).first
            if await agree.count() == 0: agree = page.get_by_text("Next", exact=True).first
            
            if await agree.count() > 0:
                await visual_tap(page, agree, "Terms")
                await burst_wait(page, 2, "03_terms")
            else:
                log_msg("❌ CRITICAL: Agree/Next not found! Retrying...")
                await browser.close()
                return "retry"

            # 3. DOB
            await page.mouse.move(200, 500); await page.mouse.down()
            await page.mouse.move(200, 800, steps=10); await page.mouse.up()
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: 
                await visual_tap(page, dob_next, "DOB")
                await burst_wait(page, 2, "04_dob")
            else:
                log_msg("❌ CRITICAL: DOB Next not found! Retrying...")
                await browser.close()
                return "retry"

            # 4. PHONE OPTION
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: 
                await visual_tap(page, use_phone, "PhoneOpt")
                await burst_wait(page, 2, "05_phone")
            else:
                log_msg("❌ CRITICAL: 'Use phone number' not found! Retrying...")
                await browser.close()
                return "retry"

            # 5. COUNTRY SWITCH (Strict Check)
            log_msg("🌍 Switching Country...")
            hk = page.get_by_text("Hong Kong").first
            if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
            
            if await hk.count() > 0:
                await visual_tap(page, hk, "Country")
                await burst_wait(page, 2, "06_list")
                
                search = page.locator("input").first
                if await search.count() > 0:
                    await visual_tap(page, search, "Search")
                    await page.keyboard.type("Russia", delay=50)
                    await burst_wait(page, 2, "07_typed")
                    
                    rus = page.get_by_text("Russia", exact=False).first
                    if await rus.count() > 0: 
                        await visual_tap(page, rus, "Russia")
                    else:
                        log_msg("❌ Russia not found in list!")
                        await browser.close(); return "retry"
                else:
                    log_msg("❌ Search box not found!")
                    await browser.close(); return "retry"
            else:
                log_msg("❌ CRITICAL: Country Selector not found! Retrying...")
                await browser.close()
                return "retry"

            # 6. INPUT NUMBER
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for c in phone_number:
                    if not BOT_RUNNING: return "stopped"
                    await page.keyboard.type(c); await asyncio.sleep(0.05)
                await page.touchscreen.tap(350, 100) # Close KB
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code").first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Monitoring for Captcha (60s)...")
                    
                    # --- CAPTCHA LOOP ---
                    start_time = time.time()
                    while BOT_RUNNING:
                        if time.time() - start_time > 60:
                            log_msg("⏰ Timeout waiting for Captcha.")
                            await browser.close()
                            return "retry"

                        # Check for Captcha Frame
                        captcha_frame = None
                        for frame in page.frames:
                            try:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_frame = frame; break
                            except: pass
                        
                        if captcha_frame:
                            log_msg("🧩 CAPTCHA FOUND! Calling Solver...")
                            session_id = f"sess_{int(time.time())}"
                            ai_success = await solve_captcha(page, session_id, logger=log_msg)
                            
                            if not ai_success:
                                log_msg("⚠️ Solver Failed. Retrying same number...")
                                await browser.close(); return "retry"
                            
                            log_msg("⏳ Checking result (Wait 10s)...")
                            await burst_wait(page, 10, "11_check")
                            
                            # Verify if Captcha is Gone
                            is_still_there = False
                            for frame in page.frames:
                                try:
                                    if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                        is_still_there = True; break
                                except: pass
                            
                            if not is_still_there:
                                log_msg("✅ SUCCESS! CAPTCHA GONE.")
                                await burst_wait(page, 3, "12_done")
                                await browser.close()
                                return "success" # ONLY HERE WE RETURN SUCCESS
                            else:
                                log_msg("🔁 Verification Failed. Trying loop again...")
                                await asyncio.sleep(2)
                                continue
                        else:
                            await asyncio.sleep(1)
                else:
                    log_msg("❌ Get Code Button not found!")
                    await browser.close(); return "retry"
            else:
                log_msg("❌ Input field not found!")
                await browser.close(); return "retry"

            await browser.close()
            log_msg("⚠️ End of script reached without success.")
            return "retry" # Default to retry if fell through

        except Exception as e:
            log_msg(f"❌ Crash: {str(e)}")
            await browser.close()
            return "retry"