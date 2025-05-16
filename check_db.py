import psycopg2
import os
from dotenv import load_dotenv

def check_database():
    """Check the database schema and show sample data"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database connection details from environment variables
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        print("Connected to database successfully")
        
        cursor = conn.cursor()
        
        # Check table schema
        cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'pump_tokens'
        ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("\nTable Schema:")
        print("-" * 50)
        for col in columns:
            print(f"{col[0]:<30} {col[1]}")
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM pump_tokens")
        count = cursor.fetchone()[0]
        print(f"\nTotal records: {count}")
        
        # Show sample data
        if count > 0:
            cursor.execute("""
            SELECT 
                token_symbol, 
                price, 
                market_cap, 
                nomint, 
                blacklist, 
                burnt, 
                top10_percentage, 
                insiders_percentage, 
                dev
            FROM pump_tokens 
            ORDER BY created_at DESC 
            LIMIT 5
            """)
            
            records = cursor.fetchall()
            print("\nLatest 5 records:")
            print("-" * 100)
            print(f"{'Token':<15} {'Price':<20} {'Market Cap':<15} {'NoMint':<8} {'Blacklist':<10} {'Burnt':<8} {'Top 10%':<10} {'Insiders%':<10} {'Dev':<10}")
            print("-" * 100)
            
            for record in records:
                print(f"{str(record[0]):<15} {str(record[1]):<20} {str(record[2]):<15} {str(record[3]):<8} {str(record[4]):<10} {str(record[5]):<8} {str(record[6]):<10} {str(record[7]):<10} {str(record[8]):<10}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database() 