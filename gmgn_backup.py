from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime, timedelta
import psycopg2
import os
from dotenv import load_dotenv

def setup_database():
    """Set up the PostgreSQL database connection using environment variables"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database connection details from environment variables
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )
    return conn

def calculate_token_creation_time(age_text):
    """Calculate token creation time from age text (e.g., '30s', '5m', '1h')"""
    if not age_text:
        return None
        
    try:
        # Convert age text to seconds
        seconds = 0
        if 'm' in age_text:
            seconds = int(age_text.replace('m', '')) * 60
        elif 's' in age_text:
            seconds = int(age_text.replace('s', ''))
        elif 'h' in age_text:
            seconds = int(age_text.replace('h', '')) * 3600
        
        if seconds > 0:
            # Calculate creation time in UTC
            creation_time = datetime.utcnow() - timedelta(seconds=seconds)
            return creation_time
        
    except Exception as e:
        print(f"Error parsing age data '{age_text}': {e}")
    
    return None

def insert_or_update_token(conn, token_data):
    """Insert a new token record or update if contract address already exists"""
    cursor = conn.cursor()
    
    # Check if token already exists
    cursor.execute("SELECT contract_address FROM pump_tokens WHERE contract_address = %s", 
                  (token_data['contractAddress'],))
    exists = cursor.fetchone()
    
    # Use UTC timestamps
    current_time = datetime.utcnow()
    
    # Calculate token creation time from age
    token_creation_time = calculate_token_creation_time(token_data['age'])
    
    if exists:
        # Update existing record
        cursor.execute('''
        UPDATE pump_tokens SET 
            token_symbol = %s,
            price = %s,
            liquidity = %s,
            holders = %s,
            transactions = %s,
            volume = %s,
            change_1m = %s,
            change_5m = %s,
            change_1h = %s,
            sol_data = %s,
            percent_change = %s,
            market_cap = %s,
            nomint = %s,
            blacklist = %s,
            burnt = %s,
            top10_percentage = %s,
            insiders_percentage = %s,
            dev = %s,
            updated_at = %s
        WHERE contract_address = %s
        ''', (
            token_data['tokenSymbol'],
            token_data['price'],
            token_data['liquidity'],
            token_data['holders'],
            token_data['transactions'],
            token_data['volume'],
            token_data['change1m'],
            token_data['change5m'],
            token_data['change1h'],
            token_data['solData'],
            token_data['percentChange'],
            token_data['marketCap'],
            token_data['nomint'],
            token_data['blacklist'],
            token_data['burnt'],
            token_data['top10Percentage'],
            token_data['insidersPercentage'],
            token_data['dev'],
            current_time,
            token_data['contractAddress']
        ))
        
        # Only update token_creation_time if we can calculate it and it's not already set
        if token_creation_time:
            cursor.execute('''
            UPDATE pump_tokens 
            SET token_creation_time = %s 
            WHERE contract_address = %s 
            AND (token_creation_time IS NULL OR token_creation_time > %s)
            ''', (
                token_creation_time,
                token_data['contractAddress'],
                token_creation_time
            ))
    else:
        # Insert new record
        cursor.execute('''
        INSERT INTO pump_tokens (
            contract_address,
            token_symbol,
            price,
            liquidity,
            holders,
            transactions,
            volume,
            change_1m,
            change_5m,
            change_1h,
            sol_data,
            percent_change,
            market_cap,
            nomint,
            blacklist,
            burnt,
            top10_percentage,
            insiders_percentage,
            dev,
            created_at,
            updated_at,
            token_creation_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            token_data['contractAddress'],
            token_data['tokenSymbol'],
            token_data['price'],
            token_data['liquidity'],
            token_data['holders'],
            token_data['transactions'],
            token_data['volume'],
            token_data['change1m'],
            token_data['change5m'],
            token_data['change1h'],
            token_data['solData'],
            token_data['percentChange'],
            token_data['marketCap'],
            token_data['nomint'],
            token_data['blacklist'],
            token_data['burnt'],
            token_data['top10Percentage'],
            token_data['insidersPercentage'],
            token_data['dev'],
            current_time,
            current_time,
            token_creation_time
        ))
    
    conn.commit()
    return exists is not None

def store_age_data(conn, token_symbol, age_text):
    """Store the age data in a separate format for analysis"""
    try:
        # Convert age text (like '2m' or '30s') to seconds
        seconds = 0
        if 'm' in age_text:
            seconds = int(age_text.replace('m', '')) * 60
        elif 's' in age_text:
            seconds = int(age_text.replace('s', ''))
        elif 'h' in age_text:
            seconds = int(age_text.replace('h', '')) * 3600
        
        if seconds > 0:
            # Calculate discovery time
            discovery_time = datetime.now() - datetime.timedelta(seconds=seconds)
            
            # Could store in a separate table if needed
            # For now, we'll just print it
            print(f"Token {token_symbol} was discovered at approximately {discovery_time}")
            
            return discovery_time
    except Exception as e:
        print(f"Error parsing age data: {e}")
    
    return None

def main():
    print("Attempting to connect to Chrome with remote debugging...")
    
    gmgn_url = "https://gmgn.ai/new-pair?chain=sol&rd=0&ppa=0&ms=0&fb=0&bp=0&or=0&mo=0&ry=0&0ren=1&0fr=1&0mihc=50&0ihc=1&0mish=50&0ish=1&0miv=5&0iv=1&0mac=30m&0mim=5&0im=1&0mahc=0"
    
    # Set up the database
    conn = setup_database()
    print("Database connection setup complete")
    
    with sync_playwright() as p:
        try:
            # Connect to existing Chrome instance
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.new_page()
            
            # Set longer timeouts
            page.set_default_timeout(30000)
            page.set_default_navigation_timeout(30000)
            
            # Navigate to gmgn.ai
            print(f"Navigating to: {gmgn_url}")
            page.goto(gmgn_url)
            print("Initial page load complete")
            
            # Wait for data to load
            print("Waiting for table data to load...")
            try:
                # First try to wait for tokens to appear in the table
                page.wait_for_selector('table', timeout=15000)
                print("Table found on page")
            except Exception as e:
                print(f"Warning: Table selector not found: {e}")
            
            time.sleep(5)
            
            # Run the data extraction loop
            while True:
                try:
                    # Take a screenshot to debug what's on the page
                    page.screenshot(path="gmgn_screenshot.png")
                    print("Saved screenshot for debugging")
                    
                    # Manually walk the DOM and extract content
                    records = page.evaluate('''
                    () => {
                        try {
                            // The table structure on gmgn.ai has rows with data-row-key attributes
                            const tokenRows = Array.from(document.querySelectorAll('.g-table-row'));
                            if (tokenRows.length === 0) {
                                console.log("No token rows found using .g-table-row selector");
                            }
                            
                            return tokenRows.map(row => {
                                // Get the full contract address from the row link
                                let fullContractAddress = "";
                                const tokenLinkElement = row.querySelector('a.css-1ahnstt');
                                if (tokenLinkElement && tokenLinkElement.getAttribute('href')) {
                                    const href = tokenLinkElement.getAttribute('href');
                                    // Format is usually /sol/token/mintAddress
                                    const parts = href.split('/');
                                    if (parts.length > 0) {
                                        fullContractAddress = parts[parts.length - 1];
                                    }
                                }
                                
                                // Extract token symbol - usually in a div with title attribute or bold text
                                let tokenSymbol = "";
                                const tokenNameElement = row.querySelector('.css-9enbzl');
                                if (tokenNameElement) {
                                    tokenSymbol = tokenNameElement.textContent.trim();
                                }
                                
                                // Extract time/age
                                let age = "";
                                const ageElement = row.querySelector('.g-table-cell:nth-child(2)');
                                if (ageElement) {
                                    age = ageElement.textContent.trim();
                                }
                                
                                // Extract SOL data
                                let solData = "";
                                let percentChange = "";
                                const solElement = row.querySelector('.css-1ubmcdg');
                                if (solElement) {
                                    // Get the SOL value
                                    const solValue = solElement.textContent.trim();
                                    const solMatch = solValue.match(/SOL\\s*([\\d.]+)\\/0\\.015/);
                                    if (solMatch) {
                                        solData = "SOL " + solMatch[1] + "/0.015";
                                    }
                                    
                                    // Get the percent change
                                    const percentElement = solElement.querySelector('.css-ix4bfh');
                                    if (percentElement) {
                                        percentChange = percentElement.textContent.trim();
                                    }
                                }
                                
                                // Extract liquidity
                                let liquidity = "";
                                const liquidityElement = row.querySelector('.g-table-cell:nth-child(4) .chakra-text');
                                if (liquidityElement) {
                                    liquidity = liquidityElement.textContent.trim();
                                }
                                
                                // Extract market cap (MC)
                                let marketCap = "";
                                const mcElement = row.querySelector('.g-table-cell:nth-child(4) .chakra-text');
                                if (mcElement) {
                                    marketCap = mcElement.textContent.trim();
                                }
                                
                                // Extract holders
                                let holders = "";
                                const holdersElement = row.querySelector('.g-table-cell:nth-child(5) .chakra-text');
                                if (holdersElement) {
                                    holders = holdersElement.textContent.trim();
                                }
                                
                                // Extract transactions
                                let transactions = "";
                                const txElement = row.querySelector('.g-table-cell:nth-child(6) .css-xe0j2');
                                if (txElement) {
                                    transactions = txElement.textContent.trim();
                                }
                                
                                // Extract volume
                                let volume = "";
                                const volElement = row.querySelector('.g-table-cell:nth-child(7) .chakra-text');
                                if (volElement) {
                                    volume = volElement.textContent.trim();
                                }
                                
                                // Extract price
                                let price = "";
                                const priceElement = row.querySelector('.g-table-cell:nth-child(8) .chakra-text');
                                if (priceElement) {
                                    price = priceElement.textContent.trim();
                                }
                                
                                // Extract percentage changes
                                let change1m = "";
                                let change5m = "";
                                let change1h = "";
                                
                                const change1mElement = row.querySelector('.g-table-cell:nth-child(9) .css-1srsqcm span');
                                if (change1mElement) {
                                    change1m = change1mElement.textContent.trim();
                                }
                                
                                const change5mElement = row.querySelector('.g-table-cell:nth-child(10) .css-1srsqcm span');
                                if (change5mElement) {
                                    change5m = change5mElement.textContent.trim();
                                }
                                
                                const change1hElement = row.querySelector('.g-table-cell:nth-child(11) .css-1srsqcm span');
                                if (change1hElement) {
                                    change1h = change1hElement.textContent.trim();
                                }
                                
                                // Extract Degen Audit fields
                                let nomint = "";
                                let blacklist = "";
                                let burnt = "";
                                let top10Percentage = "";
                                let insidersPercentage = "";
                                
                                // Look for NoMint field
                                const nomintElement = row.querySelector('.nomint-field');
                                if (nomintElement) {
                                    nomint = nomintElement.textContent.trim();
                                } else {
                                    // Try to find it by looking for "NoMint" text followed by Yes/No
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && node.textContent.includes('NoMint')) {
                                            const siblingNode = node.nextElementSibling;
                                            if (siblingNode && (siblingNode.textContent === "Yes" || siblingNode.textContent === "No")) {
                                                nomint = siblingNode.textContent.trim();
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                // Look for Blacklist field
                                const blacklistElement = row.querySelector('.blacklist-field');
                                if (blacklistElement) {
                                    blacklist = blacklistElement.textContent.trim();
                                } else {
                                    // Try to find it by looking for "Blacklist" text followed by Yes/No
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && node.textContent.includes('Blacklist')) {
                                            const siblingNode = node.nextElementSibling;
                                            if (siblingNode && (siblingNode.textContent === "Yes" || siblingNode.textContent === "No")) {
                                                blacklist = siblingNode.textContent.trim();
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                // Look for Burnt field
                                const burntElement = row.querySelector('.burnt-field');
                                if (burntElement) {
                                    burnt = burntElement.textContent.trim();
                                } else {
                                    // Try to find it by looking for "Burnt" text followed by Yes/No
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && node.textContent.includes('Burnt')) {
                                            const siblingNode = node.nextElementSibling;
                                            if (siblingNode && (siblingNode.textContent === "Yes" || siblingNode.textContent === "No")) {
                                                burnt = siblingNode.textContent.trim();
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                // Look for Top 10 percentage
                                const top10Element = row.querySelector('.top10-field');
                                if (top10Element) {
                                    top10Percentage = top10Element.textContent.trim();
                                } else {
                                    // Try several methods to find the Top 10 percentage value
                                    
                                    // Method 1: Look for the text after "Top 10" label
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && node.textContent.includes('Top 10')) {
                                            // Check the next sibling or nearby elements
                                            const siblings = node.parentElement ? Array.from(node.parentElement.children) : [];
                                            for (const sibling of siblings) {
                                                if (sibling !== node && sibling.textContent && sibling.textContent.includes('%')) {
                                                    top10Percentage = sibling.textContent.trim();
                                                    break;
                                                }
                                            }
                                            
                                            // If not found in siblings, try to extract from the element itself
                                            if (!top10Percentage) {
                                                const matches = node.parentElement ? node.parentElement.textContent.match(/Top 10\s+(\d+\.?\d*%)/i) : null;
                                                if (matches && matches.length > 1) {
                                                    top10Percentage = matches[1];
                                                }
                                            }
                                            
                                            if (top10Percentage) break;
                                        }
                                    }
                                    
                                    // Method 2: Extract from column values in a row
                                    if (!top10Percentage) {
                                        // Check for percentages that appear after Top 10 header
                                        const columns = row.querySelectorAll('.g-table-cell');
                                        columns.forEach((col, index) => {
                                            const headers = document.querySelectorAll('.g-table-head .g-table-cell');
                                            if (index < headers.length && headers[index] && 
                                                headers[index].textContent && 
                                                headers[index].textContent.includes('Top 10') &&
                                                col.textContent && 
                                                col.textContent.includes('%')) {
                                                top10Percentage = col.textContent.trim();
                                            }
                                        });
                                    }
                                    
                                    // Method 3: Look for values directly in the table structure
                                    if (!top10Percentage) {
                                        // This specific format shown in screenshots (10.1%, 65.8%, etc.)
                                        const percentageElements = row.querySelectorAll('*');
                                        for (const el of percentageElements) {
                                            const text = el.textContent;
                                            if (text && /^\d+(\.\d+)?%$/.test(text.trim()) && 
                                                !text.includes('0%')) { // Exclude Insiders 0%
                                                const previousElement = el.previousElementSibling;
                                                const parentText = el.parentElement ? el.parentElement.textContent : '';
                                                
                                                // Check if this is under Top 10 context and not under other percentage contexts
                                                if ((previousElement && previousElement.textContent.includes('Top 10')) ||
                                                    (parentText.includes('Top 10'))) {
                                                    top10Percentage = text.trim();
                                                    break;
                                                }
                                                
                                                // Backup approach - if no other percentage found, take the first valid one
                                                if (!top10Percentage && !parentText.includes('Insiders') && 
                                                    !parentText.includes('1m%') && !parentText.includes('5m%') && 
                                                    !parentText.includes('1h%')) {
                                                    top10Percentage = text.trim();
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // Look for Insiders percentage
                                const insidersElement = row.querySelector('.insiders-field');
                                if (insidersElement) {
                                    insidersPercentage = insidersElement.textContent.trim();
                                } else {
                                    // Try several methods to find the Insiders percentage
                                    
                                    // Method 1: Look for the text after "Insiders" label
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && node.textContent.includes('Insiders')) {
                                            // Check the next sibling or nearby elements
                                            const siblings = node.parentElement ? Array.from(node.parentElement.children) : [];
                                            for (const sibling of siblings) {
                                                if (sibling !== node && sibling.textContent && sibling.textContent.includes('%')) {
                                                    insidersPercentage = sibling.textContent.trim();
                                                    break;
                                                }
                                            }
                                            
                                            // If not found in siblings, try to extract from the element itself
                                            if (!insidersPercentage) {
                                                const matches = node.parentElement ? node.parentElement.textContent.match(/Insiders\s+(\d+\.?\d*%)/i) : null;
                                                if (matches && matches.length > 1) {
                                                    insidersPercentage = matches[1];
                                                }
                                            }
                                            
                                            if (insidersPercentage) break;
                                        }
                                    }
                                    
                                    // Method 2: Extract from column values in a row
                                    if (!insidersPercentage) {
                                        // Check for percentages that appear after Insiders header
                                        const columns = row.querySelectorAll('.g-table-cell');
                                        columns.forEach((col, index) => {
                                            const headers = document.querySelectorAll('.g-table-head .g-table-cell');
                                            if (index < headers.length && headers[index] && 
                                                headers[index].textContent && 
                                                headers[index].textContent.includes('Insiders') &&
                                                col.textContent) {
                                                insidersPercentage = col.textContent.trim();
                                            }
                                        });
                                    }
                                    
                                    // Method 3: Look for specific "0%" values in the context of Insiders
                                    if (!insidersPercentage) {
                                        const percentageElements = row.querySelectorAll('*');
                                        for (const el of percentageElements) {
                                            const text = el.textContent;
                                            // Looking for the 0% after Insiders
                                            if (text && text.trim() === '0%') {
                                                const previousElement = el.previousElementSibling;
                                                const parentText = el.parentElement ? el.parentElement.textContent : '';
                                                
                                                // Check if this is under Insiders context
                                                if ((previousElement && previousElement.textContent.includes('Insiders')) ||
                                                    (parentText.includes('Insiders'))) {
                                                    insidersPercentage = text.trim();
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    
                                    // Method 4: Direct DOM proximity approach - look for "0%" text appearing after an "Insiders" element
                                    if (!insidersPercentage) {
                                        const insiderHeaders = Array.from(row.querySelectorAll('*')).filter(el => 
                                            el.textContent && el.textContent.trim() === 'Insiders');
                                            
                                        for (const header of insiderHeaders) {
                                            // Look at position in DOM to find the next elements
                                            let current = header;
                                            while (current && current.nextElementSibling) {
                                                current = current.nextElementSibling;
                                                if (current.textContent && current.textContent.trim() === '0%') {
                                                    insidersPercentage = '0%';
                                                    break;
                                                }
                                            }
                                            
                                            if (insidersPercentage) break;
                                        }
                                    }
                                }
                                
                                // Extract Dev field
                                let dev = "";
                                const devElement = row.querySelector('.dev-field');
                                if (devElement) {
                                    dev = devElement.textContent.trim();
                                } else {
                                    // Look for "HODL" or "Sell All" text
                                    const nodeList = Array.from(row.querySelectorAll('*'));
                                    for (const node of nodeList) {
                                        if (node.textContent && (node.textContent.includes('HODL') || node.textContent.includes('Sell All'))) {
                                            dev = node.textContent.trim();
                                            break;
                                        }
                                    }
                                }
                                
                                // Get the displayed abbreviated contract address
                                let displayedAddress = "";
                                const addressElement = row.querySelector('.css-vps9hc');
                                if (addressElement) {
                                    displayedAddress = addressElement.textContent.trim();
                                }
                                
                                // Get raw text for debugging
                                const rawText = row.textContent.trim().substring(0, 200);
                                
                                return {
                                    tokenSymbol,
                                    age,
                                    solData,
                                    percentChange,
                                    liquidity,
                                    marketCap,
                                    price,
                                    holders,
                                    transactions,
                                    volume,
                                    change1m,
                                    change5m,
                                    change1h,
                                    contractAddress: fullContractAddress,
                                    displayedAddress,
                                    nomint,
                                    blacklist,
                                    burnt,
                                    top10Percentage,
                                    insidersPercentage,
                                    dev,
                                    rawText
                                };
                            });
                        } catch (error) {
                            console.error("Error extracting token data:", error);
                            return [];
                        }
                    }
                    ''')
                    
                    # Log the timestamp
                    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    print(f"\n--- Data extracted at {current_time} ---")
                    
                    # Print the extracted data and store in database
                    if records and len(records) > 0:
                        print(f"Found {len(records)} token entries")
                        new_tokens = 0
                        updated_tokens = 0
                        
                        for idx, record in enumerate(records):
                            token_info = f"Token #{idx+1}: {record['tokenSymbol']}"
                            if record['age']:
                                token_info += f" (Age: {record['age']})"
                                
                                # Calculate and display token creation time
                                creation_time = calculate_token_creation_time(record['age'])
                                if creation_time:
                                    token_info += f" [Created: {creation_time.strftime('%Y-%m-%d %H:%M:%S UTC')}]"
                                    
                            print(token_info)
                            
                            # Determine the contract address format
                            contract = record['contractAddress']
                            display = record['displayedAddress']
                            
                            # If the displayed address ends with "...ump", ensure full address does too
                            if display and display.endswith("...ump") and contract:
                                # Extract the suffix from displayed address
                                if not contract.endswith("ump"):
                                    contract = contract + "ump"
                                print(f"  Contract: {contract}")
                                print(f"  (Displayed as: {display})")
                            else:
                                print(f"  Contract: {contract}")
                                if display and display != contract:
                                    print(f"  (Displayed as: {display})")
                            
                            # Update contract address in record
                            record['contractAddress'] = contract
                            
                            if record['solData']:
                                print(f"  {record['solData']} {record['percentChange']}")
                            
                            if record['liquidity']:
                                print(f"  Liquidity: {record['liquidity']}")
                                
                            if record['marketCap']:
                                print(f"  Market Cap: {record['marketCap']}")
                                
                            if record['holders']:
                                print(f"  Holders: {record['holders']}")
                                
                            if record['transactions']:
                                print(f"  Transactions: {record['transactions']}")
                            
                            if record['volume']:
                                print(f"  Volume: {record['volume']}")
                                
                            if record['price']:
                                print(f"  Price: {record['price']}")
                            
                            changes = []
                            if record['change1m']: changes.append(f"1m: {record['change1m']}")
                            if record['change5m']: changes.append(f"5m: {record['change5m']}")
                            if record['change1h']: changes.append(f"1h: {record['change1h']}")
                            
                            if changes:
                                print(f"  Changes: {' | '.join(changes)}")
                                
                            # Print Degen Audit fields
                            degen_audit_fields = []
                            if record['nomint']: degen_audit_fields.append(f"NoMint: {record['nomint']}")
                            if record['blacklist']: degen_audit_fields.append(f"Blacklist: {record['blacklist']}")
                            if record['burnt']: degen_audit_fields.append(f"Burnt: {record['burnt']}")
                            if record['top10Percentage']: degen_audit_fields.append(f"Top 10: {record['top10Percentage']}")
                            if record['insidersPercentage']: degen_audit_fields.append(f"Insiders: {record['insidersPercentage']}")
                            
                            if degen_audit_fields:
                                print(f"  Degen Audit: {' | '.join(degen_audit_fields)}")
                            
                            # Print Dev field
                            if record['dev']:
                                print(f"  Dev: {record['dev']}")
                                
                            # Store in database
                            if record['contractAddress']:
                                was_updated = insert_or_update_token(conn, record)
                                if was_updated:
                                    updated_tokens += 1
                                else:
                                    new_tokens += 1
                            
                            print("")
                            
                        print(f"Database updated: {new_tokens} new tokens, {updated_tokens} updated tokens")
                    else:
                        print("No records found on page")
                        
                        # Debug info
                        page_title = page.title()
                        page_url = page.url
                        print(f"Current page title: {page_title}")
                        print(f"Current URL: {page_url}")
                        
                        # Dump HTML for debugging
                        print("Saving page HTML and screenshot for debugging...")
                        html_content = page.content()
                        with open("gmgn_debug.html", "w", encoding="utf-8") as f:
                            f.write(html_content)
                        page.screenshot(path="gmgn_debug.png")
                        print("HTML saved to gmgn_debug.html and screenshot to gmgn_debug.png")
                    
                    print("--- End of data ---\n")
                    
                    # Wait for 1 minute before next extraction
                    print(f"Waiting 60 seconds until next extraction...")
                    time.sleep(60)
                    
                    # The data updates automatically, no need to refresh
                    print("Waiting for auto-updated data...")
                    
                    # Wait for data to load
                    time.sleep(5)
                    
                except Exception as ex:
                    print(f"Error during data extraction: {ex}")
                    time.sleep(10)
            
        except Exception as e:
            print(f"Error occurred: {e}")
            print("\nMake sure Chrome is running with remote debugging enabled:")
            print("Run this command first:")
            print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --user-data-dir=~/chrome-debug-profile --remote-debugging-port=9222 --no-first-run --no-default-browser-check")
        finally:
            # Close database connection
            if conn:
                conn.close()

if __name__ == '__main__':
    main()
