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
NUMBERS_FILE = "numbers.txt"

# 📱 MOBILE LINK
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html#/wapRegister/regByPhone"

# 👇 PROXY CONFIG 👇
PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
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

# --- FILE HELPER ---
def get_next_number():
    if not os.path.exists(NUMBERS_FILE): return None
    with open(NUMBERS_FILE, "r") as f: lines = f.readlines()
    numbers = [line.strip() for line in lines if line.strip()]
    if not numbers: return None
    current_number = numbers[0]
    new_lines = numbers[1:] + [current_number]
    with open(NUMBERS_FILE, "w") as f: f.write("\n".join(new_lines))
    return current_number

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Deep Stealth</title>
        <style>
            body { background: #000; color: #00e5ff; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d50000; color: white; border-radius: 4px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; }
            .gallery img { height: 250px; border: 2px solid #333; margin: 3px; border-radius: 10px; }
            #video-section { display:none; margin-top:20px; }
        </style>
    </head>
    <body>
        <h1>🥷 DEEP STEALTH: REGION INJECTOR</h1>
        <p>Forcing Region: PK | Emulating: Samsung S23 Ultra</p>
        <button onclick="startBot()">🚀 START DEEP AGENT</button>
        <button onclick="refreshData()" style="background: #2979ff;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #00c853;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="450"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> INJECTING SCRIPT..."); }
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
    bt.add_task(run_deep_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=1, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- VISUAL TOUCH ---
async def visual_tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '20px'; height = '20px'; background = 'rgba(255, 0, 0, 0.5)';
                dot.style.borderRadius = '50%'; border = '2px solid white'; zIndex = '99999';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            await asyncio.sleep(0.5)
            return True
    except: pass
    return False

# --- MAIN AGENT ---
async def run_deep_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        while True:
            current_number = get_next_number()
            if not current_number:
                log_msg("❌ No numbers left!")
                return
            
            log_msg(f"📱 Processing: {current_number}")

            async with async_playwright() as p:
                # 1. ARGS TO HIDE AUTOMATION
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--use-gl=egl",
                    "--disable-dev-shm-usage",
                    # Important: Ignore default automation flags
                    "--disable-infobars",
                    "--hide-scrollbars",
                ]

                browser = await p.chromium.launch(
                    headless=True,
                    args=args,
                    proxy=PROXY_CONFIG,
                    # Ignore default playwright args that leak identity
                    ignore_default_args=["--enable-automation"] 
                )

                # 2. SAMSUNG S23 ULTRA PROFILE
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
                    viewport={"width": 412, "height": 915},
                    device_scale_factor=3.0,
                    is_mobile=True,
                    has_touch=True,
                    timezone_id="Asia/Karachi", # Force PK Timezone
                    locale="en-PK"
                )
                
                # 3. FORCE NETWORK HEADERS (Client Hints)
                # Ye sab se important hai! Huawei ko batata hai k platform Android hai
                await context.set_extra_http_headers({
                    "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                    "sec-ch-ua-mobile": "?1",
                    "sec-ch-ua-platform": '"Android"',
                    "Upgrade-Insecure-Requests": "1"
                })

                page = await context.new_page()

                # 4. INJECT REGION & REMOVE WEBDRIVER (Before Page Load)
                await page.add_init_script("""
                    // 1. Hide WebDriver
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    
                    // 2. Force LocalStorage for Region PK
                    // Huawei uses localStorage keys like 'countryCode', 'regionCode'
                    try {
                        localStorage.setItem('countryCode', 'pk');
                        localStorage.setItem('regionCode', 'pk');
                        localStorage.setItem('site', 'pk');
                        localStorage.setItem('lang', 'en-us');
                    } catch(e) {}
                """)

                log_msg("🚀 Loading Page (With Injected Region PK)...")
                try:
                    await page.goto(MAGIC_URL, timeout=60000)
                except:
                    log_msg("❌ Network Fail")
                    await browser.close()
                    continue

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_loaded.jpg")

                # FIND INPUT
                inp = page.locator("input[type='tel']").first
                if await inp.count() == 0: inp = page.locator("input").first
                
                if await inp.count() > 0:
                    await visual_tap(page, inp, "Input")
                    
                    # Human Typing
                    for char in current_number:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    await page.touchscreen.tap(10, 100) # Blur
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_typed.jpg")
                else:
                    log_msg("❌ Input Not Found")
                    await browser.close()
                    continue

                # GET CODE
                retry = 0
                max_retries = 2
                
                while retry < max_retries:
                    retry += 1
                    btn = page.locator(".get-code-btn").first
                    if await btn.count() == 0: btn = page.get_by_text("Get code", exact=False).first
                    
                    if await btn.count() > 0:
                        await visual_tap(page, btn, "Get Code")
                        log_msg("⏳ Waiting 5s...")
                        await asyncio.sleep(5)
                    else:
                        log_msg("❌ Button Lost")
                        break
                    
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{current_number}_{retry}.jpg")

                    # CHECK SUCCESS
                    if len(page.frames) > 1 or await page.locator("iframe").count() > 0:
                        log_msg("🎉 BINGO! CAPTCHA DETECTED! (Region PK Success)")
                        await page.screenshot(path=f"{CAPTURE_DIR}/monitor_SUCCESS.jpg")
                        await browser.close()
                        return

                    # CHECK ERROR
                    if await page.get_by_text("Unexpected problem").count() > 0:
                        log_msg(f"🛑 Blocked on Try {retry}")
                        ok = page.get_by_text("OK").first
                        if await ok.count() > 0:
                            await visual_tap(page, ok, "OK")
                            log_msg("⏳ Waiting 10s...")
                            await asyncio.sleep(10)
                        else: await asyncio.sleep(5)
                    else:
                        log_msg("❓ Checking again...")
                        await asyncio.sleep(2)

                log_msg("❌ Rotating...")
                await browser.close()

    except Exception as e:
        log_msg(f"❌ Error: {str(e)}")