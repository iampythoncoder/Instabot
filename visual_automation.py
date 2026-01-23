"""
Visual Automation with OpenCV (SikuliX-Style)
==============================================
This script uses computer vision to:
1. Take screenshots of the screen
2. Find UI elements (like chat boxes) using template matching
3. Click on them using their visual appearance

Requirements:
    pip install opencv-python pyautogui pillow numpy mss

Usage:
    1. First, capture a reference image of the element you want to find
       (e.g., the chat box icon) and save it in the 'templates/' folder
    2. Run the script to locate and interact with that element
"""

import cv2
import numpy as np
import pyautogui
import mss
import time
import os
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Disable pyautogui fail-safe (move mouse to corner to abort)
# pyautogui.FAILSAFE = True  # Keep enabled for safety

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Directory to store template images (screenshots of UI elements to find)
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Confidence threshold for template matching (0.0 to 1.0)
# Higher = more strict matching, Lower = more lenient
DEFAULT_CONFIDENCE = 0.8

# Screenshot region (None = full screen, or (x, y, width, height))
SCREENSHOT_REGION = None

# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class Match:
    """Represents a found element on screen."""
    x: int           # Center X coordinate
    y: int           # Center Y coordinate
    width: int       # Width of matched region
    height: int      # Height of matched region
    confidence: float  # Match confidence (0.0 to 1.0)
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    @property
    def top_left(self) -> Tuple[int, int]:
        return (self.x - self.width // 2, self.y - self.height // 2)
    
    @property
    def bottom_right(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


# ==============================================================================
# SCREEN CAPTURE
# ==============================================================================

def capture_screen(region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
    """
    Capture the screen (or a region) and return as OpenCV image (BGR format).
    
    Args:
        region: Optional (x, y, width, height) tuple to capture specific area
    
    Returns:
        Screenshot as numpy array in BGR format
    """
    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3]
            }
        else:
            # Capture primary monitor
            monitor = sct.monitors[1]  # [0] is all monitors combined
        
        # Capture screenshot
        screenshot = sct.grab(monitor)
        
        # Convert to numpy array (BGRA format from mss)
        img = np.array(screenshot)
        
        # Convert BGRA to BGR (remove alpha channel)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        return img_bgr


def save_screenshot(filename: str, region: Optional[Tuple[int, int, int, int]] = None):
    """
    Save a screenshot to a file.
    
    Args:
        filename: Output filename (will be saved in templates directory)
        region: Optional region to capture
    """
    TEMPLATES_DIR.mkdir(exist_ok=True)
    screenshot = capture_screen(region)
    filepath = TEMPLATES_DIR / filename
    cv2.imwrite(str(filepath), screenshot)
    print(f"Screenshot saved to: {filepath}")
    return filepath


# ==============================================================================
# TEMPLATE MATCHING (FINDING ELEMENTS)
# ==============================================================================

def load_template(template_name: str) -> np.ndarray:
    """
    Load a template image from the templates directory.
    
    Args:
        template_name: Filename of the template (e.g., 'chat_icon.png')
    
    Returns:
        Template image as numpy array
    """
    template_path = TEMPLATES_DIR / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Please capture a reference image first using capture_template()"
        )
    
    template = cv2.imread(str(template_path))
    if template is None:
        raise ValueError(f"Could not load template image: {template_path}")
    
    return template


def find_on_screen(
    template: np.ndarray | str,
    confidence: float = DEFAULT_CONFIDENCE,
    grayscale: bool = True,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Optional[Match]:
    """
    Find a template image on the screen using OpenCV template matching.
    
    This is the core SikuliX-style function - it visually locates an element.
    
    Args:
        template: Template image (numpy array) or filename string
        confidence: Minimum confidence threshold (0.0 to 1.0)
        grayscale: Convert to grayscale before matching (faster, often more reliable)
        region: Optional screen region to search in
    
    Returns:
        Match object if found, None otherwise
    """
    # Load template if string provided
    if isinstance(template, str):
        template = load_template(template)
    
    # Capture current screen
    screenshot = capture_screen(region)
    
    # Convert to grayscale if requested
    if grayscale:
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        search_img = screenshot_gray
        template_img = template_gray
    else:
        search_img = screenshot
        template_img = template
    
    # Get template dimensions
    h, w = template_img.shape[:2]
    
    # Perform template matching
    result = cv2.matchTemplate(search_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    # Find the best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # Check if confidence threshold is met
    if max_val >= confidence:
        # Calculate center point
        top_left = max_loc
        center_x = top_left[0] + w // 2
        center_y = top_left[1] + h // 2
        
        # Adjust for region offset if specified
        if region:
            center_x += region[0]
            center_y += region[1]
        
        return Match(
            x=center_x,
            y=center_y,
            width=w,
            height=h,
            confidence=max_val
        )
    
    return None


def find_all_on_screen(
    template: np.ndarray | str,
    confidence: float = DEFAULT_CONFIDENCE,
    grayscale: bool = True,
    region: Optional[Tuple[int, int, int, int]] = None,
    max_matches: int = 50
) -> List[Match]:
    """
    Find ALL occurrences of a template on screen.
    
    Args:
        template: Template image or filename
        confidence: Minimum confidence threshold
        grayscale: Use grayscale matching
        region: Screen region to search
        max_matches: Maximum number of matches to return
    
    Returns:
        List of Match objects
    """
    if isinstance(template, str):
        template = load_template(template)
    
    screenshot = capture_screen(region)
    
    if grayscale:
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        search_img = screenshot_gray
        template_img = template_gray
    else:
        search_img = screenshot
        template_img = template
    
    h, w = template_img.shape[:2]
    result = cv2.matchTemplate(search_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    # Find all locations above threshold
    locations = np.where(result >= confidence)
    
    matches = []
    for pt in zip(*locations[::-1]):  # Switch columns and rows
        center_x = pt[0] + w // 2
        center_y = pt[1] + h // 2
        
        if region:
            center_x += region[0]
            center_y += region[1]
        
        conf = result[pt[1], pt[0]]
        matches.append(Match(x=center_x, y=center_y, width=w, height=h, confidence=conf))
    
    # Remove overlapping matches (keep highest confidence)
    matches = _remove_duplicates(matches, w, h)
    
    return matches[:max_matches]


def _remove_duplicates(matches: List[Match], width: int, height: int) -> List[Match]:
    """Remove overlapping matches, keeping highest confidence."""
    if not matches:
        return []
    
    # Sort by confidence (highest first)
    matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
    
    filtered = []
    for match in matches:
        # Check if this match overlaps with any already-kept match
        is_duplicate = False
        for kept in filtered:
            if (abs(match.x - kept.x) < width // 2 and 
                abs(match.y - kept.y) < height // 2):
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered.append(match)
    
    return filtered


def wait_for(
    template: np.ndarray | str,
    timeout: float = 10.0,
    confidence: float = DEFAULT_CONFIDENCE,
    poll_interval: float = 0.5
) -> Optional[Match]:
    """
    Wait for an element to appear on screen.
    
    Args:
        template: Template to look for
        timeout: Maximum seconds to wait
        confidence: Match confidence threshold
        poll_interval: Seconds between screen checks
    
    Returns:
        Match if found within timeout, None otherwise
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        match = find_on_screen(template, confidence=confidence)
        if match:
            return match
        time.sleep(poll_interval)
    
    return None


# ==============================================================================
# ACTIONS (CLICKING, TYPING, ETC.)
# ==============================================================================

def click(match: Match, button: str = 'left', clicks: int = 1):
    """
    Click on a matched element.
    
    Args:
        match: Match object from find_on_screen()
        button: 'left', 'right', or 'middle'
        clicks: Number of clicks
    """
    pyautogui.click(match.x, match.y, button=button, clicks=clicks)
    print(f"Clicked at ({match.x}, {match.y})")


def click_image(
    template: np.ndarray | str,
    confidence: float = DEFAULT_CONFIDENCE,
    button: str = 'left',
    clicks: int = 1,
    wait_timeout: float = 5.0
) -> bool:
    """
    Find and click on an image (combines find + click).
    
    Args:
        template: Template to find and click
        confidence: Match confidence
        button: Mouse button
        clicks: Number of clicks
        wait_timeout: How long to wait for element to appear
    
    Returns:
        True if found and clicked, False otherwise
    """
    match = wait_for(template, timeout=wait_timeout, confidence=confidence)
    
    if match:
        click(match, button=button, clicks=clicks)
        return True
    else:
        print(f"Could not find element on screen")
        return False


def double_click(match: Match):
    """Double-click on a matched element."""
    click(match, clicks=2)


def right_click(match: Match):
    """Right-click on a matched element."""
    click(match, button='right')


def type_text(text: str, interval: float = 0.05):
    """
    Type text at the current cursor position.
    
    Args:
        text: Text to type
        interval: Seconds between keystrokes
    """
    pyautogui.write(text, interval=interval)


def press_key(key: str):
    """Press a single key (e.g., 'enter', 'tab', 'escape')."""
    pyautogui.press(key)


def hotkey(*keys):
    """Press a key combination (e.g., hotkey('ctrl', 'v'))."""
    pyautogui.hotkey(*keys)


def move_to(match: Match, duration: float = 0.3):
    """Move mouse to a matched element."""
    pyautogui.moveTo(match.x, match.y, duration=duration)


# ==============================================================================
# TEMPLATE CAPTURE HELPER
# ==============================================================================

def capture_template(name: str, delay: float = 3.0):
    """
    Interactive helper to capture a template image.
    
    Gives you time to position the screen, then captures a region
    you select with your mouse.
    
    Args:
        name: Name for the template file (e.g., 'chat_icon.png')
        delay: Seconds to wait before capture starts
    """
    TEMPLATES_DIR.mkdir(exist_ok=True)
    
    print(f"\n{'='*60}")
    print("TEMPLATE CAPTURE MODE")
    print(f"{'='*60}")
    print(f"\nIn {delay} seconds, you'll select the region to capture.")
    print("Position your screen so the element is visible!")
    
    for i in range(int(delay), 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("\nMove mouse to TOP-LEFT corner and CLICK...")
    
    # Wait for click at top-left
    while not pyautogui.mouseDown():
        time.sleep(0.01)
    while pyautogui.mouseDown():
        time.sleep(0.01)
    
    top_left = pyautogui.position()
    print(f"  Top-left: {top_left}")
    
    print("Now move to BOTTOM-RIGHT corner and CLICK...")
    
    # Wait for click at bottom-right
    while not pyautogui.mouseDown():
        time.sleep(0.01)
    while pyautogui.mouseDown():
        time.sleep(0.01)
    
    bottom_right = pyautogui.position()
    print(f"  Bottom-right: {bottom_right}")
    
    # Calculate region
    x = min(top_left[0], bottom_right[0])
    y = min(top_left[1], bottom_right[1])
    w = abs(bottom_right[0] - top_left[0])
    h = abs(bottom_right[1] - top_left[1])
    
    if w < 5 or h < 5:
        print("ERROR: Selected region too small!")
        return None
    
    # Capture the region
    filepath = save_screenshot(name, region=(x, y, w, h))
    
    print(f"\n✓ Template saved: {filepath}")
    print(f"  Size: {w}x{h} pixels")
    print(f"\nYou can now use this template:")
    print(f'  match = find_on_screen("{name}")')
    
    return filepath


def capture_fullscreen_template(name: str, delay: float = 3.0):
    """
    Capture a full screenshot as a template.
    """
    TEMPLATES_DIR.mkdir(exist_ok=True)
    
    print(f"\nCapturing full screen in {delay} seconds...")
    print("Position your screen!")
    
    for i in range(int(delay), 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    filepath = save_screenshot(name)
    print(f"\n✓ Screenshot saved: {filepath}")
    return filepath


# ==============================================================================
# DEBUG / VISUALIZATION
# ==============================================================================

def debug_find(
    template: np.ndarray | str,
    confidence: float = DEFAULT_CONFIDENCE,
    output_file: str = "debug_result.png"
):
    """
    Debug template matching by saving an annotated screenshot.
    
    Shows where the template was found (or best match if not above threshold).
    """
    if isinstance(template, str):
        template_name = template
        template = load_template(template)
    else:
        template_name = "template"
    
    screenshot = capture_screen()
    h, w = template.shape[:2]
    
    # Find match
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # Draw rectangle on screenshot
    output = screenshot.copy()
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    
    # Green if above confidence, red if below
    color = (0, 255, 0) if max_val >= confidence else (0, 0, 255)
    cv2.rectangle(output, top_left, bottom_right, color, 3)
    
    # Add text with confidence
    text = f"{template_name}: {max_val:.2%}"
    cv2.putText(output, text, (top_left[0], top_left[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Save debug image
    output_path = TEMPLATES_DIR / output_file
    cv2.imwrite(str(output_path), output)
    print(f"Debug image saved: {output_path}")
    print(f"Match confidence: {max_val:.2%} (threshold: {confidence:.2%})")
    
    return max_val >= confidence


# ==============================================================================
# EXAMPLE USAGE FOR INSTAGRAM CHAT
# ==============================================================================

def demo_find_chat_box():
    """
    Example: Find and click on Instagram chat/messages icon.
    
    Steps to use:
    1. First, capture a template of the chat icon:
       capture_template("chat_icon.png")
    
    2. Then use this function to find and click it:
       demo_find_chat_box()
    """
    print("\n" + "=" * 60)
    print("VISUAL AUTOMATION DEMO: Find Chat Box")
    print("=" * 60)
    
    # Check if template exists
    chat_template = "chat_icon.png"
    template_path = TEMPLATES_DIR / chat_template
    
    if not template_path.exists():
        print(f"\n⚠️  Template not found: {template_path}")
        print("\nPlease capture a template first!")
        print("Run in Python:")
        print('  from visual_automation import capture_template')
        print('  capture_template("chat_icon.png")')
        return False
    
    # Try to find the chat icon
    print("\nSearching for chat icon on screen...")
    match = find_on_screen(chat_template, confidence=0.7)
    
    if match:
        print(f"\n✓ Found chat icon!")
        print(f"  Location: ({match.x}, {match.y})")
        print(f"  Confidence: {match.confidence:.2%}")
        
        # Move mouse to the location (visual confirmation)
        print("\nMoving mouse to chat icon...")
        move_to(match, duration=0.5)
        time.sleep(1)
        
        # Click it
        print("Clicking...")
        click(match)
        
        return True
    else:
        print("\n✗ Chat icon not found on screen.")
        print("  Try lowering confidence or recapturing the template.")
        print("\n  Debug with: debug_find('chat_icon.png')")
        return False


# ==============================================================================
# MAIN - INTERACTIVE MODE
# ==============================================================================

def main():
    """
    Interactive mode for testing visual automation.
    """
    print("\n" + "=" * 60)
    print("VISUAL AUTOMATION WITH OPENCV")
    print("SikuliX-Style Screen Automation")
    print("=" * 60)
    
    # Create templates directory
    TEMPLATES_DIR.mkdir(exist_ok=True)
    print(f"\nTemplates directory: {TEMPLATES_DIR}")
    
    # List existing templates
    templates = list(TEMPLATES_DIR.glob("*.png"))
    if templates:
        print(f"\nExisting templates:")
        for t in templates:
            print(f"  - {t.name}")
    
    print("\n" + "-" * 60)
    print("AVAILABLE COMMANDS (run in Python):")
    print("-" * 60)
    print("""
    # Capture a new template
    capture_template("chat_icon.png")
    
    # Find an element on screen
    match = find_on_screen("chat_icon.png")
    
    # Find and click an element
    click_image("chat_icon.png")
    
    # Wait for element to appear, then click
    match = wait_for("chat_icon.png", timeout=10)
    if match:
        click(match)
    
    # Debug matching (saves annotated screenshot)
    debug_find("chat_icon.png")
    
    # Type text
    type_text("Hello, world!")
    
    # Press keys
    press_key("enter")
    hotkey("ctrl", "v")
    """)
    
    print("-" * 60)
    print("\nTo test, run: demo_find_chat_box()")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

