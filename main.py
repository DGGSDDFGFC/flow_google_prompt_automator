import os
import re
import asyncio
from playwright.async_api import async_playwright
import urllib.request
import urllib.error

# --- CONFIGURATION ---
PROMPTS_FILE = "prompts.txt"
BASE_DIR = r"D:\youtube\stority"
FOLDER_PREFIX = "vid_photos"
START_INDEX = 6

def get_next_folder_path():
    """Finds the highest vid_photosX and returns the path for the next one."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        
    existing_dirs = []
    for item in os.listdir(BASE_DIR):
        # Look for folders that start with vid_photos
        if os.path.isdir(os.path.join(BASE_DIR, item)) and item.startswith(FOLDER_PREFIX):
            # Extract the raw number from the end (e.g. 6 from vid_photos6)
            match = re.search(r'\d+', item[len(FOLDER_PREFIX):])
            if match:
                existing_dirs.append(int(match.group()))
                
    if not existing_dirs:
        next_index = START_INDEX
    else:
        # Start at 6 minimum, even if lower numbers exist
        next_index = max(max(existing_dirs) + 1, START_INDEX)
        
    new_dir = os.path.join(BASE_DIR, f"{FOLDER_PREFIX}{next_index}")
    os.makedirs(new_dir, exist_ok=True)
    return new_dir

def parse_prompts(filepath):
    """Reads the prompts file, extracts instructions (if separated by 2 empty lines), and splits prompts."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # Split by two or more empty lines to separate instructions from prompts
    # Two empty lines means at least 3 newlines.
    parts = re.split(r'\n\s*\n\s*\n+', content, maxsplit=1)
    
    instructions = ""
    if len(parts) == 2:
        instructions = parts[0].strip()
        prompts_text = parts[1]
    else:
        prompts_text = parts[0]
        
    # Split prompts by one or more empty carriage returns/newlines
    raw_prompts = re.split(r'\n\s*\n', prompts_text)
    
    # Clean up whitespace and ignore empty elements
    prompts = [p.strip() for p in raw_prompts if p.strip()]
    return instructions, prompts

async def generate_images():
    output_dir = get_next_folder_path()
    print(f"Creating and saving images to: {output_dir}")
    
    # 1. Parse Prompts
    if not os.path.exists(PROMPTS_FILE):
        print(f"Error: {PROMPTS_FILE} not found. Creating a template...")
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            f.write("Cinematic lighting, 8k resolution, highly detailed\n\n\n")
            f.write("A sunset over the mountains, highly detailed\n\n")
            f.write("A cyberpunk city at night, neon lights\n\n")
        print(f"Please add your prompts to {PROMPTS_FILE} and run again.")
        return
        
    instructions, prompts = parse_prompts(PROMPTS_FILE)
    if not prompts:
        print("No prompts found in the file.")
        return
        
    print(f"Found {len(prompts)} prompts to process with instructions length {len(instructions)}.")

    # 2. Browser Automation
    async with async_playwright() as p:
        # We use persistent context to store your google login cookies. 
        # This prevents having to log in manually every time.
        user_data_dir = os.path.join(os.getcwd(), "chrome_session")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # Must be False to see and interact if captcha happens
            channel="chrome", # Ensure we use the local chrome install
            viewport={'width': 1280, 'height': 720},
            args=['--disable-blink-features=AutomationControlled'],
            ignore_default_args=['--enable-automation']
        )
        page = await browser.new_page()
        
        # Navigate to the site
        await page.goto("https://flow.google.com")
        print("\n--- ATTENTION ---")
        print("If you are not logged in, please log in now.")
        print("Waiting 15 seconds to let the page load/login...\n")
        await page.wait_for_timeout(15000)
        
        print("Checking for '+ New project' button...")
        try:
            new_project_btn = page.get_by_text("New project", exact=False).first
            if await new_project_btn.is_visible():
                await new_project_btn.click(force=True, timeout=5000)
                print("Clicked 'New project'. Waiting 5 seconds for workspace to load...")
                await page.wait_for_timeout(5000)
            else:
                print("No 'New project' button visible. Assuming we are already in a workspace.")
        except Exception as e:
            print(f"Could not click 'New project': {e}")
        
        if instructions:
            print("Entering global instructions into the instruction tab...")
            try:
                svg_btns = page.locator('button, [role="button"]')
                count = await svg_btns.count()
                
                inst_btn = None
                for i in range(count):
                    try:
                        btn = svg_btns.nth(i)
                        if not await btn.is_visible(): continue
                        lbl = (await btn.get_attribute('aria-label') or await btn.get_attribute('title') or await btn.get_attribute('data-tooltip') or "").lower()
                        if any(kw in lbl for kw in ["style", "reference", "advanced", "magic", "instruct", "document"]):
                            inst_btn = btn
                            print(f" -> Auto-detected Instruction button: '{lbl}'")
                            break
                    except: pass
                
                if not inst_btn:
                    print("Could not reliably identify Instruction button. Printing all visible buttons for debugging:")
                    for i in range(count):
                        try:
                            btn = svg_btns.nth(i)
                            if await btn.is_visible():
                                lbl = await btn.get_attribute('aria-label') or await btn.get_attribute('title') or ""
                                if lbl: print(f"  - {lbl}")
                        except: pass
                    inst_btn = svg_btns.nth(count - 3 if count >= 3 else 0)
                
                await inst_btn.click(timeout=5000)
                await page.wait_for_timeout(1500)
                
                # --- NEW UI LOGIC based on screenshot ---
                # Click + Add instruction if it exists
                add_inst_btn = page.get_by_text("Add instruction", exact=False).first
                if await add_inst_btn.is_visible():
                    await add_inst_btn.click(timeout=3000)
                    await page.wait_for_timeout(500)
                
                # Find the instruction text box in the panel
                inst_input = page.locator('textarea:visible, div[contenteditable="true"]:visible').first
                await inst_input.click(timeout=3000, force=True)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(instructions, delay=5)
                
                # Click Done to save and close the panel
                done_btn = page.get_by_text("Done", exact=True).first
                if await done_btn.is_visible():
                    await done_btn.click(timeout=3000, force=True)
                else:
                    await inst_btn.click(force=True) # Fallback close
                
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)
                print("Successfully entered global instructions.")
            except Exception as e:
                print(f"Failed to automate the instruction tab. Error: {e}")

        # Re-done prompt loop from scratch to maximize stability
        print("\n--- Starting Prompts ---")
        for index, prompt in enumerate(prompts):
            print(f"Processing Prompt {index+1}/{len(prompts)}: {prompt[:50]}...")

            if index == 0:
                print("Waiting 5 seconds for workspace to fully initialize before first prompt...")
                await page.wait_for_timeout(5000)

            # --- ENFORCE SETTINGS EVERY PROMPT ---
            # Google Flow has a bug where it resets to 2x images mid-session. We force 1x every loop!
            try:
                svg_btns = page.locator('button, [role="button"]')
                count = await svg_btns.count()
                settings_btn = None
                
                for i in range(count):
                    try:
                        btn = svg_btns.nth(i)
                        if not await btn.is_visible(): continue
                        lbl = (await btn.get_attribute('aria-label') or await btn.get_attribute('title') or "").lower()
                        if any(kw in lbl for kw in ["setting", "option", "slider", "config"]):
                            settings_btn = btn
                            break
                    except: pass
                    
                if not settings_btn:
                    print("Could not find the settings button. Skipping enforcement to avoid clicking wrong elements.")
                else:
                    await settings_btn.click(timeout=3000, force=True)
                    await page.wait_for_timeout(1000)
                
                try:
                    qty_btns = page.locator('button, [role="button"], [role="radio"], [role="option"]').filter(
                        has_text=re.compile(r"^\s*1x?\s*$|^\s*1 image\s*$", re.IGNORECASE)
                    )
                    if await qty_btns.count() > 0:
                        await qty_btns.last.click(timeout=1000, force=True)
                    else:
                        await page.get_by_text("1", exact=True).last.click(timeout=1000, force=True)
                except:
                    pass
                    
                await page.wait_for_timeout(500)
                await page.keyboard.press("Escape")
                await settings_btn.click(force=True)
                await page.wait_for_timeout(500)
            except:
                pass
            # -------------------------------------

            # 1. Locate the main chat input
            try:
                # Get the absolute last text area/contenteditable which is almost always the main chat bar
                prompt_input = page.locator('div[contenteditable="true"]:visible, textarea:visible, input[type="text"]:visible').last 
                await prompt_input.wait_for(state="visible", timeout=10000)
                
                # Clear active overlays
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(200)
                
                # Use .fill() for robust text injection, and trigger React with a final spacebar
                await prompt_input.click(force=True, click_count=3)
                await page.keyboard.press("Backspace")
                await prompt_input.fill(prompt)
                await prompt_input.click(force=True)
                await page.keyboard.press("Space")
                await page.wait_for_timeout(300)
            except Exception as e:
                print(f"Failed to enter text into prompt box! Error: {e}")
                continue
            
            # 2. Emulate pressing Enter to submit
            await page.keyboard.press("Enter")
            
            # 3. Wait for generation
            print("Checking if generation started...")
            started_generating = False
            for _ in range(15): # Max 7.5 seconds
                has_stop = await page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    return btns.some(b => (b.getAttribute('aria-label') || '').toLowerCase().includes('stop') ||
                                          (b.getAttribute('title') || '').toLowerCase().includes('stop'));
                }''')
                if has_stop:
                    started_generating = True
                    break
                await page.wait_for_timeout(500)
                
            if started_generating:
                print("Generating... Waiting for completion...")
                for _ in range(120): # Max 60 seconds
                    still_generating = await page.evaluate('''() => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        return btns.some(b => (b.getAttribute('aria-label') || '').toLowerCase().includes('stop') ||
                                              (b.getAttribute('title') || '').toLowerCase().includes('stop'));
                    }''')
                    if not still_generating:
                        print("Generation finished visually! Waiting 3 seconds for images to settle...")
                        await page.wait_for_timeout(3000)
                        break
                    await page.wait_for_timeout(500)
            else:
                print("WARNING: Could not verify if it started generating! Executing a blind 25-second wait just to be safe!")
                await page.wait_for_timeout(25000)
            
            # 4. Filter and download real images
            images = await page.locator('img').all()
            
            valid_images = []
            for img in images[-15:]: # Inspect trailing images
                try:
                    w = await img.evaluate('el => el.naturalWidth')
                    if w and int(w) > 150:
                        valid_images.append(img)
                except:
                    pass
                
            img_count = 1
            for img in valid_images[-2:]: # Grab the user's latest images
                src = await img.get_attribute('src')
                if src and (src.startswith('http') or src.startswith('data:image')):
                    filename = os.path.join(output_dir, f"prompt_{index+1}_img_{img_count}.jpg")
                    try:
                        urllib.request.urlretrieve(src, filename)
                        print(f"  -> Saved: {filename}")
                        img_count += 1
                    except Exception:
                        pass
                        
            await page.wait_for_timeout(2000)
            
        print(f"Finished processing! All saved in {output_dir}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(generate_images())
