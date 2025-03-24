from playwright.sync_api import sync_playwright
import os
import sys
from dotenv import load_dotenv
import time
import traceback
import random

load_dotenv()

processed_profiles = set()  # Keep track of processed profile URLs

class BrowserContext:
    def __init__(self, page):
        self.page = page

    async def get_current_page(self):
        return self.page

class ElementTree:
    def __init__(self, page):
        self.page = page

    def get_clickable_elements(self):
        # Get all interactive elements
        elements = self.page.query_selector_all('button, input, a, [role="button"], [role="textbox"]')
        indexed_elements = []
        
        for idx, element in enumerate(elements, 1):
            # Get element properties using evaluate
            element_props = element.evaluate("""element => {
                return {
                    tagName: element.tagName.toLowerCase(),
                    role: element.getAttribute('role'),
                    text: element.innerText || '',
                    placeholder: element.getAttribute('placeholder') || '',
                    ariaLabel: element.getAttribute('aria-label') || ''
                }
            }""")
            
            # Determine element type and text
            element_type = element_props['role'] or element_props['tagName']
            element_text = (element_props['text'] or 
                          element_props['placeholder'] or 
                          element_props['ariaLabel'] or '')
            
            indexed_elements.append({
                'index': idx,
                'element': element,
                'selector': f'[{idx}]<{element_type}>{element_text}</{element_type}>'
            })
        return indexed_elements

def random_delay(min_seconds=2, max_seconds=4):
    """Add random delay to make actions look more human"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def convert_followers_count(text):
    """Convert followers text to number"""
    try:
        text = text.strip().lower()
        if 'k' in text:
            return float(text.replace('k', '')) * 1000
        elif 'm' in text:
            return float(text.replace('m', '')) * 1000000
        else:
            return float(text.replace(',', ''))
    except Exception as e:
        print(f"Error converting followers count '{text}': {e}")
        return 0

def is_valid_profile_url(href):
    """Check if URL is a valid profile URL"""
    invalid_patterns = ['hashtag', 'search?q=', 'src=', 'f=user']
    return href and not any(pattern in href for pattern in invalid_patterns)

def process_profile_list(page):
    while True:
        # Wait for profile cells to be visible
        page.wait_for_selector('[data-testid="cellInnerDiv"]', timeout=10000)
        random_delay(2, 3)
        
        # Get all profile cells
        profile_cells = page.query_selector_all('[data-testid="cellInnerDiv"]')
        print(f"\nFound {len(profile_cells)} profile cells in current view")
        
        processed_any = False
        
        for cell in profile_cells:
            try:
                # Find the main profile link within the cell
                profile_link = cell.query_selector('a[role="link"]')
                if not profile_link:
                    continue
                
                href = profile_link.get_attribute('href')
                if not href or not is_valid_profile_url(href) or href in processed_profiles:
                    continue
                
                processed_any = True
                print(f"\nProcessing new profile: {href}")
                processed_profiles.add(href)
                
                # Random delay before opening profile
                random_delay(2, 4)
                
                # Get base URL and construct full profile URL
                base_url = page.url.split('/search')[0]
                full_url = base_url + href
                print(f"Opening URL: {full_url}")

                # Create new tab and navigate to profile
                new_page = page.context.new_page()
                new_page.goto(full_url)
                print("Navigated to profile in new tab")

                # Wait for profile content to load
                random_delay(3, 5)
                
                # Check for DM button
                dm_button = new_page.query_selector(
                    'button[aria-label="Message"][data-testid="sendDMFromProfile"]'
                )
                
                keep_tab = False
                if dm_button:
                    print("DMs are open - Found message button")
                    
                    # Check followers count
                    try:
                        # Wait for profile content to load
                        random_delay(2, 3)
                        
                        # Find the Followers link and get its parent container
                        followers_link = new_page.evaluate('''
                            () => {
                                const spans = document.querySelectorAll('span');
                                for (const span of spans) {
                                    if (span.textContent === 'Followers') {
                                        const link = span.closest('a');
                                        if (link) {
                                            const spans = link.querySelectorAll('span');
                                            for (const s of spans) {
                                                const text = s.textContent;
                                                if (text && text !== 'Followers' && /^[\d,.KkMm]+$/.test(text.trim())) {
                                                    return text.trim();
                                                }
                                            }
                                        }
                                    }
                                }
                                return null;
                            }
                        ''')
                        
                        if followers_link:
                            print(f"Raw followers text: {followers_link}")
                            followers_count = convert_followers_count(followers_link)
                            print(f"Followers count: {followers_link} ({followers_count:,.0f})")
                            
                            if followers_count >= 10000:
                                print("✅ More than 10K followers - keeping tab open")
                                keep_tab = True
                            else:
                                print("❌ Less than 10K followers - closing tab")
                        else:
                            print("❌ Couldn't find followers count")
                            
                    except Exception as e:
                        print(f"Error checking followers count: {e}")
                        traceback.print_exc()
                else:
                    print("❌ DMs are closed - closing tab")
                
                # Handle tab management
                random_delay(1, 2)
                if not keep_tab:
                    new_page.close()
                    print("Closed profile tab")
                else:
                    print("Kept profile tab open")
                
                # Switch back to original tab
                page.bring_to_front()
                print("Switched back to search results")
                random_delay(2, 3)
                
                # Break after processing one profile
                break
                
            except Exception as e:
                print(f"Error processing profile: {e}")
                traceback.print_exc()
        
        # If we didn't process any new profiles, try scrolling
        if not processed_any:
            previous_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollBy(0, 300)")  # Scroll less aggressively
            random_delay(2, 3)
            
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                print("\nReached end of list - no more new profiles to load")
                break
            else:
                print("\nScrolled to load more profiles...")
                random_delay(1, 2)
                continue

def main():
    with sync_playwright() as p:
        try:
            # Connect to the existing Chrome instance
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]  # Get the first browser context
            page = context.pages[0] if context.pages else context.new_page()
            
            # Create our context wrapper
            browser_context = BrowserContext(page)
            element_tree = ElementTree(page)

            # Increase timeout settings
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)

            # Navigate to Twitter
            page.goto('https://twitter.com')
            time.sleep(2)  # Give a moment for the page to start loading

            # Get all clickable elements and print them for debugging
            elements = element_tree.get_clickable_elements()
            print("Found elements:")
            for elem in elements:
                print(elem['selector'])

            # Wait for and find the search box
            search_box = None
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # Try different selectors
                    selectors = [
                        'input[aria-label="Search query"]',
                        'input[placeholder*="Search"]',
                        'input[role="textbox"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            search_box = page.wait_for_selector(selector, state='visible', timeout=20000)
                            if search_box:
                                print(f"Found search box with selector: {selector}")
                                break
                        except Exception:
                            continue
                    
                    if search_box:
                        break
                    
                    if attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed with error: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(2)

            if search_box:
                # Ensure element is visible and clickable
                search_box.scroll_into_view_if_needed()
                time.sleep(1)
                
                # Click the search box
                search_box.click()
                time.sleep(1)
                
                # Type the search term with small delays
                search_box.fill('meme coin')
                time.sleep(1)
                
                # Press Enter
                search_box.press('Enter')

                # Instead of waiting for networkidle, let's wait for specific elements
                print("Waiting for search results...")
                
                # Wait for the navigation tabs to appear
                try:
                    # First wait for the tabs container
                    tabs = page.wait_for_selector('[role="tablist"]', timeout=10000)
                    if tabs:
                        print("Found tabs container")
                        
                        # Look for the People tab specifically
                        people_tab = None
                        selectors = [
                            'a[href*="/search?q=meme%20coin&src=typed_query&f=user"]',
                            '[role="tab"]:has-text("People")',
                            'a:has-text("People")',
                            'div[role="tab"]:has-text("People")'
                        ]
                        
                        for selector in selectors:
                            try:
                                people_tab = page.wait_for_selector(selector, state='visible', timeout=5000)
                                if people_tab:
                                    print(f"Found People tab with selector: {selector}")
                                    
                                    # Give the page a moment to stabilize
                                    time.sleep(2)
                                    
                                    # Click the People tab
                                    people_tab.click()
                                    print("Clicked People tab")
                                    
                                    # Wait for people results to appear
                                    page.wait_for_selector('[data-testid="cellInnerDiv"]', timeout=10000)
                                    print("People results loaded")

                                    # Wait a moment for the results to stabilize
                                    time.sleep(2)

                                    # After clicking People tab and waiting for results
                                    print("Starting to process profiles...")
                                    random_delay(2, 3)
                                    process_profile_list(page)
                                    
                                    break
                            except Exception as tab_error:
                                print(f"Selector {selector} failed: {tab_error}")
                                continue
                        
                        if not people_tab:
                            print("Could not find People tab")
                            # Print all available tabs for debugging
                            tabs_text = tabs.evaluate('el => el.innerText')
                            print(f"Available tabs: {tabs_text}")
                    
                except Exception as e:
                    print(f"Error while trying to click People tab: {e}")
                    # Get the current page content for debugging
                    print("\nCurrent page elements:")
                    elements = element_tree.get_clickable_elements()
                    for elem in elements:
                        print(elem['selector'])

            input('Press Enter to close connection...')
        except Exception as e:
            print(f"Error occurred: {e}")
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == '__main__':
    main() 