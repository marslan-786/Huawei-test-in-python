import os
import glob
import asyncio
import random
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async  # 🕵️ Stealth Mode

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"

# Desktop URL (Mobile 'wap' hata diya hai)
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?service=https%3A%2F%2Foauth-login.cloud.huawei.com%2Foauth2%2Fv2%2Fauthorize%3Faccess_type%3Doffline&loginChannel=61000000&reqClientType=61&lang=en-us"

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
            body { background: #1a1a1a; color: #fff; font-family: sans-serif; padding: 20px; text-align: center; }
            .box { border: 1px solid #444; padding: 15px; margin: 10px auto; max-width: 800px; background: #222; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #00bcd4; color: black; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ddd; font-size: 14px; background: black; }
            .gallery img { height: 160px; border: 2px solid #555; margin: 4px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🖱️ HUAWEI HUMAN CLICKER</h1>
        <div class="box">
            <button onclick="startBot()">🚀 START HUMAN MODE</button>
            <button onclick="refreshData()" style="background: #4caf50; color: white;">🔄 REFRESH</button>
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
    log_msg(">>> COMMAND: Human Mode (Desktop + Stealth)")
    bt.add_task(run_human_agent)
    return {"status": "started"}

# --- HUMAN MOVEMENT HELPER ---
async def human_click(page, element):
    """Moves mouse naturally to element and clicks with realistic timing"""
    # 1. Get Element Position
    box = await element.bounding_box()
    if not box: return False
    
    start_x = box['x'] + (box['width'] / 2)
    start_y = box['y'] + (box['height'] / 2)
    
    # Randomize exact click point (Insan bilkul beach main click nahi karta)
    target_x = start_x + random.uniform(-10, 10)
    target_y = start_y + random.uniform(-5, 5)
    
    # 2. Move Mouse (Hover)
    log_msg(f"🖱️ Moving mouse to {int(target_x)}, {int(target_y)}...")
    await page.mouse.move(target_x, target_y, steps=15) # steps=15 means slow movement
    await asyncio.sleep(random.uniform(0.2, 0.5)) # Pause before clicking
    
    # 3. Press Down
    log_msg("🖱️ Mouse Down...")
    await page.mouse.down()
    
    # 4. Wait (Human press duration)
    await asyncio.sleep(random.uniform(0.05, 0.15))
    
    # 5. Release
    log_msg("🖱️ Mouse Up (Click Complete)")
    await page.mouse.up()
    
    return True

# --- MAIN LOGIC ---
async def run_human_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # DESKTOP SETUP (Not Mobile)
            # stealth mode on karne k liye args
            args = ["--disable-blink-features=AutomationControlled"]
            
            browser = await p.chromium.launch(headless=True, args=args)
            
            # Standard Desktop Viewport (1920x1080)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            # Activate Stealth (Hides 'navigator.webdriver')
            await stealth_async(page)

            log_msg("🚀 Loading Desktop Page...")
            await page.goto(MAGIC_URL)
            await asyncio.sleep(5)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")

            # --- STEP 1: CHANGE COUNTRY (Desktop has different layout) ---
            # Desktop page shayad default China/Hong Kong ho, check karte hain
            # Lekin pehle input dhoondte hain
            
            # Note: Desktop layout might be different. Let's look for Phone Input.
            log_msg("🔍 Finding Phone Input...")
            
            # Try specific desktop selectors
            # Huawei desktop usually has a dropdown for country code
            
            # For now, let's assume direct input strategy first
            phone_input = page.locator("input[type='text']").first # Desktop often uses text, not tel
            
            # Agar generic input na mile to specific class dhoondo
            if await phone_input.count() == 0:
                 phone_input = page.locator(".huawei-input").first

            if await phone_input.count() > 0:
                await human_click(page, phone_input)
                await page.keyboard.type(TARGET_PHONE, delay=random.randint(50, 150)) # Human typing speed
                log_msg(f"⌨️ Typed {TARGET_PHONE}")
                await asyncio.sleep(1)
                await page.screenshot(path=f"{CAPTURE_DIR}/02_filled.jpg")
                
                # Blur out
                await page.mouse.click(500, 500)
            else:
                log_msg("❌ Phone input not found (Layout might be different on Desktop)")
                # Let's take a screenshot to see what desktop view looks like
                await page.screenshot(path=f"{CAPTURE_DIR}/debug_layout.jpg")
                await browser.close()
                return

            # --- STEP 2: GET CODE (HUMAN CLICK) ---
            log_msg("🔍 Looking for 'Get code'...")
            
            # Desktop pe aksar button "Get Code" text nahi, balki "Obtain code" ya kuch aur hota hai
            # Hum generic button dhoondenge jo 'code' contain kare
            get_code_btn = page.locator("div, span, button").filter(has_text="Get code").last
            
            if await get_code_btn.count() == 0:
                 # Try variations
                 get_code_btn = page.locator("div, span, button").filter(has_text="Code").last
            
            if await get_code_btn.count() > 0:
                # Scroll into view
                await get_code_btn.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                
                # Highlight for screenshot
                box = await get_code_btn.bounding_box()
                if box:
                    await page.evaluate(f"""
                        var d = document.createElement('div');
                        d.style.position='absolute';d.style.left='{box['x']}px';d.style.top='{box['y']}px';
                        d.style.width='{box['width']}px';d.style.height='{box['height']}px';
                        d.style.border='3px solid red'; d.style.zIndex='9999'; d.style.pointerEvents='none';
                        document.body.appendChild(d);
                    """)
                    await page.screenshot(path=f"{CAPTURE_DIR}/03_target_found.jpg")
                
                log_msg("🖱️ Performing Human Click...")
                await human_click(page, get_code_btn)
                log_msg("✅ Click Executed.")
            else:
                log_msg("❌ 'Get Code' button not found!")
                await page.screenshot(path=f"{CAPTURE_DIR}/debug_no_button.jpg")

            # --- MONITORING ---
            log_msg("👀 Watching (60s)...")
            for i in range(1, 16):
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")
                
            log_msg("✅ Finished.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")