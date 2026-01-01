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
from pymongo import MongoClient
from bson.binary import Binary
import base64

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

MONGO_URI = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"
DB_NAME = "huawei_captcha"
COLLECTION_NAME = "captchas"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "arldpbwk-rotate", 
    "password": "iak7d1keh2ix"
}

# MongoDB Connection
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    captcha_collection = db[COLLECTION_NAME]
    mongo_client.server_info()  # Test connection
    print("✅ MongoDB Connected Successfully")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
    captcha_collection = None

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

logs = []
bot_running = False
stop_requested = False

def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 500: logs.pop()

def load_numbers():
    """Load numbers from numbers.txt file"""
    if not os.path.exists(NUMBERS_FILE):
        log_msg(f"❌ {NUMBERS_FILE} not found!")
        return []
    
    with open(NUMBERS_FILE, 'r') as f:
        numbers = [line.strip() for line in f if line.strip()]
    log_msg(f"📋 Loaded {len(numbers)} numbers from file")
    return numbers

def save_captcha_to_db(image_path, phone_number, session_info):
    """Save CAPTCHA image to MongoDB"""
    if captcha_collection is None:
        log_msg("❌ MongoDB not connected, skipping save")
        return False
    
    try:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
        
        document = {
            "timestamp": datetime.now(),
            "phone_number": phone_number,
            "session_info": session_info,
            "image": Binary(img_data),
            "image_size": len(img_data)
        }
        
        result = captcha_collection.insert_one(document)
        log_msg(f"✅ CAPTCHA saved to DB (ID: {result.inserted_id})")
        return True
    except Exception as e:
        log_msg(f"❌ Error saving to DB: {e}")
        return False

def get_captcha_count():
    """Get total number of CAPTCHAs in database"""
    if captcha_collection is None:
        return 0
    try:
        return captcha_collection.count_documents({})
    except:
        return 0

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei CAPTCHA Collector</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 12px 24px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            button:disabled { background: #555; cursor: not-allowed; }
            
            .status-bar { 
                background: #333; color: yellow; padding: 10px; margin: 10px auto; 
                width: 80%; border-radius: 5px; font-weight: bold; display: none; 
            }

            .logs { height: 250px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; font-size: 12px; color: #ccc; }
            
            #video-section { 
                display:none; 
                margin: 20px auto; 
                border: 3px solid #00e676; 
                padding:15px; 
                background: #111;
                width: fit-content;
                border-radius: 10px;
            }

            .stats { 
                background: #1a1a1a; 
                padding: 15px; 
                margin: 20px auto; 
                width: 80%; 
                border-radius: 5px;
                border: 2px solid #00e676;
            }
            
            .stats h3 { margin: 0 0 10px 0; color: #00e676; }
            .stats p { margin: 5px 0; font-size: 16px; }

            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px; margin-top: 20px; }
            .gallery img { height: 60px; border: 1px solid #333; opacity: 0.9; }
            .gallery img:hover { height: 150px; border-color: white; z-index:999; transition: 0.1s; }
        </style>
    </head>
    <body>
        <h1>🇷🇺 HUAWEI CAPTCHA COLLECTOR</h1>
        <p>Automated CAPTCHA Collection System | MongoDB Storage</p>
        
        <div>
            <button id="startStopBtn" onclick="toggleBot()">🚀 START COLLECTION</button>
            <button onclick="getLiveStatus()" style="background: #2962ff;">📊 LIVE STATUS</button>
            <button onclick="window.location.href='/database_captchas'" style="background: #ff6f00;">📦 VIEW DATABASE</button>
            <button onclick="makeVideo()" style="background: #e91e63;">🎬 GENERATE VIDEO</button>
            <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH</button>
        </div>

        <div class="stats" id="stats">
            <h3>📊 SYSTEM STATUS</h3>
            <p>Bot Status: <span id="bot-status" style="color: yellow;">IDLE</span></p>
            <p>CAPTCHAs in Database: <span id="db-count" style="color: #00e676;">Loading...</span></p>
        </div>

        <div id="status-bar" class="status-bar"></div>
        
        <div class="logs" id="logs">Waiting for commands...</div>
        
        <div id="video-section">
            <h3 style="margin-top:0; color: #00e676;">🎬 REPLAY</h3>
            <video id="v-player" controls width="500" autoplay loop></video>
        </div>

        <h3>🎞️ FULL HISTORY FEED</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            let isRunning = false;

            function toggleBot() {
                const btn = document.getElementById('startStopBtn');
                
                if (!isRunning) {
                    fetch('/start', {method: 'POST'}).then(r => r.json()).then(d => {
                        if (d.status === "started") {
                            isRunning = true;
                            btn.textContent = "🛑 STOP COLLECTION";
                            btn.style.background = "#d32f2f";
                            document.getElementById('bot-status').textContent = "RUNNING";
                            document.getElementById('bot-status').style.color = "#00e676";
                            logUpdate(">>> COLLECTION STARTED...");
                        } else {
                            alert(d.message || "Failed to start");
                        }
                    });
                } else {
                    fetch('/stop', {method: 'POST'}).then(r => r.json()).then(d => {
                        isRunning = false;
                        btn.textContent = "🚀 START COLLECTION";
                        btn.style.background = "#6200ea";
                        document.getElementById('bot-status').textContent = "STOPPED";
                        document.getElementById('bot-status').style.color = "red";
                        logUpdate(">>> COLLECTION STOPPED");
                    });
                }
            }

            function getLiveStatus() {
                fetch('/live_status').then(r => r.json()).then(d => {
                    document.getElementById('db-count').textContent = d.captcha_count;
                    document.getElementById('bot-status').textContent = d.bot_running ? "RUNNING" : "IDLE";
                    document.getElementById('bot-status').style.color = d.bot_running ? "#00e676" : "yellow";
                    
                    const status = document.getElementById('status-bar');
                    status.style.display = 'block';
                    status.style.color = "#00e676";
                    status.innerText = `✅ Database: ${d.captcha_count} CAPTCHAs | Bot: ${d.bot_running ? "RUNNING" : "IDLE"}`;
                    setTimeout(() => { status.style.display = 'none'; }, 5000);
                });
            }
            
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
                });
                getLiveStatus();
            }

            function makeVideo() {
                var status = document.getElementById('status-bar');
                status.style.display = 'block';
                status.innerText = "⏳ PROCESSING FRAMES... PLEASE WAIT...";
                status.style.color = "yellow";

                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        status.innerText = "✅ VIDEO READY! PLAYING BELOW...";
                        status.style.color = "#00e676";
                        
                        var vSection = document.getElementById('video-section');
                        vSection.style.display = 'block';
                        
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
                document.getElementById('logs').innerHTML = "<div>" + msg + "</div>" + document.getElementById('logs').innerHTML; 
            }
            
            // Auto-refresh every 5 seconds
            setInterval(refreshData, 5000);
            
            // Initial load
            getLiveStatus();
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    # Get latest 50 images only
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)[:50]
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.get("/live_status")
async def live_status():
    count = get_captcha_count()
    return JSONResponse({
        "captcha_count": count,
        "bot_running": bot_running,
        "timestamp": datetime.now().isoformat()
    })

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    global bot_running, stop_requested
    
    if bot_running:
        return {"status": "error", "message": "Bot is already running"}
    
    bot_running = True
    stop_requested = False
    bt.add_task(run_collection_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    global stop_requested
    stop_requested = True
    log_msg("🛑 Stop requested by user...")
    return {"status": "stopped"}

@app.get("/database_captchas", response_class=HTMLResponse)
async def view_database_captchas():
    """View all CAPTCHAs stored in MongoDB"""
    if captcha_collection is None:
        return "<h1>❌ MongoDB not connected</h1>"
    
    try:
        # Get all captchas from database
        captchas = list(captcha_collection.find().sort("timestamp", -1).limit(100))
        
        html_content = """
        <html>
        <head>
            <title>Database CAPTCHAs</title>
            <style>
                body { background: #000; color: #00e676; font-family: monospace; padding: 20px; }
                h1 { text-align: center; }
                .captcha-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }
                .captcha-card { background: #1a1a1a; border: 2px solid #00e676; border-radius: 10px; padding: 15px; }
                .captcha-card img { width: 100%; border-radius: 5px; }
                .captcha-info { margin-top: 10px; font-size: 12px; }
                .captcha-info p { margin: 5px 0; }
                .back-btn { display: block; width: 200px; margin: 20px auto; padding: 10px; text-align: center; background: #6200ea; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>📦 DATABASE CAPTCHAs (Latest 100)</h1>
            <a href="/" class="back-btn">← Back to Dashboard</a>
            <div class="captcha-grid">
        """
        
        for captcha in captchas:
            # Convert binary image to base64
            img_base64 = base64.b64encode(captcha['image']).decode('utf-8')
            timestamp = captcha['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            phone = captcha.get('phone_number', 'N/A')
            session = captcha.get('session_info', 'N/A')
            
            html_content += f"""
            <div class="captcha-card">
                <img src="data:image/jpeg;base64,{img_base64}" alt="CAPTCHA">
                <div class="captcha-info">
                    <p>📱 <strong>Phone:</strong> {phone}</p>
                    <p>🕒 <strong>Time:</strong> {timestamp}</p>
                    <p>📋 <strong>Session:</strong> {session}</p>
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        return f"<h1>❌ Error: {str(e)}</h1>"

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    if not files: return {"status": "error", "error": "No images found"}
    
    try:
        with imageio.get_writer(VIDEO_PATH, fps=15, format='FFMPEG', quality=8) as writer:
            for filename in files:
                try:
                    img = imageio.imread(filename)
                    writer.append_data(img)
                except:
                    continue
        return {"status": "done"}
    except Exception as e:
        print(f"Video Error: {e}")
        return {"status": "error", "error": str(e)}

async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: 
        pass
    return False

def cleanup_old_images():
    """Keep only latest 50 images, delete older ones"""
    try:
        files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
        if len(files) > 50:
            for old_file in files[50:]:
                try:
                    os.remove(old_file)
                except:
                    pass
    except:
        pass

async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Recording {step_name} ({seconds}s)...")
    frames = int(seconds / 0.1)
    for i in range(frames):
        ts = datetime.now().strftime("%H%M%S%f")
        filename = f"{ts}_{step_name}.jpg"
        await page.screenshot(path=f"{CAPTURE_DIR}/{filename}")
        await asyncio.sleep(0.1)
    
    # Cleanup after each burst
    cleanup_old_images()

# --- MAIN COLLECTION LOOP ---
async def run_collection_loop():
    global bot_running, stop_requested
    
    numbers = load_numbers()
    if not numbers:
        log_msg("❌ No numbers found in numbers.txt")
        bot_running = False
        return
    
    number_index = 0
    
    while not stop_requested:
        current_number = numbers[number_index]
        log_msg(f"🎬 Starting Session {number_index + 1} | Number: {current_number}")
        
        success = await run_single_session(current_number)
        
        # Move to next number
        number_index += 1
        if number_index >= len(numbers):
            log_msg("🔄 All numbers processed, restarting from beginning...")
            number_index = 0
        
        if stop_requested:
            break
        
        # Small delay between sessions
        await asyncio.sleep(2)
    
    bot_running = False
    log_msg("✅ Collection loop stopped")

async def run_single_session(phone_number):
    """Run a single session for one phone number"""
    
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
            
            # Cookie
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: 
                cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0: 
                await visual_tap(page, cookie_close, "Cookie")
            
            # Register
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: 
                reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 3, "02_reg_click")
            
            # Terms
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0: 
                await visual_tap(page, agree_text, "Terms")
            
            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: 
                agree_btn = page.get_by_text("Next", exact=True).first
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree_Next")
                await burst_wait(page, 3, "03_terms_done")

            # DOB
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: 
                await visual_tap(page, dob_next, "DOB_Next")
            await burst_wait(page, 2, "04_dob_done")

            # Phone Option
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: 
                await visual_tap(page, use_phone, "Use_Phone")
            await burst_wait(page, 2, "05_phone_screen")

            # --- COUNTRY SWITCH ---
            log_msg("🌍 Switching to RUSSIA...")
            hk_selector = page.get_by_text("Hong Kong").first
            if await hk_selector.count() == 0: 
                hk_selector = page.get_by_text("Country/Region").first
            
            if await hk_selector.count() > 0:
                await visual_tap(page, hk_selector, "Country_Selector")
                await burst_wait(page, 2, "06_list_opened")
                
                if await page.locator("input").count() > 0:
                    search_box = page.locator("input").first
                    await visual_tap(page, search_box, "Search_Box")
                    
                    log_msg("⌨️ Typing Russia...")
                    await page.keyboard.type("Russia", delay=100)
                    await burst_wait(page, 2, "07_typed")

                    target = page.get_by_text("Russia", exact=False).first
                    if await target.count() > 0:
                        await visual_tap(page, target, "Select_Russia")
                        await burst_wait(page, 3, "08_russia_set")
                    else:
                        log_msg("❌ Russia not found")
            
            # INPUT & CODE
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: 
                inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in phone_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.1)
                
                await page.touchscreen.tap(350, 100)
                await burst_wait(page, 1, "09_ready")
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: 
                    get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting for CAPTCHA...")
                    await burst_wait(page, 10, "10_waiting_captcha")

                    # CHECK FOR CAPTCHA AND SAVE TO DB
                    if len(page.frames) > 1:
                        log_msg("🧩 CAPTCHA DETECTED! Capturing...")
                        
                        # Take CAPTCHA screenshot
                        captcha_filename = f"{CAPTURE_DIR}/captcha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        await page.screenshot(path=captcha_filename)
                        
                        # Save to MongoDB
                        session_info = f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        save_captcha_to_db(captcha_filename, phone_number, session_info)
                        
                        await burst_wait(page, 3, "11_captcha_saved")
                        log_msg(f"✅ CAPTCHA saved for {phone_number}")
                    else:
                        log_msg("❓ No CAPTCHA frame detected")

            await browser.close()
            return True

        except Exception as e:
            log_msg(f"❌ Error in session: {str(e)}")
            await browser.close()
            return False