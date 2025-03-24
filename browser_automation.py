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

                # Wait for search results
                page.wait_for_load_state('networkidle')
                print("Search completed successfully.")
            else:
                print("Search box not found after all attempts.")

            input('Press Enter to close connection...')
        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == '__main__':
    main() 