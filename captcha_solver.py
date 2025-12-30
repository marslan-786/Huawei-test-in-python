import asyncio
import random
import time
# import cv2  <-- Future use for exact calculation
# import numpy as np

async def solve_captcha(page):
    print("🧩 CAPTCHA DETECTED! Initializing Solver...")
    
    # 1. FIND IFRAME
    # Huawei captcha usually loads inside an iframe
    frames = page.frames
    captcha_frame = None
    
    # Dhoondo k kis frame me captcha hai
    for frame in frames:
        try:
            # Check for slider element
            if await frame.locator(".uc-btn-handler").count() > 0:
                captcha_frame = frame
                print("✅ Slider found in frame!")
                break
        except: continue
        
    if not captcha_frame:
        print("❌ Could not find Captcha Frame")
        return False

    # 2. LOCATE ELEMENTS
    try:
        slider_btn = captcha_frame.locator(".uc-btn-handler").first
        background_img = captcha_frame.locator("#img_Verify").first # Background image ID usually
        
        # Screenshot for debugging (Taake hum bad me OpenCV adjust kar sakein)
        timestamp = int(time.time())
        await captcha_frame.screenshot(path=f"./captures/captcha_debug_{timestamp}.jpg")
        print(f"📸 Captcha Screenshot Saved: captcha_debug_{timestamp}.jpg")

        # 3. GET COORDINATES
        box = await slider_btn.bounding_box()
        if not box: return False
        
        start_x = box['x'] + (box['width'] / 2)
        start_y = box['y'] + (box['height'] / 2)
        
        # --- HUMAN DRAG LOGIC ---
        # Abhi hum "Blind Drag" kar rahay hain test k liye.
        # Baad me hum yahan OpenCV se exact 'end_x' nikalenge.
        
        # Huawei sliders usually need to move between 100px to 250px
        # Let's try a safe drag to middle for testing interaction
        distance = random.randint(150, 220) 
        end_x = start_x + distance
        
        print(f"🖱️ Dragging Slider from {start_x} to {end_x}...")
        
        # Mouse Down
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await asyncio.sleep(0.3)
        
        # Drag Movement (Thora upar neechay shake karte hue - Human behavior)
        current_x = start_x
        while current_x < end_x:
            step = random.randint(5, 15)
            current_x += step
            
            # Thora sa Y-axis movement (Shake)
            y_shake = start_y + random.randint(-2, 2)
            
            await page.mouse.move(current_x, y_shake)
            await asyncio.sleep(random.uniform(0.01, 0.05)) # Fast movements
            
        # Mouse Up (Release)
        await page.mouse.up()
        print("✅ Drag Complete. Waiting for verification...")
        
        await asyncio.sleep(3)
        return True

    except Exception as e:
        print(f"❌ Solver Error: {e}")
        return False