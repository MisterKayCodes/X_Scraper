import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth
from app.data.db_manager import is_duplicate

from typing import Callable, Awaitable

# Phase 2: Resource Guard (VPS Protection)
# Ensures only one browser instance runs at a time to prevent OOM on 1GB RAM.
browser_semaphore = asyncio.Semaphore(1)

async def scrape_profile_media(username: str, user_id: int, limit: int = 20, status_callback: Callable[[str], Awaitable[None]] = None, mode: str = "media"):
    """
    Scrapes an X profile for direct status links.
    mode="media"    -> Scans /media tab (UserMedia). Only direct uploads.
    mode="timeline" -> Scans main timeline (UserTweets). Includes quotes & retweets.
    Returns a list of unique status URLs.
    """
    if username.startswith("@"):
        username = username[1:]
    
    # Mode decides which URL and which GraphQL endpoint we intercept
    if mode == "timeline":
        url = f"https://x.com/{username}"
        graphql_key = "UserTweets"
    else:
        url = f"https://x.com/{username}/media"
        graphql_key = "UserMedia"

    links = []
    
    if status_callback: await status_callback("🚀 **STATUS:** Initializing Stealth Radar...")
    
    async with browser_semaphore:
        async with async_playwright() as p:
            # Rule: Isolated and Headless
            import os
            import json
            from pathlib import Path
            cookie_path = str(Path(__file__).resolve().parent.parent / "data" / "cookies.json")
            has_cookies = os.path.exists(cookie_path)
            print(f"[RADAR] Cookie path: {cookie_path} | Exists: {has_cookies}")
            
            if has_cookies:
                try:
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        cdata = json.load(f)
                    
                    cookies_list = cdata if isinstance(cdata, list) else cdata.get("cookies", [])
                    needs_save = False
                    
                    for c in cookies_list:
                        if "sameSite" in c:
                            ss = c["sameSite"].lower()
                            if ss in ["no_restriction", "none"]:
                                c["sameSite"] = "None"
                                needs_save = True
                            elif ss in ["lax"]:
                                c["sameSite"] = "Lax"
                                needs_save = True
                            elif ss in ["strict"]:
                                c["sameSite"] = "Strict"
                                needs_save = True
                            else:
                                del c["sameSite"]
                                needs_save = True
                                
                    if isinstance(cdata, list) or needs_save:
                        with open(cookie_path, 'w', encoding='utf-8') as f:
                            json.dump({"cookies": cookies_list, "origins": []}, f)
                except Exception:
                    pass

            if status_callback: await status_callback(f"🌐 **STATUS:** Opening Chromium (Cookies Loaded: {has_cookies})...")
            print("[RADAR] Launching Chromium...")
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )
                print("[RADAR] Browser launched successfully.")
            except Exception as launch_err:
                print(f"[🚨] Browser Launch Failed: {launch_err}")
                if status_callback: await status_callback(f"❌ **Radar Failure:** Browser launch error on VPS.")
                return []
            
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 720}
            }
            if has_cookies:
                context_args["storage_state"] = cookie_path
                
            context = await browser.new_context(**context_args)
            print("[RADAR] Context created with cookies.")
            
            page = await context.new_page()
            print("[RADAR] Page object created.")
            # Apply anti-bot stealth mask
            # Note: If stealth(page) fails, we'll try to find the right import in the test
            try:
                # We try to call stealth as a function first
                await stealth(page)
            except Exception:
                # Fallback to the sub-module function if detected previously
                try:
                    from playwright_stealth.stealth import stealth as stealth_func
                    await stealth_func(page)
                except Exception:
                    pass # Continue without stealth if absolutely necessary (not ideal)

            import re
            intercepted_tweet_ids = set()

            async def handle_response(response):
                if "/graphql/" in response.url and graphql_key in response.url:
                    try:
                        body = await response.text()
                        # 1. Look for rest_id which is the primary tweet ID in modern Twitter GraphQL
                        found = re.findall(r'"rest_id":"(\d+)"', body)
                        # 2. Fallback: conversation_id_str (older API responses)
                        found += re.findall(r'"conversation_id_str":"(\d+)"', body)
                        # 3. Fallback: hardcoded tweet URLs in payload
                        found += re.findall(r'https://(?:twitter|x)\.com/[^/]+/status/(\d+)', body)
                        
                        for tid in found:
                            # Tweet IDs are long numbers (>10 digits). Filter out user IDs which are shorter.
                            if tid.isdigit() and len(tid) > 10:
                                intercepted_tweet_ids.add(tid)
                        print(f"[RADAR-NET] Intercepted {graphql_key}! Found {len(found)} raw IDs. Unique tweets so far: {len(intercepted_tweet_ids)}")
                    except Exception as e:
                        print(f"[RADAR-NET] Error parsing payload: {e}")

            page.on("response", handle_response)

            print(f"[RADAR] Navigating to {url}...")
            if status_callback: await status_callback(f"🔍 **STATUS:** Navigating to profile... (Waiting for Interception)")
            try:
                # Drop networkidle, interceptor handles the real data
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # TEST 1: The Redirect Catch (The Bouncer Test)
                if "/login" in page.url or "/i/flow/" in page.url:
                    error_msg = "⚠️ Cookies expired or invalid. Diverted to Login."
                    print(f"[🚨] {error_msg}")
                    if status_callback: await status_callback(f"❌ **Radar Failure:** {error_msg}")
                    return []
                    
                # TEST 4: The Headless Stealth Handshake (X's 'Something went wrong' Canvas Fingerprint check)
                page_text = await page.content()
                if "Something went wrong. Try reloading" in page_text:
                    error_msg = "⚠️ Stealth Check Failed. X detected headless browser and blocked page."
                    print(f"[🚨] {error_msg}")
                    if status_callback: await status_callback(f"❌ **Radar Failure:** {error_msg}")
                    return []
                    
                # BYPASS: NSFW "Sensitive Content" Warning
                # Must wait a moment — the wall is rendered by JS AFTER domcontentloaded fires
                await asyncio.sleep(3)
                
                # ---- DIAGNOSTICS ----
                current_url = page.url
                page_snapshot = await page.content()
                print(f"[RADAR-DIAG] Landed URL: {current_url}")
                print(f"[RADAR-DIAG] Page has 'sensitive' mention: {'sensitive' in page_snapshot.lower()}")
                # ---------------------

                try:
                    # Try multiple button texts Twitter uses across regions
                    nsfw_clicked = False
                    for btn_text in ["Yes, view profile", "View", "Yes"]:
                        nsfw_btn = page.get_by_role("button", name=btn_text)
                        if await nsfw_btn.count() > 0:
                            print(f"[RADAR] NSFW wall detected! Clicking '{btn_text}' bypass...")
                            if status_callback: await status_callback("⚠️ **STATUS:** Bypassing NSFW wall...")
                            await nsfw_btn.first.click()
                            await asyncio.sleep(3)  # Wait for actual media page to load
                            nsfw_clicked = True
                            break
                    if not nsfw_clicked:
                        print("[RADAR] No NSFW wall found, proceeding normally.")
                except Exception as e:
                    print(f"[RADAR] NSFW bypass error: {e}")

                
                # Wiggle & Tease the lazy-loading ("Ghost Wall" bypass)
                for i in range(10):
                    if len(intercepted_tweet_ids) >= limit:
                        break
                        
                    if status_callback: await status_callback(f"🔄 **STATUS:** Teasing lazy-load (Wave {i+1}/10)... Found {len(intercepted_tweet_ids)} targets.")
                    
                    # Human wiggle
                    await page.mouse.move(random.randint(100, 700), random.randint(100, 700))
                    await asyncio.sleep(0.5)
                    await page.evaluate("window.scrollBy(0, 1200)")
                    await asyncio.sleep(random.uniform(2.5, 4.5))
                    
                # TEST 2: The Heartbeat Interception
                if not intercepted_tweet_ids:
                    error_msg = "⚠️ Ghost Wall active! 0 GraphQL payloads intercepted."
                    print(f"[🚨] {error_msg}")
                    if status_callback: await status_callback(f"❌ **Radar Failure:** {error_msg}")
                    return []
                    
                # Filter against DB limit
                for tid in intercepted_tweet_ids:
                    if not is_duplicate(tid, user_id):
                        links.append(f"https://x.com/{username}/status/{tid}")
                        if len(links) >= limit:
                            break
                    else:
                        print(f"[RADAR] Skipped duplicate DB entry: {tid}")

                    
            except Exception as e:
                print(f"[🚨] Radar Failure: {e}")
            finally:
                await browser.close()
            
    print(f"[RADAR] Successfully harvested {len(links)} unique targets from @{username}")
    return links[:limit]
