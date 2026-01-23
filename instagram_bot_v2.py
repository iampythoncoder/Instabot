import pyautogui
import time
import random
import cv2
import numpy as np
import mss
import subprocess
import pytesseract
import requests


# ==============================================================================
# CONFIG
# ==============================================================================

MODE = "inbox"

INBOX_URL = "https://www.instagram.com/direct/inbox/"

MISTRAL_ENDPOINT = "http://localhost:11434/api/generate"
MISTRAL_MODEL = "mistral"

MAX_THREADS = 20

COLD_DM_USERNAMES = [
    "kourtneykardash",
]

COLD_DM_MESSAGE = (
    "Hi! 👋 Just wanted to share something we've been building and see if it might be useful for you. "
    "If you're interested, I'd love to send a few more details or examples."
)


# ==============================================================================
# HELPERS
# ==============================================================================

def human_delay(min_s=0.5, max_s=1.0):
    time.sleep(random.uniform(min_s, max_s))


def type_human(text):
    for char in text:
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        else:
            pyautogui.write(char)
        time.sleep(random.uniform(0.02, 0.05))


def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        return screenshot, monitor["width"], monitor["height"]


# ==============================================================================
# FIND DM ICON - FIXED NAVIGATION
# ==============================================================================

def find_dm_icon_position():
    """
    Find the DM/messages icon position on Instagram sidebar.
    Returns (x, y) coordinates or None if not found.
    
    The DM icon is typically in the left sidebar area, but NOT at the very left edge.
    Instagram's DM icon is usually located at:
    - X position: ~60-100 pixels from left edge
    - Y position: ~200-400 pixels from top (depends on screen size)
    """
    screenshot, screen_w, screen_h = capture_screen()
    
    # Convert to grayscale for processing
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    
    # DM icon area in sidebar - NOT at x=0, but in the middle-left
    # Sidebar is typically first 15-20% of screen width
    sidebar_width = int(screen_w * 0.20)
    
    # Look for common DM icon indicators:
    # 1. The "Message" text label
    # 2. The paper airplane / send icon shape
    # 3. Blue color typical of Instagram's interactive elements
    
    # Method 1: Look for "Message" text using OCR
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    
    dm_positions = []
    for i, text in enumerate(data['text']):
        text_lower = text.lower().strip()
        conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
        
        # Look for "Message" or similar keywords
        if conf > 30 and ('message' in text_lower or 'messages' in text_lower or 'dm' == text_lower):
            x = data['left'][i] + data['width'][i] // 2
            y = data['top'][i] + data['height'][i] // 2
            
            # Only consider positions in sidebar area
            if x < sidebar_width:
                dm_positions.append((x, y, conf, text))
    
    if dm_positions:
        # Return the highest confidence match in sidebar
        best = max(dm_positions, key=lambda p: p[2])
        print(f"  Found DM label '{best[3]}' at ({best[0]}, {best[1]}) conf={best[2]:.1f}")
        return (best[0], best[1])
    
    # Method 2: Look for blue elements in sidebar (DM icon is often highlighted)
    # Instagram blue is approximately RGB(0, 149, 246)
    instagram_blue_lower = np.array([0, 100, 180])  # BGR lower bound
    instagram_blue_upper = np.array([50, 180, 255])  # BGR upper bound
    
    # Mask for blue colors
    mask = cv2.inRange(screenshot, instagram_blue_lower, instagram_blue_upper)
    
    # Find contours in sidebar region
    sidebar_roi = mask[:, :sidebar_width]
    contours, _ = cv2.findContours(sidebar_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    blue_elements = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 100:  # Minimum size
            x, y, w, h = cv2.boundingRect(contour)
            # DM icon region - typically y between 100-400
            if 50 < y < 500:
                blue_elements.append((x + w//2, y + h//2, area))
    
    if blue_elements:
        # Return the element most likely to be DM icon (smaller, higher up)
        best = min(blue_elements, key=lambda p: (p[2], -p[1]))
        print(f"  Found blue element at ({best[0]}, {best[1]})")
        return (best[0], best[1])
    
    # Method 3: Fallback to known position based on screen size
    # This is approximate but works as last resort
    fallback_x = int(screen_w * 0.05)  # ~5% from left
    fallback_y = int(screen_h * 0.18)  # ~18% from top
    
    # Adjust for typical sidebar layout
    # DM icon is usually around row 3-4 in sidebar icons
    icon_height = int(screen_h * 0.08)  # Approximate icon spacing
    fallback_y = int(screen_h * 0.10) + (icon_height * 3)  # After home, search, explore
    
    print(f"  Using fallback DM position ({fallback_x}, {fallback_y})")
    return (fallback_x, fallback_y)


def click_dm_icon():
    """
    Navigate to Instagram DMs by clicking the DM icon.
    """
    print("Finding DM icon position...")
    
    pos = find_dm_icon_position()
    
    if pos:
        x, y = pos
        print(f"Clicking DM icon at ({x}, {y})")
        pyautogui.click(x, y)
        human_delay(1.5, 2.5)
        return True
    else:
        print("Could not find DM icon")
        return False


def navigate_to_dms():
    """
    Navigate to Instagram Direct Messages.
    """
    print("Navigating to DMs...")
    
    # Open Instagram inbox
    subprocess.run(["open", INBOX_URL])
    human_delay(5.0, 7.0)  # Wait for page to load
    
    # Click DM icon to ensure we're in the right place
    click_dm_icon()
    human_delay(2.0, 3.0)
    
    # Verify we're in DMs by checking for conversation list
    screenshot, screen_w, screen_h = capture_screen()
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    
    # Look for DM-related text
    for i, text in enumerate(data['text']):
        if text.lower() in ['inbox', 'message', 'sent', 'requests']:
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
            if conf > 40:
                print(f"  Confirmed DM view - found '{text}'")
                return True
    
    print("  DM view not confirmed, proceeding anyway...")
    return True


# ==============================================================================
# CLICK DM CONVERSATIONS - FIXED
# ==============================================================================

def click_all_dm_conversations():
    """
    Click on each DM conversation in the chat view (NOT sidebar).
    This opens conversations in the main chat area.
    """
    screenshot, screen_w, screen_h = capture_screen()
    
    # Chat view region - conversations are in the left panel when in DMs
    # Not at x=0, but in the main content area
    left = int(screen_w * 0.0)
    right = int(screen_w * 0.35)
    top = int(screen_h * 0.10)
    bottom = int(screen_h * 0.95)
    
    # Calculate click positions for each conversation
    # Instagram DM conversations are listed vertically
    num_conversations = 8
    height = bottom - top
    step = height // num_conversations
    
    positions = []
    for i in range(num_conversations):
        # Use middle of conversation item width, not left edge
        x = left + int(screen_w * 0.12)  # ~12% from left (conversation list area)
        y = top + (step * i) + (step // 2)
        positions.append((x, y))
    
    return positions


# ==============================================================================
# SEND MESSAGE - FIXED
# ==============================================================================

def send_reply(message):
    screenshot, screen_w, screen_h = capture_screen()
    
    # Message input field is typically at bottom of chat
    # On Instagram DM: input is around 50-90% from left, 85-95% from top
    input_y = int(screen_h * 0.90)
    input_x = int(screen_w * 0.35)  # Start of chat area
    
    # Try to find the input field more precisely
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    
    input_found = False
    for i, text in enumerate(data['text']):
        text_lower = text.lower().strip()
        conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0
        
        # Look for message input placeholder
        if conf > 40 and ('message' in text_lower or 'send' == text_lower):
            x = data['left'][i] + data['width'][i] // 2
            y = data['top'][i] + data['height'][i] // 2
            
            # Use this position if it's in the lower portion of screen
            if y > screen_h * 0.7:
                print(f"  Found message input at ({x}, {y})")
                pyautogui.click(x, y)
                input_found = True
                break
    
    if not input_found:
        # Fallback to approximate position
        print(f"  Using fallback input position ({input_x}, {input_y})")
        pyautogui.click(input_x, input_y)
    
    human_delay(0.3, 0.5)
    
    type_human(message)
    human_delay(0.2, 0.4)
    pyautogui.press("enter")


# ==============================================================================
# AI REPLY - FIXED
# ==============================================================================

def get_ai_reply(message_text):
    if not message_text or not message_text.strip():
        return None  # Don't reply to empty messages

    # Check for gibberish or invalid content
    cleaned = clean_message_text(message_text)
    if not is_valid_message(cleaned):
        print(f"  Skipping invalid message: '{message_text[:50]}...'")
        return None

    prompt = (
        "You are a friendly Instagram DM assistant. Reply briefly, naturally, and under 5 sentences.\n\n"
        f"User said: {cleaned}\n\n"
        "Your reply:"
    )

    try:
        resp = requests.post(
            MISTRAL_ENDPOINT,
            json={"model": MISTRAL_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        resp.raise_for_status()
        reply = resp.json().get("response", "").strip()
        
        if reply and len(reply) > 2:
            return reply
        else:
            return "Thanks for reaching out! 👍"
    except Exception as e:
        print(f"  AI request failed: {e}")
        return "Thanks for your message!"


# ==============================================================================
# MESSAGE CLEANING - NEW
# ==============================================================================

def clean_message_text(text):
    """
    Clean extracted message text by removing UI elements and noise.
    """
    if not text:
        return ""
    
    # Remove common UI text that appears in OCR
    ui_noise = [
        'send', 'message', 'like', 'emoji', 'photo', 'video', 'gif', 'sticker',
        'heart', 'like', 'reply', 'forward', 'info', 'call', 'video call',
        'follow', 'following', 'followers', 'profile', 'settings', 'search',
        'home', 'explore', 'notifications', 'likes', 'comments', 'share',
        'more', 'options', 'cancel', 'done', 'save', 'delete', 'archive'
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove short lines that are likely UI elements
        line = line.strip()
        if len(line) < 2:
            continue
        
        # Remove lines that are just UI keywords
        if line.lower() in ui_noise:
            continue
        
        # Remove very long lines (likely multiple messages or noise)
        if len(line) > 500:
            continue
        
        # Check if line contains mostly symbols or gibberish
        alpha_count = sum(c.isalnum() for c in line)
        symbol_count = len(line) - alpha_count
        
        # If more than 50% symbols, skip
        if symbol_count > len(line) * 0.5:
            continue
        
        cleaned_lines.append(line)
    
    return ' '.join(cleaned_lines)


def is_valid_message(text):
    """
    Check if the extracted text is a valid message worth replying to.
    """
    if not text or len(text) < 2:
        return False
    
    # Check for minimum meaningful content
    words = text.split()
    if len(words) < 1:
        return False
    
    # Check for excessive special characters
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if special_chars > len(text) * 0.6:  # More than 60% special chars
        return False
    
    # Check if it's all numbers (like timestamps or view counts)
    if text.replace(' ', '').replace('.', '').replace(',', '').isdigit():
        return False
    
    # Check for common non-message patterns
    non_message_patterns = ['@', '#', 'http', 'www', '.com']
    if any(text.lower().startswith(p) for p in non_message_patterns):
        # Allow @ mentions as they could be usernames
        pass
    
    return True


# ==============================================================================
# READ MESSAGE - IMPROVED OCR
# ==============================================================================

def read_message():
    """
    Read message from current DM conversation with improved OCR.
    Focuses on the actual chat message bubbles, not UI elements.
    """
    screenshot, screen_w, screen_h = capture_screen()

    # Chat message area - more precise region for actual messages
    # Messages appear in the center-right area when DMs are open
    # Top portion is for the other person's messages
    msg_top = int(screen_h * 0.15)
    msg_bottom = int(screen_h * 0.70)  # Stop before the input area
    msg_left = int(screen_w * 0.35)    # Start of chat area
    msg_right = int(screen_w * 0.95)   # End of chat area

    # Extract just the chat region
    msg_region = screenshot[msg_top:msg_bottom, msg_left:msg_right]
    
    if msg_region.size == 0:
        return ""
    
    # Convert to grayscale
    gray = cv2.cvtColor(msg_region, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply adaptive threshold for better text separation
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Also create inverted version
    inverted = 255 - thresh
    
    results = []
    
    # Approach 1: Original grayscale
    try:
        text1 = pytesseract.image_to_string(gray).strip()
        if text1 and len(text1) > 5:
            results.append(text1)
    except:
        pass
    
    # Approach 2: Adaptive threshold (good for varying backgrounds)
    try:
        text2 = pytesseract.image_to_string(thresh).strip()
        if text2 and len(text2) > 5:
            results.append(text2)
    except:
        pass
    
    # Approach 3: Inverted threshold
    try:
        text3 = pytesseract.image_to_string(inverted).strip()
        if text3 and len(text3) > 5:
            results.append(text3)
    except:
        pass
    
    # Select the best result
    if results:
        # Prioritize longer texts (actual messages) over short UI text
        best_text = max(results, key=lambda t: len(t))
        return best_text.strip()
    
    return ""


# ==============================================================================
# CHECK IF ALREADY REPLIED
# ==============================================================================

def is_conversation_replied():
    """
    Check if we already replied to this conversation.
    """
    screenshot, screen_w, screen_h = capture_screen()
    
    msg_top = int(screen_h * 0.18)
    msg_bottom = int(screen_h * 0.86)
    msg_left = int(screen_w * 0.33)
    msg_right = int(screen_w * 0.98)

    msg_region = screenshot[msg_top:msg_bottom, msg_left:msg_right]
    rgb = cv2.cvtColor(msg_region, cv2.COLOR_BGR2RGB)
    
    text = pytesseract.image_to_string(rgb).lower()
    
    # Simple check - if text contains common reply patterns
    return False  # Always reply for now


# ==============================================================================
# INBOX MODE - FIXED
# ==============================================================================

def run_inbox_mode():
    """
    Main inbox mode - navigates to DMs and replies to conversations.
    """
    # Navigate to DMs first
    navigate_to_dms()
    
    # Get all conversation positions
    positions = click_all_dm_conversations()
    
    replies_sent = 0
    
    for i, (cx, cy) in enumerate(positions[:MAX_THREADS]):
        print(f"\nChecking DM #{i+1} at ({cx}, {cy})")
        
        try:
            # Click on the conversation
            pyautogui.click(cx, cy)
            human_delay(2.0, 2.5)
            
            # Read the message
            msg = read_message()
            print(f"  Raw message: '{msg[:80]}...'")
            
            # Clean and validate the message
            cleaned_msg = clean_message_text(msg)
            print(f"  Cleaned: '{cleaned_msg[:80]}...'")
            
            if is_valid_message(cleaned_msg):
                print(f"  Valid message detected")
                reply = get_ai_reply(cleaned_msg)
                
                if reply:
                    send_reply(reply)
                    print(f"  Replied: '{reply[:50]}...'")
                    replies_sent += 1
                else:
                    print(f"  No reply generated")
            else:
                print(f"  No valid message content")
            
            human_delay(1.5, 2.5)
            
        except Exception as e:
            print(f"  Error processing conversation: {e}")
            continue
    
    print(f"\n✓ Done! Processed {len(positions[:MAX_THREADS])} conversations, sent {replies_sent} replies.")


# ==============================================================================
# COLD DM MODE
# ==============================================================================

def run_cold_dm_mode():
    for username in COLD_DM_USERNAMES:
        profile_url = f"https://www.instagram.com/{username}/"
        subprocess.run(["open", profile_url])
        human_delay(6.0, 8.0)

        screenshot, _, _ = capture_screen()
        
        rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
        
        for j in range(len(data["text"])):
            if "Message" in data["text"][j]:
                try:
                    conf = float(data["conf"][j])
                    if conf > 25:
                        x = data["left"][j]
                        y = data["top"][j]
                        w = data["width"][j]
                        h = data["height"][j]
                        pyautogui.click(x + w//2, y + h//2)
                        human_delay(2.0, 3.0)
                        send_reply(COLD_DM_MESSAGE)
                        break
                except:
                    pass

        human_delay(8.0, 12.0)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    try:
        if MODE == "inbox":
            run_inbox_mode()
        elif MODE == "cold":
            run_cold_dm_mode()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error: {e}")

