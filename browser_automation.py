from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp('http://localhost:9222')
        context = browser.contexts[0]
        pages = context.pages
        page = pages[0] if pages else context.new_page()
        try:
            page.goto('https://twitter.com', wait_until='networkidle')
            input('Press Enter to close connection...')
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            browser.disconnect()

if __name__ == '__main__':
    main() 