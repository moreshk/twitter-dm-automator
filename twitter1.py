from playwright.sync_api import sync_playwright
import time
from dotenv import load_dotenv
import random

load_dotenv()

def random_delay(min_seconds=1, max_seconds=2):
    """Add random delay to make actions look more human"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def main():
    with sync_playwright() as p:
        try:
            # Connect to existing Chrome instance
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            # Set longer timeouts
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)

            # Navigate to Twitter
            page.goto('https://twitter.com')
            random_delay()

            # Wait for and click the For you tab
            for_you_selectors = [
                'a[href="/home"]',
                'a[href*="/home"]',
                'span:has-text("For you")',
                '[role="tab"]:has-text("For you")',
                '[role="link"]:has-text("For you")'
            ]
            
            for_you_tab = None
            for selector in for_you_selectors:
                try:
                    for_you_tab = page.wait_for_selector(selector, state='visible', timeout=5000)
                    if for_you_tab:
                        print("Found For you tab")
                        for_you_tab.click()
                        print("Clicked For you tab")
                        break
                except Exception:
                    continue

            if not for_you_tab:
                print("Could not find For you tab")
            else:
                # Wait for posts to load
                print("Waiting for posts to load...")
                page.wait_for_selector('[data-testid="cellInnerDiv"]', timeout=10000)
                random_delay(2, 3)

                processed_posts = set()  # Keep track of processed posts

                while True:
                    try:
                        # Get all posts
                        posts = page.evaluate('''
                            () => {
                                const articles = Array.from(document.querySelectorAll('article'));
                                return articles.map(article => {
                                    const usernameElement = article.querySelector('[data-testid="User-Name"]');
                                    const contentElement = article.querySelector('[data-testid="tweetText"]');
                                    
                                    const getMetric = (testId) => {
                                        const element = article.querySelector(`[data-testid="${testId}"]`);
                                        return element ? element.textContent : '0';
                                    };
                                    
                                    return {
                                        id: article.getAttribute('aria-labelledby'),
                                        username: usernameElement ? usernameElement.textContent : null,
                                        content: contentElement ? contentElement.textContent : null,
                                        replies: getMetric('reply'),
                                        retweets: getMetric('retweet'),
                                        likes: getMetric('like'),
                                        views: article.querySelector('[data-testid="analytics"]')?.textContent || '0'
                                    };
                                });
                            }
                        ''')

                        # Process new posts
                        new_posts = False
                        for post in posts:
                            if post['id'] and post['id'] not in processed_posts:
                                new_posts = True
                                processed_posts.add(post['id'])
                                
                                # Convert metrics to integers
                                likes = int(post['likes'].replace(',', '')) if post['likes'].replace(',', '').isdigit() else 0
                                retweets = int(post['retweets'].replace(',', '')) if post['retweets'].replace(',', '').isdigit() else 0
                                
                                if likes > 20 or retweets > 20:
                                    print("\n🔥 Viral Post Found! 🔥")
                                else:
                                    print("\nNew Post Details:")
                                    
                                print(f"Username: {post['username']}")
                                print(f"Content: {post['content']}")
                                print(f"Replies: {post['replies']}")
                                print(f"Retweets: {post['retweets']} {'⭐' if retweets > 20 else ''}")
                                print(f"Likes: {post['likes']} {'⭐' if likes > 20 else ''}")
                                print(f"Views: {post['views']}")
                                
                                random_delay(1, 2)  # Delay between processing posts

                        if new_posts:
                            # Scroll down a bit
                            page.evaluate("window.scrollBy(0, 500)")
                            random_delay(2, 4)  # Delay after scrolling
                        else:
                            # If no new posts, scroll more
                            page.evaluate("window.scrollBy(0, 800)")
                            random_delay(3, 5)  # Longer delay when no new posts found

                    except Exception as e:
                        print(f"Error processing posts: {e}")
                        random_delay(2, 3)  # Delay after error before retrying
                        continue

            input('Press Enter to close connection...')
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    main()