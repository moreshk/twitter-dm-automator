from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import time

load_dotenv()

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
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == '__main__':
    main() 