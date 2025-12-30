import os
import glob
import asyncio
import random
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"

# 🇺🇸 USA LINK
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=us&countryCode=us&lang=en-us"

# 👇 PROXY CONFIG 👇
PROXY_CONFIG = {
    "server": "http://142.111.48.253:7030", 
    "username": "wwwsyxzg", 
    "password": "582ygxexguhx"
}

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

# --- HELPER: GENERATE NUMBER ---
def generate_california_number():
    prefix = random.randint(200, 999)
    suffix = random.randint(1000, 9999)
    return f"310{prefix}{suffix}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Slow-Mo Bot</title>
        <style>
            body { background: #0d1117; color: #58a6ff; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #238636; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #30363d; padding: 10px; color: #8b949e; background: #010409; margin-bottom: 20px; }
            .gallery img { height: 110px; border: 1px solid #30363d; margin: 3px; border-radius: 4px; }
            #video-section { display:none; margin-top:20px; border: 1px dashed #30363d; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>🐢 SLOW MOTION & VISUAL CLICK BOT</h1>
        <button onclick="startBot()">🚀 START SLOW MODE</button>
        <button onclick="refreshData()" style="background: #1f6feb;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #8957e5;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls width="600"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> INITIALIZING SLOW MOTION..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
                });
            }
            function makeVideo() {
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        document.getElementById('video-section').style.display = 'block';
                        document.getElementById('v-player').src = "/captures/proof.mp4?t=" + Date.now();
                    }
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
    bt.add_task(run_slow_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=1, format='FFMPEG') as writer: # 1 FPS for slow video
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- 🔴 VISUAL CLICK HELPER ---
async def visual_click(page, element, desc):
    box = await element.bounding_box()
    if box:
        x = box['x'] + box['width'] / 2
        y = box['y'] + box['height'] / 2
        
        # 1. Add RED DOT Marker
        await page.evaluate(f"""
            var dot = document.createElement('div');
            dot.style.position = 'absolute';
            dot.style.left = '{x}px';
            dot.style.top = '{y}px';
            dot.style.width = '15px';
            dot.style.height = '15px';
            dot.style.backgroundColor = 'red';
            dot.style.borderRadius = '50%';
            dot.style.border = '2px solid yellow';
            dot.style.zIndex = '99999';
            dot.id = 'click-marker';
            document.body.appendChild(dot);
        """)
        
        log_msg(f"🖱️ Moving to {desc}...")
        await page.mouse.move(x, y, steps=30) # Slow move
        await asyncio.sleep(0.5)
        
        log_msg(f"🔴 CLICKING {desc}...")
        await page.mouse.down()
        await asyncio.sleep(0.2)
        await page.mouse.up()
        
        # Leave dot for a moment so screenshot captures it
        return True
    return False

# --- 🐢 SLOW TYPING HELPER ---
async def slow_type(page, text):
    log_msg(f"⌨️ Typing {text} slowly (5s)...")
    for char in text:
        await page.keyboard.type(char)
        # 0.5 sec delay per char * 10 chars = 5 seconds
        await asyncio.sleep(0.5) 
    log_msg("✅ Typing Complete")

# --- MAIN LOGIC ---
async def run_slow_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        current_number = generate_california_number()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"],
                proxy=PROXY_CONFIG
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                timezone_id="America/Los_Angeles",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Injection
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

            log_msg("🚀 1. Loading Website...")
            try:
                await page.goto(MAGIC_URL, timeout=60000)
            except:
                log_msg("❌ Network Error")
                await browser.close()
                return

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_loaded.jpg")

            # FIND INPUT
            log_msg("🔍 Finding Input...")
            inp = page.locator("input.huawei-input").first
            if await inp.count() == 0: inp = page.locator("input[type='text']").first
            
            if await inp.count() == 0:
                log_msg("❌ Input Not Found")
                await browser.close()
                return

            # CLICK INPUT
            await visual_click(page, inp, "Input Field")
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_input_focused.jpg")

            # --- 🐢 SLOW TYPING (5 Seconds) ---
            await slow_type(page, current_number)
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_typed.jpg")
            await page.mouse.click(500, 500) # Blur
            await asyncio.sleep(1)

            # --- LOOP ---
            retry_count = 0
            max_retries = 50
            
            while retry_count < max_retries:
                retry_count += 1
                
                # Number Rotation
                if retry_count > 1 and retry_count % 2 != 0:
                    log_msg("♻️ Changing Phone Number...")
                    current_number = generate_california_number()
                    await inp.click()
                    await inp.fill("")
                    await slow_type(page, current_number)
                    await page.mouse.click(500, 500)

                # 1. CLICK GET CODE
                btn = page.locator(".get-code-btn").first
                if await btn.count() == 0: btn = page.get_by_text("Get code").first
                
                if await btn.count() > 0:
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_loop_{retry_count}_A_before_click.jpg")
                    await visual_click(page, btn, "Get Code Button")
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_loop_{retry_count}_B_after_click.jpg")
                    
                    # Wait 3 seconds to see result (As requested)
                    log_msg("⏳ Waiting 3s for response...")
                    await asyncio.sleep(3)
                else:
                    log_msg("❌ Button Lost!")
                    break

                # 2. CHECK RESULT
                error_detected = False
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_loop_{retry_count}_C_response.jpg")

                # Check Captcha
                if len(page.frames) > 1:
                    log_msg("🎉 BINGO! CAPTCHA DETECTED!")
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_SUCCESS.jpg")
                    await browser.close()
                    return

                # Check Error
                if await page.get_by_text("An unexpected problem").count() > 0:
                    error_detected = True
                
                if error_detected:
                    log_msg(f"🛑 Error Detected on Try {retry_count}")
                    
                    # Find OK
                    ok_btn = page.locator("div.hwid-dialog-btn").filter(has_text="OK").first
                    if await ok_btn.count() == 0: ok_btn = page.get_by_text("OK", exact=True).first
                    
                    if await ok_btn.count() > 0:
                        await visual_click(page, ok_btn, "OK Button")
                        await page.screenshot(path=f"{CAPTURE_DIR}/monitor_loop_{retry_count}_D_ok_clicked.jpg")
                        
                        # --- 10 SECOND COUNTDOWN ---
                        log_msg("⏳ Cooldown started (10s)...")
                        for s in range(10, 0, -1):
                            log_msg(f"🕒 Waiting... {s}s")
                            await asyncio.sleep(1)
                    else:
                        log_msg("⚠️ Error present but OK button missing")
                        await asyncio.sleep(5)
                else:
                    log_msg("❓ No popup yet, retrying...")

            log_msg("❌ Max retries reached.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ Error: {str(e)}")