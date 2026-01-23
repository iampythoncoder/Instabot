"""
Instagram Follow Automation Script
===================================
This script uses Selenium to:
1. Auto-detect Chrome or Safari
2. Open Instagram (already logged in)
3. Search for specific users
4. Follow them if not already following

IMPORTANT: Safari shows "controlled by automated test" message.
USE CHROME INSTEAD for better results!

Requirements:
- pip install selenium webdriver-manager
- Chrome: Start with --remote-debugging-port=9222
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &

Usage:
    python3 follow_dhruva.py
    
The script auto-detects which browser is available and uses it automatically.
"""

import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Target accounts to follow
TARGET_USERNAMES = ["dhruva_valluru123", "saatviksantosh"]

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def random_delay(min_seconds=2, max_seconds=4):
    """
    Sleep for a random duration between min and max seconds.
    This makes the automation look more human-like.
    """
    delay = random.uniform(min_seconds, max_seconds)
    print(f"   (waiting {delay:.1f}s...)")
    time.sleep(delay)


def create_driver():
    """
    Create WebDriver - tries Chrome first, then Safari.
    Chrome launches automatically, Safari needs manual setup.
    """
    # Try Chrome (automatic launch)
    print("Attempting to connect to Chrome...")
    try:
        options = Options()
        # Don't add debuggerAddress - let Selenium launch Chrome normally
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        print("✓ Connected to Chrome successfully!")
        return driver, "Chrome"
    except Exception as e:
        print(f"Chrome not available: {str(e)[:100]}")
    
    # Fall back to Safari
    print("\nAttempting to connect to Safari...")
    try:
        driver = webdriver.Safari()
        driver.implicitly_wait(5)
        print("✓ Connected to Safari successfully!")
        return driver, "Safari"
    except Exception as e:
        print(f"Safari not available: {str(e)[:100]}")
        print("\nERROR: Could not connect to Chrome or Safari!")
        print("\nMake sure you're logged into Instagram in your browser.")
        return None, None


# ==============================================================================
# MAIN AUTOMATION STEPS
# ==============================================================================

def open_instagram(driver):
    """
    Step 1: Navigate to Instagram homepage and wait for login if needed.
    """
    print("\n[Step 1] Opening Instagram...")
    driver.get("https://www.instagram.com/")
    
    # Wait for page to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("   Instagram loaded.")
    except TimeoutException:
        print("   WARNING: Page took too long to load.")
    
    # Check if logged in - look for home feed or profile
    print("\n   Checking if you're logged in...")
    print("   If you see a login popup, please log in manually in the browser.")
    print("   Once logged in, the script will automatically continue...")
    
    logged_in = False
    for attempt in range(6):  # Wait up to 30 seconds for login
        try:
            # Look for elements that indicate you're logged in
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/')]"))
            )
            # Try to find search bar (only visible when logged in)
            driver.find_element(By.XPATH, "//*[@aria-label='Search']")
            logged_in = True
            print("   ✓ Logged in detected!")
            break
        except:
            if attempt < 5:
                print(f"   Not logged in yet... waiting ({(5-attempt)*5}s more)")
                time.sleep(5)
            else:
                print("   Login timeout - proceeding anyway")
    
    random_delay(2, 4)


def click_search_bar(driver):
    """
    Step 2: Find and click the Search bar/icon in the sidebar.
    Instagram has a search icon in the left sidebar.
    """
    print("\n[Step 2] Clicking Search bar...")
    
    try:
        # Try multiple selectors for different Instagram versions/browsers
        search_selectors = [
            # Most common - link with search aria-label
            "//a[.//*[@aria-label='Search']]",
            "//a[@aria-label='Search']",
            # Text-based search
            "//span[contains(text(), 'Search')]/ancestor::a",
            "//span[contains(text(), 'Search')]/ancestor::button",
            # Explore link as fallback
            "//a[contains(@href, '/explore/')]",
            # Direct aria-label element
            "//*[@aria-label='Search']",
            # Anchor with text
            "//a[contains(text(), 'Search')]",
        ]
        
        search_elem = None
        for i, selector in enumerate(search_selectors):
            try:
                search_elem = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"   Found search element (selector {i+1})")
                break
            except:
                continue
        
        if search_elem:
            # Scroll into view first
            driver.execute_script("arguments[0].scrollIntoView(true);", search_elem)
            random_delay(0.5, 1)
            search_elem.click()
            print("   Search bar clicked.")
            random_delay(1, 2)
            return True
        else:
            print("   Could not find Search element. Trying keyboard shortcut...")
            # Try keyboard shortcut - forward slash opens search on Instagram
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys("/")
                random_delay(1, 2)
                print("   Opened search with keyboard shortcut")
                return True
            except Exception as e:
                print(f"   Keyboard shortcut failed: {e}")
                return False
            
    except Exception as e:
        print(f"   Error clicking search: {e}")
        return False


def search_for_user(driver, username):
    """
    Step 3: Type the username into the search input field.
    """
    print(f"\n[Step 3] Searching for '{username}'...")
    
    try:
        # Find the search input field (appears after clicking search)
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search']"))
        )
        
        # Clear any existing text and type the username
        search_input.clear()
        
        # Type slowly like a human
        for char in username:
            search_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        print(f"   Typed '{username}' into search.")
        random_delay(2, 3)  # Wait for search results to appear
        return True
        
    except TimeoutException:
        print("   ERROR: Search input field not found.")
        return False
    except Exception as e:
        print(f"   Error typing in search: {e}")
        return False


def click_profile_result(driver, username):
    """
    Step 4: Click on the correct profile from search results.
    """
    print(f"\n[Step 4] Clicking on '{username}' in search results...")
    
    try:
        # Wait for search results to load
        # Look for a link that contains the username
        profile_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH, 
                f"//a[contains(@href, '/{username}/') or contains(@href, '/{username}')]"
            ))
        )
        
        profile_link.click()
        print(f"   Clicked on {username}'s profile.")
        random_delay(3, 5)  # Wait for profile page to load
        return True
        
    except TimeoutException:
        print(f"   ERROR: Could not find '{username}' in search results.")
        return False
    except Exception as e:
        print(f"   Error clicking profile: {e}")
        return False


def check_and_follow(driver):
    """
    Step 5: Check if already following, and click Follow if not.
    """
    print("\n[Step 5] Checking follow status...")
    
    try:
        # Wait for profile page to fully load - look for specific profile elements
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Follow') or contains(text(), 'Following')]"))
            )
            print("   Follow button loaded")
        except:
            print("   Waiting for button to appear...")
            random_delay(3, 5)
        
        # Scroll down a bit to make sure Follow button is visible
        driver.execute_script("window.scrollBy(0, 200);")
        random_delay(0.5, 1)
        
        # Find the Follow button using multiple selectors
        follow_selectors = [
            "//button[contains(text(), 'Follow')]",
            "//button[text()='Follow']",
            "//button[contains(@aria-label, 'Follow')]",
        ]
        
        following_selectors = [
            "//button[contains(text(), 'Following')]",
            "//button[text()='Following']",
            "//button[contains(text(), 'Requested')]",
        ]
        
        # Check if already following
        for selector in following_selectors:
            try:
                elem = driver.find_element(By.XPATH, selector)
                if elem:
                    print(f"   Status: Already following (found '{elem.text}')")
                    return "already_following"
            except:
                pass
        
        # Look for Follow button
        follow_button = None
        for selector in follow_selectors:
            try:
                follow_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if follow_button:
                    print(f"   Found Follow button: '{follow_button.text}'")
                    break
            except:
                pass
        
        if follow_button:
            print("   Clicking Follow button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", follow_button)
            random_delay(0.5, 1)
            follow_button.click()
            random_delay(2, 3)
            print("   ✓ Followed successfully!")
            return "followed"
        else:
            print("   WARNING: Follow button not found")
            # Show all button text for debugging
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"   {len(buttons)} buttons found:")
            for btn in buttons[:15]:
                txt = btn.text.strip()
                if txt:
                    print(f"      - '{txt}'")
            return "button_not_found"
            
    except Exception as e:
        print(f"   Error: {e}")
        return "error"


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """
    Main function that orchestrates all the automation steps.
    """
    print("=" * 60)
    print("INSTAGRAM FOLLOW AUTOMATION")
    print("=" * 60)
    print(f"Target accounts: {', '.join(TARGET_USERNAMES)}")
    print("=" * 60)
    
    driver = None
    browser_name = None
    
    try:
        # Initialize the browser (auto-detect)
        driver, browser_name = create_driver()
        
        if driver is None:
            print("\nScript ending due to browser connection failure.")
            return  # Error message already printed
        
        print(f"\nUsing: {browser_name}")
        print("\nStarting automation in 3 seconds...")
        time.sleep(3)
        
        # Step 1: Open Instagram
        open_instagram(driver)
        
        results = {}
        
        # Process each target username
        for idx, target_username in enumerate(TARGET_USERNAMES, 1):
            print(f"\n{'=' * 60}")
            print(f"[{idx}/{len(TARGET_USERNAMES)}] Processing: {target_username}")
            print(f"{'=' * 60}")
            
            try:
                # Step 2: Click the search bar
                if not click_search_bar(driver):
                    print("\nFailed to open search. Skipping this account.")
                    results[target_username] = "search_failed"
                    continue
                
                # Step 3: Type the username
                if not search_for_user(driver, target_username):
                    print("\nFailed to search. Skipping this account.")
                    results[target_username] = "search_failed"
                    continue
                
                # Step 4: Click the profile from results
                if not click_profile_result(driver, target_username):
                    print("\nFailed to find profile. Skipping this account.")
                    results[target_username] = "profile_not_found"
                    continue
                
                # Step 5: Check follow status and follow if needed
                result = check_and_follow(driver)
                results[target_username] = result
                
            except Exception as e:
                print(f"\nError processing {target_username}: {e}")
                results[target_username] = f"error: {str(e)[:30]}"
        
        # Final summary
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        for username, result in results.items():
            if result == "followed":
                print(f"✓ {username}: Successfully followed")
            elif result == "already_following":
                print(f"ℹ {username}: Already following")
            else:
                print(f"✗ {username}: {result}")
        print("=" * 60)
        
        # Keep browser open briefly so you can see the result
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always close the browser
        if driver:
            try:
                driver.quit()
                print("Browser closed.")
            except:
                pass


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()

