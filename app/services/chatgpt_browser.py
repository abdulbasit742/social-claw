import os
import json
import logging
from loguru import logger
from playwright.async_api import async_playwright

# Project Root
project_root = r"C:\Users\absh5\MoneyPrinterTurbo"
CG_STORAGE = os.path.join(project_root, "storage", "chatgpt_session.json")
PROXY = "http://172.30.10.10:3128"

def _load_credentials():
    login_file = os.path.join(project_root, "tiktok_login.json")
    if os.path.exists(login_file):
        try:
            with open(login_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("email"), data.get("password")
        except Exception as e:
            logger.warning(f"[ChatGPT-Playwright] Failed to load credentials from file: {e}")
    return None, None

async def _take_screenshot(page, name):
    try:
        shot_dir = os.path.join(project_root, "storage", "screenshots")
        os.makedirs(shot_dir, exist_ok=True)
        path = os.path.join(shot_dir, f"cg_{name}.png")
        await page.screenshot(path=path)
        logger.info(f"[ChatGPT-Playwright] Captured screenshot: storage/screenshots/cg_{name}.png")
    except Exception as e:
        logger.warning(f"[ChatGPT-Playwright] Failed to capture screenshot: {e}")

async def ask_chatgpt(prompt: str) -> str:
    """
    Automates chatgpt.com via Playwright to answer the given prompt.
    """
    email, password = _load_credentials()
    if not email or not password:
        raise ValueError("[ChatGPT-Playwright] Credentials (email/password) missing.")

    logger.info("[ChatGPT-Playwright] Starting ChatGPT browser automation...")

    async with async_playwright() as p:
        # Launch browser headfully if login is needed, otherwise headless is fine.
        # But to be robust and bypass Cloudflare, headful is often safer, or headless with a good user agent.
        # Let's try headless first with user-agent, and if login is needed we start headful.
        headless_mode = True
        if not os.path.exists(CG_STORAGE):
            headless_mode = False  # Start headful for the first login run

        browser = await p.chromium.launch(
            headless=headless_mode,
            proxy={"server": PROXY},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )

        ctx_kwargs = {}
        if os.path.exists(CG_STORAGE):
            ctx_kwargs["storage_state"] = CG_STORAGE
            logger.info("[ChatGPT-Playwright] Loaded persistent storage state (cookies + localStorage)")

        # Emulate standard chrome user agent to avoid Cloudflare blocks
        ctx_kwargs["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        ctx = await browser.new_context(**ctx_kwargs)
        page = await ctx.new_page()

        # Set default timeout
        page.set_default_timeout(30000)

        logger.info("[ChatGPT-Playwright] Navigating to ChatGPT...")
        try:
            await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            logger.warning(f"[ChatGPT-Playwright] Navigation error: {e}. Retrying...")
            await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

        # Wait for Cloudflare/Page load elements to settle
        logger.info("[ChatGPT-Playwright] Waiting for page to load (handling Cloudflare)...")
        try:
            await page.wait_for_selector(
                'button:has-text("Log in"), [data-testid="login-button"], textarea[id="prompt-textarea"], button:has-text("Sign up")',
                timeout=60000
            )
            logger.info("[ChatGPT-Playwright] Page elements loaded.")
        except Exception as e:
            logger.warning(f"[ChatGPT-Playwright] Page load wait timed out: {e}. Proceeding hoping Cloudflare is cleared...")

        # Check if we are logged in
        async def _is_logged_in():
            try:
                textareas = await page.query_selector_all('#prompt-textarea, [id="prompt-textarea"], [placeholder*="Ask anything"], div[contenteditable="true"]')
                for textarea in textareas:
                    if await textarea.is_visible():
                        return True
            except Exception:
                pass
            return False

        is_logged_in = await _is_logged_in()

        if not is_logged_in:
            logger.warning("[ChatGPT-Playwright] Session expired or not logged in. Starting login flow...")
            
            # If we were in headless mode, restart headfully so user can see it
            if headless_mode:
                logger.info("[ChatGPT-Playwright] Restarting browser in HEADFUL mode for manual authentication...")
                await browser.close()
                browser = await p.chromium.launch(
                    headless=False,
                    proxy={"server": PROXY},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"]
                )
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await ctx.new_page()
                page.set_default_timeout(30000)

            logger.info("[ChatGPT-Playwright] Navigating directly to ChatGPT login route...")
            await page.goto("https://chatgpt.com/auth/login", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # Look for email input field
            try:
                email_input = await page.wait_for_selector(
                    'input[type="email"], input[name="username"], input#username',
                    state="visible",
                    timeout=8000
                )
                if email_input:
                    logger.info(f"[ChatGPT-Playwright] Filling email: {email}...")
                    await email_input.fill(email)
                    await page.wait_for_timeout(1000)
                    
                    # Click Continue
                    continue_btn = await page.query_selector('button[type="submit"], button[name="action"][value="default"]')
                    if continue_btn:
                        await continue_btn.click()
                        await page.wait_for_timeout(5000)
            except Exception as e:
                logger.warning(f"[ChatGPT-Playwright] Email input did not become visible: {e}")

            # Look for password input field
            try:
                pass_input = await page.wait_for_selector(
                    'input[type="password"], input[name="password"], input#password',
                    state="visible",
                    timeout=8000
                )
                if pass_input:
                    logger.info("[ChatGPT-Playwright] Filling password...")
                    await pass_input.fill(password)
                    await page.wait_for_timeout(1000)
                    
                    # Click Continue/Login
                    submit_btn = await page.query_selector('button[type="submit"], button[name="action"][value="default"]')
                    if submit_btn:
                        await submit_btn.click()
                        await page.wait_for_timeout(5000)
            except Exception as e:
                logger.warning(f"[ChatGPT-Playwright] Password input did not become visible: {e}")

            # Check if we are still not logged in (waiting for CAPTCHA/human verification)
            is_logged_in = await _is_logged_in()
            if not is_logged_in:
                logger.info("=====================================================================")
                logger.info("ACTION REQUIRED: Please verify / log in to ChatGPT in the browser window.")
                logger.info("Credentials have been auto-filled if stored successfully.")
                logger.info("We will wait up to 10 minutes (600s) for you to complete any CAPTCHA.")
                logger.info("=====================================================================")
                await _take_screenshot(page, "1_login_waiting")
                
                for poll in range(120):  # 120 * 5s = 600s
                    await page.wait_for_timeout(5000)
                    if poll % 3 == 0:
                        await _take_screenshot(page, f"login_waiting_{poll}")
                    
                    # Automate Google Sign-In if redirected
                    current_url = page.url
                    if poll % 3 == 0:
                        logger.info(f"[ChatGPT-Playwright] Polling... Current URL: {current_url}")
                        try:
                            elements = await page.evaluate("() => { return Array.from(document.querySelectorAll('*')).filter(el => (el.id && el.id.includes('prompt')) || (typeof el.className === 'string' && el.className.includes('textarea')) || el.placeholder || el.getAttribute('contenteditable')).map(el => ({ tag: el.tagName, id: el.id, cls: typeof el.className === 'string' ? el.className : '', placeholder: el.placeholder, contenteditable: el.getAttribute('contenteditable'), visible: el.offsetWidth > 0 })); }")
                            logger.info(f"[ChatGPT-Playwright] Matching inputs in DOM: {elements[:15]}")
                        except Exception as de:
                            logger.warning(f"Error querying inputs: {de}")
                    # Universal Login Solver
                    # Helper to find and fill first visible element
                    async def fill_visible(selector, text, name):
                        try:
                            elms = await page.query_selector_all(selector)
                            for el in elms:
                                if await el.is_visible():
                                    val = await el.input_value()
                                    if not val:
                                        logger.info(f"[ChatGPT-Playwright] Automatically filling {name}...")
                                        await el.fill(text)
                                        return True
                        except Exception as e:
                            logger.warning(f"Error checking/filling {name}: {e}")
                        return False

                    # Helper to find and click first visible element
                    async def click_visible(selector, name):
                        try:
                            elms = await page.query_selector_all(selector)
                            for el in elms:
                                if await el.is_visible():
                                    logger.info(f"[ChatGPT-Playwright] Clicking {name}...")
                                    await el.click()
                                    return True
                        except Exception as e:
                            logger.warning(f"Error checking/clicking {name}: {e}")
                        return False

                    # 1. Check for "Continue with password" option (common for OTP verification bypass)
                    await click_visible('button:has-text("Continue with password"), a:has-text("Continue with password")', "Continue with password button")

                    # 2. Try filling visible email/identifier field
                    filled_email = await fill_visible('input[type="email"], input[name="identifier"], input[name="username"]', email, "Email field")
                    if filled_email:
                        await page.wait_for_timeout(1000)
                        await click_visible('button[type="submit"], button:has-text("Next"), button:has-text("Continue"), #identifierNext', "Email Next button")
                        await page.wait_for_timeout(3000)

                    # 3. Try filling visible password field
                    filled_pass = await fill_visible('input[type="password"]', password, "Password field")
                    if filled_pass:
                        await page.wait_for_timeout(1000)
                        await click_visible('button[type="submit"], button:has-text("Next"), button:has-text("Continue"), #passwordNext', "Password Next button")
                        await page.wait_for_timeout(5000)

                    # 4. Check for Google "Try another way" challenge fallback
                    try:
                        await click_visible('div[role="link"]:has-text("Try another way"), button:has-text("Try another way"), :has-text("Try another way")', "Google 'Try another way' link")
                        await page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    
                    # 5. Check for Google "Get a verification code" email option
                    try:
                        await click_visible('div[role="link"]:has-text("Get a verification code"), :has-text("Get a verification code")', "Google 'Get a verification code' option")
                        await page.wait_for_timeout(2000)
                    except Exception:
                        pass

                    if "email-otp" not in current_url:
                        # 6. Check for OpenAI "Try another method" fallback option
                        try:
                            await click_visible('button:has-text("Try another method"), a:has-text("Try another method"), div[role="button"]:has-text("Try another method")', "OpenAI 'Try another method' option")
                            await page.wait_for_timeout(2000)
                        except Exception:
                            pass

                        # 7. Check for OpenAI "Email" or "Send code to email" option
                        try:
                            await click_visible('button:has-text("Email"), a:has-text("Email"), div[role="button"]:has-text("Email")', "OpenAI 'Email' verify option")
                            await page.wait_for_timeout(2000)
                        except Exception:
                            pass

                    # 8. Check for local OTP file to auto-fill
                    otp_file = os.path.join(r"C:\Users\absh5\MoneyPrinterTurbo\storage", "otp_code.txt")
                    if os.path.exists(otp_file):
                        try:
                            with open(otp_file, "r") as f:
                                code = f.read().strip()
                            if code:
                                logger.info(f"[ChatGPT-Playwright] Found OTP code in file: {code}. Attempting to fill...")
                                code_inp = await page.query_selector('input[type="text"], input[name="code"], input[placeholder*="code"]')
                                if code_inp:
                                    await code_inp.fill(code)
                                    await page.wait_for_timeout(1000)
                                    await click_visible('button[type="submit"], button:has-text("Continue"), button:has-text("Next")', "OTP Submit button")
                                    os.remove(otp_file)
                                    logger.info("[ChatGPT-Playwright] OTP code submitted and file removed.")
                                    await page.wait_for_timeout(5000)
                        except Exception as otpe:
                            logger.warning(f"Error processing OTP file: {otpe}")

                    is_logged_in = await _is_logged_in()
                    if is_logged_in:
                        logger.info("[ChatGPT-Playwright] Login success detected during wait!")
                        break
            
            if not is_logged_in:
                raise TimeoutError("[ChatGPT-Playwright] Failed to log in within the 10-minute wait limit.")

            # Save state upon login success
            logger.info("[ChatGPT-Playwright] Saving session state for future runs...")
            os.makedirs(os.path.dirname(CG_STORAGE), exist_ok=True)
            await ctx.storage_state(path=CG_STORAGE)

        # Now logged in, input the prompt
        logger.info("[ChatGPT-Playwright] Inputting prompt...")
        await _take_screenshot(page, "2_before_prompt")
        
        textarea = None
        for _ in range(30):
            textareas = await page.query_selector_all('#prompt-textarea, [id="prompt-textarea"], [placeholder*="Ask anything"], div[contenteditable="true"]')
            for ta in textareas:
                if await ta.is_visible():
                    textarea = ta
                    break
            if textarea:
                break
            await page.wait_for_timeout(1000)
            
        if not textarea:
            raise ValueError("[ChatGPT-Playwright] Prompt textarea not found or not visible")
        
        await textarea.click()
        await page.wait_for_timeout(500)
        try:
            await textarea.fill(prompt)
        except Exception:
            try:
                await textarea.type(prompt)
            except Exception:
                await page.evaluate("(el, val) => { el.innerText = val; el.dispatchEvent(new Event('input', { bubbles: true })); }", textarea, prompt)
        await page.wait_for_timeout(1000)

        # Send prompt
        send_btn = await page.query_selector('button[data-testid="send-button"], button[aria-label="Send prompt"]')
        if send_btn:
            logger.info("[ChatGPT-Playwright] Clicking Send button...")
            await send_btn.click()
        else:
            logger.info("[ChatGPT-Playwright] Pressing Enter to send prompt...")
            await textarea.press("Enter")

        # Wait for reply generation to finish
        logger.info("[ChatGPT-Playwright] Waiting for response generation...")
        await page.wait_for_timeout(5000)
        
        # Poll for completion: Send button is enabled and Stop generating button is absent
        for poll in range(90):  # 90 * 2s = 180s max
            await page.wait_for_timeout(2000)
            stop_btn = await page.query_selector('button[data-testid="stop-generating-button"]')
            send_btn = await page.query_selector('button[data-testid="send-button"]:not([disabled])')
            if not stop_btn and send_btn:
                logger.info("[ChatGPT-Playwright] Response generation finished.")
                break
        
        await _take_screenshot(page, "3_response_done")

        # Extract latest message content
        logger.info("[ChatGPT-Playwright] Extracting response text...")
        assistant_msgs = await page.query_selector_all('div[data-message-author-role="assistant"]')
        if not assistant_msgs:
            # Fallback selector just in case DOM changed
            assistant_msgs = await page.query_selector_all('div.agent-turn')

        if not assistant_msgs:
            raise ValueError("[ChatGPT-Playwright] No response message from assistant found on the page.")

        last_msg = assistant_msgs[-1]
        
        # Try to locate markdown container inside last message
        markdown_container = await last_msg.query_selector('.markdown')
        if markdown_container:
            response_text = await markdown_container.inner_text()
        else:
            response_text = await last_msg.inner_text()

        response_text = response_text.strip()
        logger.success(f"[ChatGPT-Playwright] Successfully retrieved response ({len(response_text)} chars)")
        
        # Update cookies storage state to keep it active
        await ctx.storage_state(path=CG_STORAGE)
        
        await browser.close()
        return response_text
