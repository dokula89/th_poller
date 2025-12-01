"""
Track API usage for OpenAI and Google APIs
Logs all API calls to database for expense tracking
"""

import mysql.connector
from datetime import datetime
import json

# Pricing constants (as of 2025)
OPENAI_PRICING = {
    "gpt-4-vision-preview": {"input": 0.01 / 1000, "output": 0.03 / 1000},
    "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
    "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
    "gpt-4o": {"input": 0.0025 / 1000, "output": 0.01 / 1000},
    "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},
}

GOOGLE_PRICING = {
    "places_details": 0.017,
    "geocoding": 0.005,
    "places_search": 0.032,
    "places_nearby": 0.032,
}


def log_openai_call(model, input_tokens, output_tokens, endpoint="chat.completions", metadata=None):
    """
    Log an OpenAI API call to the database
    
    Args:
        model: Model name (e.g., "gpt-4-vision-preview")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        endpoint: API endpoint used
        metadata: Optional dict with additional info
    """
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="offta"
        )
        cursor = conn.cursor()
        
        # Calculate cost
        pricing = OPENAI_PRICING.get(model, {"input": 0.01 / 1000, "output": 0.03 / 1000})
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        total_tokens = input_tokens + output_tokens
        
        # Insert record
        cursor.execute("""
            INSERT INTO api_calls 
            (service, endpoint, tokens_used, input_tokens, output_tokens, model, cost_usd, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "openai",
            endpoint,
            total_tokens,
            input_tokens,
            output_tokens,
            model,
            cost,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[API Track] OpenAI: {total_tokens:,} tokens (${cost:.6f})")
        return cost
        
    except Exception as e:
        print(f"[API Track] Error logging OpenAI call: {e}")
        return 0


def log_google_call(endpoint, calls_count=1, metadata=None):
    """
    Log a Google API call to the database
    
    Args:
        endpoint: API endpoint (e.g., "places_details", "geocoding")
        calls_count: Number of API calls made
        metadata: Optional dict with additional info
    """
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="offta"
        )
        cursor = conn.cursor()
        
        # Calculate cost
        cost_per_call = GOOGLE_PRICING.get(endpoint, 0.01)
        total_cost = cost_per_call * calls_count
        
        # Insert record
        cursor.execute("""
            INSERT INTO api_calls 
            (service, endpoint, calls_count, cost_usd, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            "google",
            endpoint,
            calls_count,
            total_cost,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[API Track] Google {endpoint}: {calls_count} calls (${total_cost:.6f})")
        return total_cost
        
    except Exception as e:
        print(f"[API Track] Error logging Google call: {e}")
        return 0


def get_total_costs():
    """Get total costs for OpenAI and Google APIs"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="offta"
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                service,
                SUM(cost_usd) as total_cost,
                COUNT(*) as total_calls
            FROM api_calls
            GROUP BY service
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        costs = {
            "openai": {"cost": 0, "calls": 0},
            "google": {"cost": 0, "calls": 0}
        }
        
        for row in results:
            service = row['service']
            if service in costs:
                costs[service]['cost'] = float(row['total_cost'] or 0)
                costs[service]['calls'] = int(row['total_calls'] or 0)
        
        return costs
        
    except Exception as e:
        print(f"[API Track] Error getting total costs: {e}")
        return {"openai": {"cost": 0, "calls": 0}, "google": {"cost": 0, "calls": 0}}


if __name__ == "__main__":
    # Test the tracking
    print("Testing API tracking...")
    
    # Test OpenAI logging
    log_openai_call("gpt-4-vision-preview", 1000, 500, metadata={"test": True})
    
    # Test Google logging
    log_google_call("places_details", 5, metadata={"test": True})
    
    # Get totals
    costs = get_total_costs()
    print(f"\nTotal costs:")
    print(f"  OpenAI: ${costs['openai']['cost']:.4f} ({costs['openai']['calls']} calls)")
    print(f"  Google: ${costs['google']['cost']:.4f} ({costs['google']['calls']} calls)")
    print(f"  Total: ${costs['openai']['cost'] + costs['google']['cost']:.4f}")
