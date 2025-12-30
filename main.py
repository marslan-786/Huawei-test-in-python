import os
import time
import random
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from DrissionPage import ChromiumPage, ChromiumOptions

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

# Desktop URL (Mobile WAP hata diya hai taake click stable ho)
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?service=https%3A%2F%2Foauth-login.cloud.huawei.com%2Foauth2%2Fv2%2Fauthorize%3Faccess_type%3Doffline&loginChannel=61000000&reqClientType=61&lang=en-us"

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING ---
logs = []
def log_msg(message):
    timestamp = time.strftime("%H:%M:%S")
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
        <title>Huawei Drission Bot</title>
        <style>
            body { background: #121212; color: #03dac6; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 10px auto; max-width: 800px; background: #1e1e1e; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #bb86fc; color: black; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #e0e0e0; font-size: 14px; background: #000; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>👑 DRISSIONPAGE POWER BOT</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START POWER CLICK</button>
            <button onclick="refreshData()" style="background: #03dac6;">🔄 REFRESH</button>
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
    import glob
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    log_msg(">>> COMMAND: DrissionPage Mode")
    bt.add_task(run_drission_agent)
    return {"status": "started"}

# --- MAIN LOGIC (DRISSIONPAGE) ---
async def run_drission_agent():
    page = None
    try:
        import glob
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        # 1. Setup Options (The Anti-Detect Magic)
        co = ChromiumOptions()
        co.headless(True) # Server par True rakhna parega
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        # Setting a REAL user agent is critical
        co.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Point to installed chromium
        co.set_browser_path('/usr/bin/chromium')

        log_msg("🚀 Initializing DrissionPage...")
        page = ChromiumPage(co)

        log_msg("🌐 Navigating...")
        page.get(MAGIC_URL)
        
        # Wait logic in DrissionPage is smart
        # It waits for element to be present in DOM
        if page.wait.ele_displayed('text:Phone number', timeout=15):
             log_msg("✅ Page Loaded Successfully.")
        else:
             log_msg("⚠️ Timeout waiting for text.")

        time.sleep(2)
        page.get_screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

        # --- STEP 1: INPUT NUMBER ---
        log_msg("🔍 Finding Input...")
        
        # DrissionPage locators are very readable
        # '@type=text' means find input where type is text
        input_ele = page.ele('@type=text') 
        
        if not input_ele:
             # Fallback
             input_ele = page.ele('tag:input')

        if input_ele:
            # Human Simulation: Click then Input
            input_ele.click() 
            time.sleep(0.5)
            
            log_msg(f"⌨️ Typing {TARGET_PHONE}...")
            input_ele.input(TARGET_PHONE)
            time.sleep(1)
            
            page.get_screenshot(path=f"{CAPTURE_DIR}/02_filled.jpg")
            
            # Blur (Click on body)
            page.ele('tag:body').click(by_js=True) # JS click for background is safe
        else:
            log_msg("❌ Input not found!")
            return

        # --- STEP 2: GET CODE (The Power Click) ---
        log_msg("🔍 Looking for 'Get code'...")
        
        # Find element by text directly
        btn = page.ele('text:Get code')
        
        if btn:
            # Scroll to it
            # DrissionPage handles scrolling automatically mostly, but let's be safe
            
            log_msg("💥 PERFORMING POWER CLICK...")
            # .click() here is NOT WebDriver click. It's a CDP simulation.
            # It's indistinguishable from a real mouse event.
            btn.click()
            # Backup: If normal click fails, try JS click immediately
            # btn.click(by_js=True) 
            
            log_msg("✅ Click Sent.")
        else:
            log_msg("❌ Button not found!")

        # --- MONITORING ---
        log_msg("👀 Watching (30s)...")
        for i in range(1, 16):
            time.sleep(2)
            page.get_screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")
            
            # Check for captchas/iframes easily
            if page.ele('tag:iframe'):
                log_msg(f"⚠️ IFRAME/CAPTCHA DETECTED (Frame {i})")
        
        log_msg("✅ Finished.")

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")
    finally:
        if page:
            page.quit()