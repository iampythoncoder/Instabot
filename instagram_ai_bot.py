"""
Instagram AI Bot - Computer Vision Automation
==============================================
Uses OpenCV + OCR to find UI elements by their visible text.
No templates needed - analyzes the screen in real-time.

Components:
    - screen_analyzer.py: OCR and color detection
    - pyautogui: Mouse/keyboard control

Usage:
    python3 instagram_ai_bot.py

Requirements:
    pip3 install opencv-python numpy mss pytesseract pillow pyautogui pyobjc-core pyobjc-framework-Quartz
    brew install tesseract
"""

import pyautogui
import time
import random
import sys

from screen_analyzer import (
    capture_screen,
    find_text_on_screen,
    find_all_text_on_screen,
    find_blue_button,
    get_all_text_on_screen,
    debug_screenshot,
    Element
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

TARGET_USERNAME = "meganskiendiel"
MESSAGE_TEXT = "hello"

# Disable pyautogui failsafe (optional - move mouse to corner to abort)
# pyautogui.FAILSAFE = True

# ==============================================================================
# HELPERS
# ==============================================================================

def log(step: int, message: str):
    """Print formatted log message."""
    print(f"[Step {step}] {message}")

def human_delay(min_sec=0.8, max_sec=1.5):
    """Random human-like delay."""
    time.sleep(random.uniform(min_sec, max_sec))

def click_element(elem: Element):
    """Click on a detected element."""
    print(f"         → Clicking at ({elem.x}, {elem.y})")
    pyautogui.click(elem.x, elem.y)

def type_like_human(text: str):
    """Type text with human-like delays."""
    for char in text:
        pyautogui.write(char, interval=0)
        time.sleep(random.uniform(0.04, 0.12))

def wait_and_find(
    target_text: str,
    timeout: float = 10.0,
    poll_interval: float = 0.5
) -> Element | None:
    """Wait for text to appear on screen."""
    start = time.time()
    while time.time() - start < timeout:
        elem = find_text_on_screen(target_text)
        if elem:
            return elem
        time.sleep(poll_interval)
    return None

def countdown(seconds: int):
    """Countdown before starting."""
    print(f"\nStarting in {seconds} seconds...")
    print("→ Switch to your browser with Instagram open!")
    for i in range(seconds, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("  GO!\n")

# ==============================================================================
# AUTOMATION STEPS
# ==============================================================================

def step1_find_and_click_search() -> bool:
    """Find and click the Search element in the sidebar."""
    log(1, "Looking for 'Search' on screen...")
    
    # Take screenshot and look for "Search"
    screenshot = capture_screen()
    screen_width, _ = pyautogui.size()
    
    # Sidebar is on the left ~20% of screen
    sidebar_right_edge = int(screen_width * 0.25)
    
    # Find ALL text that matches "Search"
    all_search = find_all_text_on_screen("Search", screenshot)
    
    if all_search:
        # Filter to only elements in the sidebar (left side)
        sidebar_search = [e for e in all_search if e.x < sidebar_right_edge]
        
        if sidebar_search:
            elem = sidebar_search[0]
            log(1, f"Found 'Search' in sidebar at ({elem.x}, {elem.y})")
            click_element(elem)
            human_delay(1.5, 2.0)
            return True
        else:
            # Use any Search element found
            elem = all_search[0]
            log(1, f"Found '{elem.text}' at ({elem.x}, {elem.y})")
            click_element(elem)
            human_delay(1.5, 2.0)
            return True
    
    # Debug: show what text WAS found
    log(1, "Could not find 'Search'. Scanning all visible text...")
    all_text = get_all_text_on_screen(screenshot)
    visible = [e.text for e in all_text[:20]]  # First 20
    print(f"         Found: {visible}")
    
    # Save debug image
    debug_screenshot("debug_step1.png")
    log(1, "Saved debug_step1.png - check what's visible")
    
    return False


def step2_type_username(username: str) -> bool:
    """Type the username in the search field."""
    log(2, f"Typing username: {username}")
    
    # Wait for search field to be ready
    human_delay(1.0, 1.5)
    
    # Just type - search field should be focused
    type_like_human(username)
    
    log(2, "Waiting for search results...")
    human_delay(2.5, 3.5)
    
    return True


def step3_click_profile_result(username: str) -> bool:
    """Find and click on the profile in search results."""
    log(3, f"Looking for '{username}' in results...")
    
    screenshot = capture_screen()
    screen_width, screen_height = pyautogui.size()
    
    # Search results appear in a dropdown panel
    # Look for text containing part of the username
    all_text = get_all_text_on_screen(screenshot)
    
    # Find elements that contain any part of the username (case insensitive)
    username_lower = username.lower()
    matching = [e for e in all_text if username_lower in e.text.lower() or e.text.lower() in username_lower]
    
    if matching:
        # Get the one that's likely in the search results area (not too far left)
        # Search results panel is usually in center-left area
        results_area = [e for e in matching if e.x > screen_width * 0.1 and e.x < screen_width * 0.5]
        
        if results_area:
            elem = results_area[0]
            log(3, f"Found '{elem.text}' at ({elem.x}, {elem.y})")
            click_element(elem)
            human_delay(3.0, 4.0)
            return True
    
    # Fallback 1: Click below the search input where first result would be
    log(3, "Username not found by OCR, clicking on first result position...")
    
    # Search results typically appear below the search bar
    # Search panel is roughly 20-40% from left, results start ~15% from top
    result_x = int(screen_width * 0.25)
    result_y = int(screen_height * 0.20)
    
    log(3, f"Clicking first result area at ({result_x}, {result_y})")
    pyautogui.click(result_x, result_y)
    human_delay(1.0, 1.5)
    
    # Fallback 2: Also try keyboard navigation
    log(3, "Also trying keyboard navigation (down + enter)...")
    pyautogui.press("down")
    human_delay(0.3, 0.5)
    pyautogui.press("enter")
    human_delay(3.0, 4.0)
    return True


def step4_click_follow() -> bool:
    """Find and click the Follow button."""
    log(4, "Looking for 'Follow' button...")
    
    screenshot = capture_screen()
    
    # Method 1: Find by text "Follow"
    elem = find_text_on_screen("Follow", screenshot)
    
    if elem:
        log(4, f"Found 'Follow' at ({elem.x}, {elem.y})")
        click_element(elem)
        human_delay(1.5, 2.0)
        return True
    
    # Method 2: Find blue button (Instagram's Follow is blue)
    log(4, "Text not found, looking for blue button...")
    blue_elem = find_blue_button(screenshot)
    
    if blue_elem:
        log(4, f"Found blue button at ({blue_elem.x}, {blue_elem.y})")
        click_element(blue_elem)
        human_delay(1.5, 2.0)
        return True
    
    # Check if already following
    following = find_text_on_screen("Following", screenshot)
    if following:
        log(4, "Already following this account!")
        return True
    
    log(4, "Could not find Follow button")
    debug_screenshot("debug_step4.png")
    return False


def step5_click_message() -> bool:
    """Find and click the Message button (the one next to Follow, NOT sidebar)."""
    log(5, "Looking for 'Message' button (next to Follow)...")
    
    screenshot = capture_screen()
    screen_width, screen_height = pyautogui.size()
    
    # Calculate sidebar threshold relative to screen width
    # Sidebar is typically ~15-20% of screen width
    sidebar_threshold = int(screen_width * 0.20)
    
    # Find ALL occurrences of "Message" on screen
    all_message_elements = find_all_text_on_screen("Message", screenshot)
    
    # Also find Follow button to help identify the right Message button
    follow_elem = find_text_on_screen("Follow", screenshot)
    
    if all_message_elements:
        log(5, f"Found {len(all_message_elements)} 'Message' elements")
        
        # Filter out the sidebar one (left side of screen)
        profile_buttons = [e for e in all_message_elements if e.x > sidebar_threshold]
        
        if profile_buttons and follow_elem:
            # Best match: Find Message button on the same row as Follow (similar Y)
            # Allow ~50px tolerance for vertical alignment
            same_row = [e for e in profile_buttons if abs(e.y - follow_elem.y) < 50]
            if same_row:
                elem = same_row[0]
                log(5, f"Found Message on same row as Follow at ({elem.x}, {elem.y})")
                click_element(elem)
                human_delay(2.0, 3.0)
                return True
        
        if profile_buttons:
            # Pick the one highest on the page (smallest y = top of screen)
            elem = min(profile_buttons, key=lambda e: e.y)
            log(5, f"Clicking profile Message button at ({elem.x}, {elem.y})")
            click_element(elem)
            human_delay(2.0, 3.0)
            return True
    
    # Fallback: Click relative to Follow button position
    if follow_elem:
        # Message button is to the right of Follow
        # Use Follow button's width as reference for offset
        offset = max(follow_elem.width * 2, 80)  # At least 2x button width or 80px
        message_x = follow_elem.x + offset
        message_y = follow_elem.y
        log(5, f"Clicking relative to Follow: ({message_x}, {message_y})")
        pyautogui.click(message_x, message_y)
        human_delay(2.0, 3.0)
        return True
    
    log(5, "Could not find Message button")
    debug_screenshot("debug_step5.png")
    return False


def step6_send_message(message: str) -> bool:
    """Type and send the message."""
    log(6, f"Sending message: '{message}'")
    
    # Wait for chat to load
    human_delay(1.5, 2.0)
    
    # Look for message input area
    screenshot = capture_screen()
    
    # Try to find "Message..." placeholder text
    input_elem = find_text_on_screen("Message", screenshot)
    
    if input_elem:
        log(6, f"Found message input at ({input_elem.x}, {input_elem.y})")
        click_element(input_elem)
        human_delay(0.5, 0.8)
    else:
        # Click at bottom of screen where input usually is
        log(6, "Clicking at typical input location...")
        screen_w, screen_h = pyautogui.size()
        pyautogui.click(screen_w // 2, int(screen_h * 0.85))
        human_delay(0.5, 0.8)
    
    # Type the message
    log(6, "Typing message...")
    type_like_human(message)
    human_delay(0.3, 0.5)
    
    # Send with Enter
    log(6, "Pressing Enter to send...")
    pyautogui.press("enter")
    
    log(6, "✓ Message sent!")
    return True


# ==============================================================================
# MAIN
# ==============================================================================

def run_bot():
    """Main automation flow."""
    print("=" * 60)
    print("INSTAGRAM AI BOT - Computer Vision Automation")
    print("=" * 60)
    print(f"Target Account: @{TARGET_USERNAME}")
    print(f"Message: {MESSAGE_TEXT}")
    print("=" * 60)
    print("\nThis bot uses OCR to find UI elements by their text.")
    print("No pre-captured templates needed!\n")
    
    countdown(5)
    
    # Step 1: Click Search
    if not step1_find_and_click_search():
        print("\n⚠️ Could not find Search. Check debug_step1.png")
        print("Make sure Instagram is visible and not scrolled.")
        return False
    
    # Step 2: Type username
    step2_type_username(TARGET_USERNAME)
    
    # Step 3: Click on profile result
    step3_click_profile_result(TARGET_USERNAME)
    
    # Step 4: Click Follow
    step4_click_follow()
    
    # Step 5: Click Message
    if not step5_click_message():
        print("\n⚠️ Could not find Message button. Check debug_step5.png")
        return False
    
    # Step 6: Send message
    step6_send_message(MESSAGE_TEXT)
    
    print("\n" + "=" * 60)
    print("✓ AUTOMATION COMPLETE!")
    print("=" * 60)
    return True


def test_ocr():
    """Test OCR on current screen."""
    print("Testing OCR on current screen...")
    print("Capturing in 3 seconds - make Instagram visible!\n")
    time.sleep(3)
    
    debug_screenshot("test_ocr.png")
    print("\nCheck test_ocr.png to see what text was detected.")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_ocr()
    else:
        try:
            run_bot()
        except KeyboardInterrupt:
            print("\n\nAborted by user.")
        except Exception as e:
            print(f"\n\nError: {e}")
            import traceback
            traceback.print_exc()

