from playwright.sync_api import sync_playwright
import time
from dotenv import load_dotenv
import random

load_dotenv()

def random_delay(min_seconds=2, max_seconds=4):
    """Add random delay to make actions look more human"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def process_replies(page):
    """Process all replies in a post"""
    print("\nAnalyzing replies...")
    processed_replies = set()
    processed_users = set()  # New set to track processed usernames
    replies_processed = 0  # Counter for number of replies processed
    
    while True:
        # Get all reply tweets
        replies = page.evaluate('''
            () => {
                const replies = Array.from(document.querySelectorAll('article'));
                return replies.map(reply => {
                    const usernameElement = reply.querySelector('[data-testid="User-Name"]');
                    const verifiedBadge = reply.querySelector('[data-testid="icon-verified"]');
                    const userLink = reply.querySelector('[data-testid="User-Name"] a');
                    
                    return {
                        id: reply.getAttribute('aria-labelledby'),
                        username: usernameElement ? usernameElement.textContent : null,
                        isVerified: !!verifiedBadge,
                        profileUrl: userLink ? userLink.href : null
                    };
                });
            }
        ''')
        
        new_replies = False
        for reply in replies:
            if reply['id'] and reply['id'] not in processed_replies:
                new_replies = True
                processed_replies.add(reply['id'])
                
                if reply['username'] and reply['profileUrl']:
                    # Extract handle to check if we've processed this user before
                    handle = reply['username'].split('@')[-1].split('·')[0].strip()
                    
                    if handle in processed_users:
                        print(f"\nSkipping already processed user: @{handle}")
                        continue
                        
                    processed_users.add(handle)  # Add to processed users set
                    replies_processed += 1  # Increment counter
                    
                    try:
                        print(f"\nProcessing reply {replies_processed}/20")
                        # Open user profile in new tab
                        print(f"\nOpening profile for: {reply['username']}")
                        profile_page = page.context.new_page()
                        profile_page.goto(reply['profileUrl'])
                        random_delay(2, 3)
                        
                        # Get user stats
                        stats = profile_page.evaluate('''
                            (async () => {
                                const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
                                
                                const getCount = () => {
                                    const followerSpan = Array.from(document.querySelectorAll('span')).find(
                                        span => span.textContent === 'Followers'
                                    );
                                    
                                    if (followerSpan) {
                                        const anchor = followerSpan.closest('a');
                                        if (anchor) {
                                            const spans = anchor.querySelectorAll('span');
                                            for (const span of spans) {
                                                const text = span.textContent;
                                                if (text && text !== 'Followers' && /^[\d,.KkMm]+$/.test(text.trim())) {
                                                    return text;
                                                }
                                            }
                                        }
                                    }
                                    return '0';
                                };
                                
                                const getMutuals = () => {
                                    // Try different selectors to find the mutual followers text
                                    const selectors = [
                                        'div[style*="color: rgb(113, 118, 123)"]',
                                        'div.css-146c3p1',
                                        'div[dir="ltr"]'
                                    ];
                                    
                                    let mutualDiv = null;
                                    for (const selector of selectors) {
                                        const divs = document.querySelectorAll(selector);
                                        mutualDiv = Array.from(divs).find(div => 
                                            div.textContent.includes('Followed by') || 
                                            div.textContent.includes('others you follow')
                                        );
                                        if (mutualDiv) break;
                                    }
                                    
                                    if (!mutualDiv) {
                                        console.log('No mutual div found'); // Debug
                                        return 'No mutual followers';
                                    }
                                    
                                    const text = mutualDiv.textContent;
                                    console.log('Found mutual text:', text); // Debug
                                    
                                    if (text.includes('Followed by')) {
                                        // Extract the number of others
                                        const othersMatch = text.match(/(\d+) others? you follow/);
                                        const othersCount = othersMatch ? parseInt(othersMatch[1]) : 0;
                                        
                                        // Count named followers
                                        const namedCount = text.split('Followed by ')[1]
                                            .split(' and ')[0]
                                            .split(', ')
                                            .length;
                                            
                                        const totalCount = namedCount + othersCount;
                                        console.log(`Named: ${namedCount}, Others: ${othersCount}, Total: ${totalCount}`); // Debug
                                        
                                        return `${totalCount} mutual followers`;
                                    }
                                    
                                    return 'No mutual followers';
                                };
                                
                                const hasDMButton = () => {
                                    return !!document.querySelector('[data-testid="sendDMFromProfile"]');
                                };
                                
                                const isNotFollowing = () => {
                                    const followButton = document.querySelector('[data-testid$="-follow"]');
                                    const followingButton = document.querySelector('[data-testid$="-unfollow"]');
                                    return followButton && !followingButton;
                                };
                                
                                // Add delays between operations
                                await sleep(Math.random() * 2000 + 2000); // 2-4s delay
                                const followers = getCount();
                                
                                await sleep(Math.random() * 2000 + 2000); // 2-4s delay
                                const followersNum = (() => {
                                    const text = followers.toLowerCase();
                                    const num = parseFloat(text.replace(/,/g, ''));
                                    if (text.includes('k')) {
                                        return num * 1000;
                                    } else if (text.includes('m')) {
                                        return num * 1000000;
                                    }
                                    return num;
                                })();
                                
                                await sleep(Math.random() * 2000 + 2000); // 2-4s delay
                                const mutuals = getMutuals();
                                
                                await sleep(Math.random() * 2000 + 2000); // 2-4s delay
                                const dmOpen = hasDMButton();
                                
                                await sleep(Math.random() * 2000 + 2000); // 2-4s delay
                                const notFollowing = isNotFollowing();
                                
                                return {
                                    followers,
                                    followersNum,
                                    mutuals,
                                    dmOpen,
                                    notFollowing
                                };
                            })()
                        ''')
                        
                        # Clean up username to get handle only
                        handle = reply['username'].split('@')[-1].split('·')[0].strip()
                        # Get profile name (just first word before any spaces)
                        profile_name = reply['username'].split('@')[0].strip().split()[0]
                        
                        print(f"Username: @{handle} {' 🔵' if reply['isVerified'] else ''}")
                        print(f"Followers: {stats['followers']} ({stats['followersNum']:,.0f})")
                        print(f"DMs: {'🔓 Open' if stats['dmOpen'] else '🔒 Closed'}")
                        print(f"Following: {'❌ No' if stats['notFollowing'] else '✅ Yes'}")
                        print(f"Mutuals: {stats['mutuals']}")
                        
                        # Check if user has >1K followers, open DMs, not following them, and >5 mutuals
                        mutuals_count = int(stats['mutuals'].split()[0]) if stats['mutuals'] != 'No mutual followers' else 0
                        
                        if (stats['followersNum'] >= 1000 and 
                            stats['dmOpen'] and 
                            stats['notFollowing'] and 
                            mutuals_count >= 5):
                            
                            print(f"🎯 High Value Target! 🎯")
                            print(f"✨ {stats['followers']} followers with open DMs and {mutuals_count} mutuals ✨")
                            
                            try:
                                print("Opening DM...")
                                random_delay(2, 4)  # Natural delay before clicking
                                
                                # Click the DM button and wait for input with longer timeout
                                profile_page.click('[data-testid="sendDMFromProfile"]')
                                profile_page.wait_for_selector('[data-testid="dmComposerTextInput"]', timeout=60000)  # Increased to 60 seconds
                                random_delay(2, 4)
                                
                                # Check for existing messages and their timing
                                message_check = profile_page.evaluate('''
                                    () => {
                                        const messageEntries = document.querySelectorAll('[data-testid="messageEntry"]');
                                        if (messageEntries.length === 0) {
                                            return { hasMessages: false };
                                        }
                                        
                                        // Get the last message's timestamp
                                        const lastMessage = messageEntries[messageEntries.length - 1];
                                        const timeElement = lastMessage.querySelector('time');
                                        if (!timeElement) {
                                            return { hasMessages: true, hoursSinceLastMessage: 24 }; // Default to 24 hours if no time found
                                        }
                                        
                                        const messageTime = new Date(timeElement.getAttribute('datetime'));
                                        const currentTime = new Date();
                                        
                                        // Ensure both dates are valid
                                        if (isNaN(messageTime.getTime()) || isNaN(currentTime.getTime())) {
                                            console.log('Invalid date detected');
                                            return { hasMessages: true, hoursSinceLastMessage: 24 };
                                        }
                                        
                                        const hoursSinceLastMessage = (currentTime - messageTime) / (1000 * 60 * 60);
                                        console.log('Message time:', messageTime);
                                        console.log('Current time:', currentTime);
                                        console.log('Hours since last message:', hoursSinceLastMessage);
                                        
                                        return {
                                            hasMessages: true,
                                            hoursSinceLastMessage: hoursSinceLastMessage
                                        };
                                    }
                                ''')
                                
                                # Determine if we should send a message
                                should_send_message = True
                                if message_check['hasMessages']:
                                    if message_check['hoursSinceLastMessage'] < 24:
                                        print(f"Last message was sent {message_check['hoursSinceLastMessage']:.1f} hours ago. Skipping.")
                                        should_send_message = False
                                    else:
                                        print(f"Last message was sent {message_check['hoursSinceLastMessage']:.1f} hours ago. Sending follow-up.")
                                
                                if should_send_message:
                                    # Prepare message based on conversation history
                                    if message_check['hasMessages']:
                                        message = f"gm {profile_name}"
                                    else:
                                        message = f"""gm {profile_name}

I'm Hal — a Solana wallet sidekick on X

Send, Swap, or Launch tokens just by tagging me

"@heyhalxyz send 1000 $Fartcoin to @cz_binance"

Wen tag?"""
                                    
                                    # Type message with chunks
                                    message_chunks = message.split('\n\n')
                                    for i, chunk in enumerate(message_chunks):
                                        if i > 0:  # Add newlines back for all chunks except first
                                            profile_page.keyboard.press('Enter')
                                            profile_page.keyboard.press('Enter')
                                            random_delay(1, 2)
                                        profile_page.type('[data-testid="dmComposerTextInput"]', chunk, delay=100)
                                        random_delay(2, 3)  # Delay between chunks
                                    
                                    random_delay(3, 5)  # Longer delay after typing
                                    
                                    # Click send with longer wait
                                    profile_page.click('[data-testid="dmComposerSendButton"]')
                                    print(f"Sent DM to {profile_name}:")
                                    print(f"{'(Follow-up message)' if message_check['hasMessages'] else '(First contact)'}")
                                    print(message)
                                    random_delay(6, 8)  # Increased delay after sending before closing
                                    
                            except Exception as e:
                                print(f"Error in DM process: {e}")
                        
                        # Close profile tab and return to post
                        print("Closing profile tab...")
                        profile_page.close()
                        random_delay(2, 4)
                    
                    except Exception as e:
                        print(f"Error processing user profile: {e}")
                        try:
                            profile_page.close()
                        except:
                            pass
                    
                    # Check if we've processed 20 replies
                    if replies_processed >= 20:
                        print("\nReached 20 replies limit. Moving to next viral post...")
                        return
                    
                    random_delay(1, 2)
        
        if not new_replies or replies_processed >= 20:
            break
            
        # Scroll down to load more replies if we haven't hit our limit
        page.evaluate("window.scrollBy(0, 800)")
        random_delay(2, 3)

def main():
    with sync_playwright() as p:
        try:
            # Connect to existing Chrome instance
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            # Set longer timeouts
            page.set_default_timeout(120000)        # Increased to 120 seconds
            page.set_default_navigation_timeout(120000)

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
                                        views: article.querySelector('[data-testid="analytics"]')?.textContent || '0',
                                        link: article.querySelector('a[href*="/status/"]')?.href || null
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
                                replies = int(post['replies'].replace(',', '')) if post['replies'].replace(',', '').isdigit() else 0
                                
                                if replies >= 20:
                                    print("\n🔥 High Engagement Post Found! (20+ replies) 🔥")
                                    if post['link']:
                                        try:
                                            print(f"Opening viral post in new tab...")
                                            new_page = page.context.new_page()
                                            new_page.goto(post['link'])
                                            print(f"Opened: {post['link']}")
                                            random_delay(2, 3)
                                            
                                            # Process replies in the new tab
                                            process_replies(new_page)
                                            
                                            # Close the tab after processing
                                            print("Closing reply tab...")
                                            new_page.close()
                                            random_delay(1, 2)
                                            
                                            # Switch back to main tab
                                            page.bring_to_front()
                                            
                                        except Exception as e:
                                            print(f"Error processing viral post: {e}")
                                            try:
                                                new_page.close()
                                                page.bring_to_front()
                                            except:
                                                pass
                                else:
                                    print("\nNew Post Details:")
                                    
                                print(f"Username: {post['username']}")
                                print(f"Content: {post['content']}")
                                print(f"Replies: {post['replies']} {'💬' if replies >= 20 else ''}")
                                print(f"Retweets: {post['retweets']}")
                                print(f"Likes: {post['likes']}")
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