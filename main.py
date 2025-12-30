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

# --- IMPORT SOLVER ---
from captcha_solver import solve_captcha

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
    "password": "582ygxexguhx"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
# Ensure sub-directories exist for AI
if not os.path.exists(f"{CAPTURE_DIR}/debug_ai"): os.makedirs(f"{CAPTURE_DIR}/debug_ai")

app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 500: logs.pop()

def generate_russia_number():
    prefix = "9"
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{rest}"

# --- DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Bot Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #0d0d0d; color: #00e676; font-family: 'Segoe UI', monospace; padding: 20px; text-align: center; margin: 0; }
            h1 { margin-bottom: 10px; text-transform: uppercase; letter-spacing: 2px; }
            
            /* BUTTONS */
            .btn { 
                padding: 12px 20px; font-weight: bold; cursor: pointer; border:none; margin: 5px; 
                color: white; border-radius: 6px; font-size: 14px; transition: 0.2s; width: 250px;
                display: inline-block;
            }
            .btn:hover { opacity: 0.8; transform: scale(1.02); }
            .btn-start { background: #6200ea; }
            .btn-view { background: #2962ff; }
            .btn-close { background: #d50000; }
            .btn-ai { background: #ff6d00; }
            .btn-video { background: #c51162; }
            .btn-refresh { background: #00bfa5; width: auto; }

            /* LOGS TERMINAL */
            .logs-container {
                width: 90%; margin: 0 auto; text-align: left;
                background: #111; border: 1px solid #333; border-radius: 8px;
                padding: 10px; height: 250px; overflow-y: auto;
                font-family: monospace; font-size: 12px; color: #ccc;
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            }
            .log-entry { padding: 2px 0; border-bottom: 1px solid #222; }

            /* SECTIONS */
            .section { margin-top: 20px; padding: 10px; border-top: 1px solid #333; }
            .hidden { display: none; }
            
            /* GALLERY */
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin-top: 10px; }
            .gallery img { height: 80px; border: 1px solid #444; border-radius: 4px; cursor: pointer; }
            .gallery img:hover { transform: scale(1.5); z-index: 100; border-color: white; }

            /* AI GALLERY SPECIFIC */
            .ai-gallery img { height: 120px; border: 2px solid #ff6d00; }

            /* VIDEO SECTION */
            #video-status { font-weight: bold; margin: 10px; font-size: 14px; min-height: 20px; }
            video { border: 2px solid #c51162; border-radius: 8px; margin-top: 10px; width: 80%; max-width: 600px; }

        </style>
    </head>
    <body>
        <h1>🤖 HUAWEI BOT PANEL</h1>
        
        <div>
            <button class="btn btn-start" onclick="startBot()">🚀 START BOT</button>
            <button class="btn btn-refresh" onclick="refreshData()">🔄 REFRESH DATA</button>
        </div>

        <h3 style="margin-bottom: 5px; text-align: left; width: 90%; margin: 10px auto;">📟 TERMINAL LOGS</h3>
        <div class="logs-container" id="logs">Loading logs...</div>

        <div class="section">
            <button id="btn-pics" class="btn btn-view" onclick="togglePictures()">📸 VIEW CAPTURES</button>
            
            <div id="gallery-wrapper" class="hidden">
                <div class="gallery" id="gallery"></div>
            </div>
        </div>

        <div class="section">
            <button id="btn-ai" class="btn btn-ai" onclick="toggleAI()">🧠 VIEW AI ANALYSIS</button>
            
            <div id="ai-wrapper" class="hidden">
                <p style="color: #ff9e80; font-size: 12px;">(Preview of what AI sees & predicted result)</p>
                <div class="gallery ai-gallery" id="ai-gallery"></div>
            </div>
        </div>

        <div class="section">
            <button class="btn btn-video" onclick="makeVideo()">🎬 GENERATE VIDEO</button>
            
            <div id="video-status"></div>
            
            <div id="video-wrapper" class="hidden">
                <video id="v-player" controls autoplay loop></video>
            </div>
        </div>

        <script>
            // --- STATE VARIABLES ---
            let showPics = false;
            let showAI = false;

            function startBot() { 
                fetch('/start', {method: 'POST'}); 
                logUpdate(">>> COMMAND SENT: START BOT"); 
            }

            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    // Update Logs
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div class="log-entry">${l}</div>`).join('');
                    
                    // Update Main Gallery
                    if (showPics) {
                        document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                    }

                    // Update AI Gallery
                    if (showAI) {
                         if(d.ai_images.length === 0) {
                             document.getElementById('ai-gallery').innerHTML = "<p>No AI images found yet.</p>";
                         } else {
                             document.getElementById('ai-gallery').innerHTML = d.ai_images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                         }
                    }
                });
            }

            function togglePictures() {
                showPics = !showPics;
                const wrapper = document.getElementById('gallery-wrapper');
                const btn = document.getElementById('btn-pics');

                if (showPics) {
                    wrapper.classList.remove('hidden');
                    btn.classList.remove('btn-view');
                    btn.classList.add('btn-close');
                    btn.innerText = "❌ CLOSE GALLERY";
                    refreshData(); // Fetch images immediately
                } else {
                    wrapper.classList.add('hidden');
                    btn.classList.remove('btn-close');
                    btn.classList.add('btn-view');
                    btn.innerText = "📸 VIEW CAPTURES";
                    document.getElementById('gallery').innerHTML = ""; // Clear to save memory
                }
            }

            function toggleAI() {
                showAI = !showAI;
                const wrapper = document.getElementById('ai-wrapper');
                const btn = document.getElementById('btn-ai');

                if (showAI) {
                    wrapper.classList.remove('hidden');
                    btn.innerText = "❌ CLOSE AI VIEW";
                    refreshData();
                } else {
                    wrapper.classList.add('hidden');
                    btn.innerText = "🧠 VIEW AI ANALYSIS";
                    document.getElementById('ai-gallery').innerHTML = "";
                }
            }

            function makeVideo() {
                var status = document.getElementById('video-status');
                var wrapper = document.getElementById('video-wrapper');
                
                status.innerText = "⏳ PROCESSING VIDEO... PLEASE WAIT...";
                status.style.color = "yellow";
                wrapper.classList.add('hidden'); // Hide player during generation

                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        status.innerText = "✅ VIDEO READY!";
                        status.style.color = "#00e676";
                        
                        wrapper.classList.remove('hidden');
                        var player = document.getElementById('v-player');
                        player.src = "/captures/proof.mp4?t=" + Date.now();
                        player.load();
                        player.play();
                    } else {
                        status.innerText = "❌ ERROR: " + d.error;
                        status.style.color = "red";
                    }
                });
            }

            function logUpdate(msg) { 
                var logs = document.getElementById('logs');
                logs.innerHTML = "<div class='log-entry'>[" + new Date().toLocaleTimeString() + "] " + msg + "</div>" + logs.innerHTML;
            }
            
            // Auto Refresh Logs Only (to keep UI responsive)
            setInterval(refreshData, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    # 1. Main Flow Images (Exclude AI debugging ones to keep main gallery clean)
    all_files = glob.glob(f'{CAPTURE_DIR}/*.jpg')
    flow_files = [f for f in all_files if "ai_" not in os.path.basename(f) and "debug" not in f]
    flow_files = sorted(flow_files, key=os.path.getmtime, reverse=True)

    # 2. AI Specific Images
    # We look for 'ai_solved_preview.jpg', '*_puzzle.png' and contents of 'debug_ai' folder
    ai_files = []
    
    # The main preview result
    if os.path.exists(f"{CAPTURE_DIR}/ai_solved_preview.jpg"):
        ai_files.append(f"{CAPTURE_DIR}/ai_solved_preview.jpg")
    
    # The raw puzzle screenshots
    ai_files.extend(glob.glob(f"{CAPTURE_DIR}/*_puzzle.png"))
    
    # The sliced tiles from debug folder
    ai_files.extend(glob.glob(f"{CAPTURE_DIR}/debug_ai/*.jpg"))
    
    # Sort AI files by time
    ai_files = sorted(ai_files, key=os.path.getmtime, reverse=True)

    # Prepare URLs
    flow_urls = [f"/captures/{os.path.basename(f)}" for f in flow_files]
    
    ai_urls = []
    for f in ai_files:
        if "debug_ai" in f:
            ai_urls.append(f"/captures/debug_ai/{os.path.basename(f)}")
        else:
            ai_urls.append(f"/captures/{os.path.basename(f)}")

    return JSONResponse({
        "logs": logs, 
        "images": flow_urls,
        "ai_images": ai_urls
    })

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    bt.add_task(run_russia_flow)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    # Filter out tiles to keep video clean
    files = [f for f in files if "debug" not in f and "ai_" not in f]
    
    if not files: return {"status": "error", "error": "No images found"}
    
    try:
        with imageio.get_writer(VIDEO_PATH, fps=15, format='FFMPEG', quality=8) as writer:
            for filename in files:
                try:
                    img = imageio.imread(filename)
                    writer.append_data(img)
                except: continue
        return {"status": "done"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

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
                dot.style.width = '20px'; height = '20px'; background = 'red';
                dot.style.borderRadius = '50%'; zIndex = '999999'; 
                dot.style.border = '2px solid yellow';
                document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Recording {step_name} ({seconds}s)...")
    frames = int(seconds / 0.1)
    for i in range(frames):
        ts = datetime.now().strftime("%H%M%S%f")
        filename = f"{ts}_{step_name}.jpg"
        await page.screenshot(path=f"{CAPTURE_DIR}/{filename}")
        await asyncio.sleep(0.1)

# --- MAIN FLOW ---
async def run_russia_flow():
    current_number = generate_russia_number()
    log_msg(f"🎬 Start Session | Number: {current_number}")

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
            await burst_wait(page, 3, "01_loaded")
            
            # (Cookie, Register, Terms logic same as before...)
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0: await visual_tap(page, cookie_close, "Cookie")
            
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 3, "02_reg_click")

            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0: await visual_tap(page, agree_text, "Terms")
            
            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree_Next")
                await burst_wait(page, 3, "03_terms_done")

            # DOB
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB_Next")
            await burst_wait(page, 2, "04_dob_done")

            # Phone Option
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "Use_Phone")
            await burst_wait(page, 2, "05_phone_screen")

            # Country Switch
            log_msg("🌍 Switching to RUSSIA...")
            hk_selector = page.get_by_text("Hong Kong").first
            if await hk_selector.count() == 0: hk_selector = page.get_by_text("Country/Region").first
            
            if await hk_selector.count() > 0:
                await visual_tap(page, hk_selector, "Country_Selector")
                await burst_wait(page, 2, "06_list_opened")
                
                if await page.locator("input").count() > 0:
                    search_box = page.locator("input").first
                    await visual_tap(page, search_box, "Search_Box")
                    await page.keyboard.type("Russia", delay=100)
                    await burst_wait(page, 2, "07_typed")
                    target = page.get_by_text("Russia", exact=False).first
                    if await target.count() > 0:
                        await visual_tap(page, target, "Select_Russia")
                        await burst_wait(page, 3, "08_russia_set")
            
            # Input & Code
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.1)
                
                await page.touchscreen.tap(350, 100)
                await burst_wait(page, 1, "09_ready")
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting 10s for CAPTCHA...")
                    await burst_wait(page, 10, "10_final")

                    if len(page.frames) > 1:
                        log_msg("🧩 CAPTCHA FOUND! Calling AI Solver...")
                        await solve_captcha(page, "SESSION_X")
                        await burst_wait(page, 5, "11_post_swap")
                    else:
                         log_msg("❓ No Captcha Frame.")

            await browser.close()
            log_msg("✅ Finished. Generate Video to watch.")

        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await browser.close()