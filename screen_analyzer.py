"""
Screen Analyzer - OpenCV + OCR Component
=========================================
Analyzes screenshots to find UI elements by:
1. Text recognition (OCR) - finds buttons/labels by their text
2. Color detection - finds elements by color (e.g., blue Follow button)
3. Shape detection - finds input fields, buttons by shape

Requirements:
    pip3 install opencv-python numpy mss pytesseract pillow

    Also install Tesseract OCR:
    brew install tesseract
"""

import cv2
import numpy as np
import mss
from PIL import Image
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os

# Try to import pytesseract, provide helpful error if not installed
try:
    import pytesseract
except ImportError:
    print("ERROR: pytesseract not installed.")
    print("Run: pip3 install pytesseract")
    print("Also: brew install tesseract")
    raise

# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class Element:
    """Represents a found UI element on screen."""
    x: int              # Center X
    y: int              # Center Y
    width: int
    height: int
    text: str           # Text content (if OCR)
    confidence: float   # Detection confidence
    element_type: str   # "text", "button", "input", etc.
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Returns (left, top, right, bottom)."""
        return (
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.x + self.width // 2,
            self.y + self.height // 2
        )


# ==============================================================================
# SCREEN CAPTURE
# ==============================================================================

def capture_screen() -> np.ndarray:
    """Capture the entire screen and return as BGR numpy array."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        # Convert BGRA to BGR
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def capture_region(x: int, y: int, width: int, height: int) -> np.ndarray:
    """Capture a specific region of the screen."""
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": width, "height": height}
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


# ==============================================================================
# TEXT DETECTION (OCR)
# ==============================================================================

def find_text_on_screen(
    target_text: str,
    screenshot: Optional[np.ndarray] = None,
    case_sensitive: bool = False
) -> Optional[Element]:
    """
    Find text on screen using OCR.
    
    Args:
        target_text: Text to search for (e.g., "Search", "Follow")
        screenshot: Optional pre-captured screenshot
        case_sensitive: Whether to match case exactly
    
    Returns:
        Element if found, None otherwise
    """
    if screenshot is None:
        screenshot = capture_screen()
    
    # Convert to RGB for pytesseract
    rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
    
    # Preprocess for better OCR (helps with dark mode)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    # Increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    
    # Try OCR on both original and preprocessed
    results = []
    for img in [rgb, gray]:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        results.append(data)
    
    search_text = target_text if case_sensitive else target_text.lower()
    
    # Search through both result sets
    for data in results:
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            compare_text = text if case_sensitive else text.lower()
            
            # EXACT match (or very close) - not partial
            if compare_text == search_text or search_text == compare_text:
                conf = int(data['conf'][i])
                if conf > 20:  # Lower threshold for dark mode
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    return Element(
                        x=x + w // 2,
                        y=y + h // 2,
                        width=w,
                        height=h,
                        text=text,
                        confidence=conf / 100.0,
                        element_type="text"
                    )
    
    return None


def find_all_text_on_screen(
    target_text: str,
    screenshot: Optional[np.ndarray] = None,
    case_sensitive: bool = False
) -> List[Element]:
    """Find all occurrences of text on screen."""
    if screenshot is None:
        screenshot = capture_screen()
    
    rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
    
    # Also try with contrast enhancement for dark mode
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    
    search_text = target_text if case_sensitive else target_text.lower()
    elements = []
    seen_positions = set()  # Avoid duplicates
    
    for img in [rgb, gray]:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            compare_text = text if case_sensitive else text.lower()
            
            # EXACT match only
            if compare_text == search_text:
                conf = int(data['conf'][i])
                if conf > 20:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # Avoid duplicates (same position)
                    pos_key = (x // 20, y // 20)  # Group nearby positions
                    if pos_key not in seen_positions:
                        seen_positions.add(pos_key)
                        elements.append(Element(
                            x=x + w // 2,
                            y=y + h // 2,
                            width=w,
                            height=h,
                            text=text,
                            confidence=conf / 100.0,
                            element_type="text"
                        ))
    
    return elements


def get_all_text_on_screen(screenshot: Optional[np.ndarray] = None) -> List[Element]:
    """Get ALL text elements found on screen (for debugging)."""
    if screenshot is None:
        screenshot = capture_screen()
    
    rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
    
    elements = []
    n_boxes = len(data['text'])
    
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if not text:
            continue
        
        conf = int(data['conf'][i])
        if conf > 50:
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            elements.append(Element(
                x=x + w // 2,
                y=y + h // 2,
                width=w,
                height=h,
                text=text,
                confidence=conf / 100.0,
                element_type="text"
            ))
    
    return elements


# ==============================================================================
# COLOR DETECTION
# ==============================================================================

def find_by_color(
    color_bgr: Tuple[int, int, int],
    tolerance: int = 30,
    min_area: int = 500,
    screenshot: Optional[np.ndarray] = None
) -> List[Element]:
    """
    Find elements by their color.
    
    Args:
        color_bgr: Target color in BGR format (e.g., (255, 0, 0) for blue)
        tolerance: Color matching tolerance (0-255)
        min_area: Minimum pixel area to consider
        screenshot: Optional pre-captured screenshot
    
    Returns:
        List of Element objects for colored regions found
    """
    if screenshot is None:
        screenshot = capture_screen()
    
    # Create color range
    lower = np.array([max(0, c - tolerance) for c in color_bgr])
    upper = np.array([min(255, c + tolerance) for c in color_bgr])
    
    # Create mask
    mask = cv2.inRange(screenshot, lower, upper)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    elements = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(contour)
            elements.append(Element(
                x=x + w // 2,
                y=y + h // 2,
                width=w,
                height=h,
                text="",
                confidence=1.0,
                element_type="color_region"
            ))
    
    return elements


def find_blue_button(screenshot: Optional[np.ndarray] = None) -> Optional[Element]:
    """
    Find Instagram's blue button (Follow, Message, etc.).
    Instagram blue is approximately RGB(0, 149, 246) / BGR(246, 149, 0)
    """
    # Instagram blue in BGR
    instagram_blue = (246, 149, 0)
    
    elements = find_by_color(instagram_blue, tolerance=40, min_area=1000, screenshot=screenshot)
    
    if elements:
        # Return the largest blue element (most likely the button)
        return max(elements, key=lambda e: e.width * e.height)
    
    return None


# ==============================================================================
# SHAPE DETECTION (INPUT FIELDS)
# ==============================================================================

def find_input_fields(screenshot: Optional[np.ndarray] = None) -> List[Element]:
    """
    Find input fields by detecting rectangular shapes with borders.
    """
    if screenshot is None:
        screenshot = capture_screen()
    
    # Convert to grayscale
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    elements = []
    for contour in contours:
        # Approximate contour to polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Look for rectangles (4 corners)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio (input fields are typically wide)
            aspect_ratio = w / h if h > 0 else 0
            
            if aspect_ratio > 3 and w > 100 and h > 20 and h < 60:
                elements.append(Element(
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h,
                    text="",
                    confidence=0.7,
                    element_type="input"
                ))
    
    return elements


# ==============================================================================
# DEBUGGING / VISUALIZATION
# ==============================================================================

def debug_screenshot(filename: str = "debug_screen.png"):
    """Save current screenshot with all detected text annotated."""
    screenshot = capture_screen()
    output = screenshot.copy()
    
    # Get all text
    elements = get_all_text_on_screen(screenshot)
    
    print(f"\nFound {len(elements)} text elements:")
    
    for elem in elements:
        # Draw rectangle
        left, top, right, bottom = elem.bounds
        cv2.rectangle(output, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Draw text label
        cv2.putText(output, elem.text, (left, top - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        print(f"  '{elem.text}' at ({elem.x}, {elem.y})")
    
    # Save
    cv2.imwrite(filename, output)
    print(f"\nSaved debug image: {filename}")
    
    return elements


def find_and_highlight(target_text: str, filename: str = "found_element.png"):
    """Find specific text and save highlighted screenshot."""
    screenshot = capture_screen()
    
    elem = find_text_on_screen(target_text, screenshot)
    
    if elem:
        output = screenshot.copy()
        left, top, right, bottom = elem.bounds
        cv2.rectangle(output, (left, top), (right, bottom), (0, 0, 255), 3)
        cv2.putText(output, f"FOUND: {elem.text}", (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imwrite(filename, output)
        print(f"Found '{target_text}' at ({elem.x}, {elem.y})")
        print(f"Saved: {filename}")
        return elem
    else:
        print(f"Could not find '{target_text}' on screen")
        return None


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == "__main__":
    print("Screen Analyzer - Testing OCR")
    print("=" * 50)
    print("\nCapturing screen and running OCR...")
    print("This will save a debug image with all detected text.\n")
    
    debug_screenshot("debug_screen.png")

