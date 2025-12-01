"""
Track OpenAI API costs per day and month
Cost: $0.0035 per image (gpt-4o vision model)
"""

import mysql.connector
from datetime import datetime, date

def log_openai_cost(num_images, cost_per_image=0.0035):
    """Log OpenAI API usage and cost to database"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta'
        )
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS openai_api_costs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL,
                time DATETIME NOT NULL,
                num_images INT NOT NULL,
                cost_per_image DECIMAL(10, 6) NOT NULL,
                total_cost DECIMAL(10, 4) NOT NULL,
                model VARCHAR(50) DEFAULT 'gpt-4o',
                INDEX idx_date (date)
            )
        """)
        
        # Insert cost record
        total_cost = num_images * cost_per_image
        now = datetime.now()
        today = date.today()
        
        cursor.execute("""
            INSERT INTO openai_api_costs 
            (date, time, num_images, cost_per_image, total_cost, model)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (today, now, num_images, cost_per_image, total_cost, 'gpt-4o'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Logged OpenAI cost: {num_images} images = ${total_cost:.4f}")
        return total_cost
        
    except Exception as e:
        print(f"Error logging OpenAI cost: {e}")
        return 0


def get_daily_cost(target_date=None):
    """Get total cost for a specific date (default: today)"""
    if target_date is None:
        target_date = date.today()
    
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta'
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                SUM(num_images) as total_images,
                SUM(total_cost) as total_cost
            FROM openai_api_costs
            WHERE date = %s
        """, (target_date,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result or {'total_images': 0, 'total_cost': 0}
        
    except Exception as e:
        print(f"Error getting daily cost: {e}")
        return {'total_images': 0, 'total_cost': 0}


def get_monthly_cost(year=None, month=None):
    """Get total cost for a specific month (default: current month)"""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta'
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                SUM(num_images) as total_images,
                SUM(total_cost) as total_cost
            FROM openai_api_costs
            WHERE YEAR(date) = %s AND MONTH(date) = %s
        """, (year, month))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result or {'total_images': 0, 'total_cost': 0}
        
    except Exception as e:
        print(f"Error getting monthly cost: {e}")
        return {'total_images': 0, 'total_cost': 0}


if __name__ == "__main__":
    # Test
    print("Today's costs:")
    daily = get_daily_cost()
    print(f"  Images: {daily['total_images']}")
    print(f"  Cost: ${float(daily['total_cost'] or 0):.4f}")
    
    print("\nThis month's costs:")
    monthly = get_monthly_cost()
    print(f"  Images: {monthly['total_images']}")
    print(f"  Cost: ${float(monthly['total_cost'] or 0):.4f}")
