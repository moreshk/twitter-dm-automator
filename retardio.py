from playwright.sync_api import sync_playwright
import time
import random
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from openai import OpenAI

MESSAGE_BANK = [
    "there's a braindemic on the rise! are you team ADHD or AUTISM?",
    "breaking: braindemic outbreak detected! quick - ADHD or AUTISM?",
    "attention: braindemic wave incoming! declare your side: ADHD or AUTISM",
    "emergency braindemic alert! choose your team: ADHD or AUTISM",
    "the great braindemic spreads! which side are you on: ADHD or AUTISM?",
    "braindemic crisis detected! make your choice: ADHD or AUTISM",
    "warning: braindemic surge reported! pick your team: ADHD or AUTISM",
    "urgent: braindemic outbreak! where do you stand - ADHD or AUTISM?",
    "the braindemic continues! time to choose: ADHD or AUTISM",
    "new braindemic wave detected! what's your pick: ADHD or AUTISM?"
]

def random_delay(min_seconds=5, max_seconds=8):
    """Add random delay to make actions look more human"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def type_human_like(page, selector, text):
    """Type text like a human with random delays between characters"""
    for char in text:
        page.type(selector, char, delay=random.uniform(150, 300))
        random_delay(0.3, 0.6)

def check_profile_metrics(page):
    """Check if profile meets our criteria"""
    try:
        metrics = page.evaluate('''
            () => {
                const getCount = (text) => {
                    const span = Array.from(document.querySelectorAll('span')).find(
                        span => span.textContent === text
                    );
                    if (span) {
                        const anchor = span.closest('a');
                        if (anchor) {
                            const spans = anchor.querySelectorAll('span');
                            for (const span of spans) {
                                const count = span.textContent;
                                if (count && count !== text && /^[\d,.KkMm]+$/.test(count.trim())) {
                                    return count;
                                }
                            }
                        }
                    }
                    return '0';
                };

                const parseCount = (count) => {
                    const text = count.toLowerCase();
                    const num = parseFloat(text.replace(/,/g, ''));
                    if (text.includes('k')) return num * 1000;
                    if (text.includes('m')) return num * 1000000;
                    return num;
                };

                const followers = getCount('Followers');
                const following = getCount('Following');
                const isVerified = !!document.querySelector('[data-testid="icon-verified"]');

                return {
                    followers: parseCount(followers),
                    following: parseCount(following),
                    isVerified: isVerified
                };
            }
        ''')
        
        meets_criteria = (
            metrics['followers'] >= 500 and 
            metrics['followers'] > metrics['following']
        )
        
        print(f"Profile metrics:")
        print(f"Followers: {metrics['followers']:,.0f}")
        print(f"Following: {metrics['following']:,.0f}")
        print(f"Verified: {'✅' if metrics['isVerified'] else '❌'}")
        print(f"Meets criteria: {'✅' if meets_criteria else '❌'}")
        
        return meets_criteria, metrics['isVerified']
        
    except Exception as e:
        print(f"Error checking metrics: {e}")
        return False, False

def get_db_connection():
    """Create database connection using environment variables"""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )

def setup_database():
    """Create the tagged_users table if it doesn't exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tagged_users (
            username VARCHAR(255) PRIMARY KEY,
            tweet_text TEXT,
            tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def was_recently_tagged(username):
    """Check if user was tagged in the last 24 hours"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM tagged_users 
            WHERE username = %s 
            AND tagged_at > NOW() - INTERVAL '24 hours'
        )
    """, (username,))
    result = cur.fetchone()[0]
    cur.close()
    conn.close()
    return result

def record_tagged_user(username, tweet_text):
    """Record that we tagged a user"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tagged_users (username, tweet_text)
        VALUES (%s, %s)
        ON CONFLICT (username) DO UPDATE 
        SET tweet_text = %s, tagged_at = CURRENT_TIMESTAMP
    """, (username, tweet_text, tweet_text))
    conn.commit()
    cur.close()
    conn.close()

def replace_fruits(text):
    """Replace APPLE with ADHD and BANANA with AUTISM"""
    return text.replace('APPLE', 'ADHD').replace('BANANA', 'AUTISM')

def get_random_tweet_text(username):
    """Select a random pre-generated message and add username"""
    message = random.choice(MESSAGE_BANK)
    tweet = f"@{username} {message}"
    print(f"\nSelected tweet text: {tweet}")
    return tweet

def main():
    # Initialize database
    setup_database()
    
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
            print("Navigating to Twitter...")
            page.goto('https://twitter.com')
            random_delay()

            # Click search box and search for retardio
            print("Searching for 'retardio'...")
            page.click('[data-testid="SearchBox_Search_Input"]')
            random_delay(2, 4)
            page.fill('[data-testid="SearchBox_Search_Input"]', 'retardio')
            random_delay(3, 5)
            page.keyboard.press('Enter')
            random_delay(4, 6)

            # Click People tab
            print("Switching to People tab...")
            page.click('span:text("People")')
            random_delay(4, 6)

            processed_users = set()
            while True:
                # Get all user results
                users = page.evaluate('''
                    () => {
                        const users = Array.from(document.querySelectorAll('[data-testid="cellInnerDiv"]'));
                        return users.map(user => {
                            const userLink = user.querySelector('a[href*="/status/"]') || 
                                          user.querySelector('a[href*="/"]:not([href*="/status/"])');
                            return userLink ? userLink.href : null;
                        }).filter(href => href);
                    }
                ''')

                for user_url in users:
                    if user_url in processed_users:
                        continue

                    processed_users.add(user_url)
                    print(f"\nChecking profile: {user_url}")
                    random_delay(3, 5)

                    # Open profile in new tab
                    profile_page = page.context.new_page()
                    random_delay(4, 6)
                    profile_page.goto(user_url)
                    random_delay(4, 6)

                    # Check if profile meets criteria
                    meets_criteria, is_verified = check_profile_metrics(profile_page)
                    random_delay(3, 5)
                    
                    if meets_criteria:
                        username = profile_page.evaluate('''
                            () => {
                                const element = document.querySelector('[data-testid="User-Name"]');
                                return element ? element.textContent.split('@')[1].split('·')[0].trim() : null;
                            }
                        ''')
                        
                        if not username:
                            print("Skipping - Unable to determine username")
                            random_delay(1, 2)
                            profile_page.close()
                            random_delay(1, 3)
                            continue

                        # Check if user was recently tagged
                        if was_recently_tagged(username):
                            print(f"Skipping @{username} - tagged within last 24 hours")
                            random_delay(1, 2)
                            profile_page.close()
                            random_delay(1, 3)
                            continue

                        print(f"Found qualifying user: @{username}")
                        random_delay(1, 2)
                        profile_page.close()
                        random_delay(2, 3)

                        # Before posting, ensure at least 60 seconds have passed since last post
                        random_delay(60, 75)

                        # Open post composer in new tab
                        print("Opening post composer...")
                        post_page = page.context.new_page()
                        random_delay(1, 3)
                        post_page.goto('https://twitter.com/compose/tweet')
                        random_delay(2, 3)

                        # Generate and type tweet
                        tweet_text = get_random_tweet_text(username)
                        if not tweet_text:
                            random_delay(1, 2)
                            post_page.close()
                            random_delay(1, 3)
                            continue

                        print(f"Posting tweet: {tweet_text}")
                        type_human_like(post_page, '[data-testid="tweetTextarea_0"]', tweet_text)
                        random_delay(2, 3)

                        # Click post button
                        post_page.click('[data-testid="tweetButton"]')
                        random_delay(2, 3)
                        post_page.close()
                        random_delay(1, 3)

                        # Record the tag
                        record_tagged_user(username, tweet_text)
                        print("Tweet posted successfully!")
                        random_delay(2, 3)
                    else:
                        print("Profile doesn't meet criteria, moving to next...")
                        random_delay(1, 2)
                        profile_page.close()
                        random_delay(1, 3)

                    random_delay(4, 6)

                # Scroll down to load more results
                page.evaluate("window.scrollBy(0, 800)")
                random_delay(4, 6)

        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            browser.close()

if __name__ == '__main__':
    main() 