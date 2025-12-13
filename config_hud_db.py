#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database operations for HUD
Split from config_hud.py
"""

# Database configuration - used by parcel automation
# Uses EXTERNAL MySQL database (same as main app)
DB_CONFIG = {
    'host': '172.104.206.182',
    'port': 3306,
    'user': 'seattlelisted_usr',
    'password': 'T@5z6^pl}',
    'database': 'offta'
}


def update_db_status(network_id, status, error_msg=None):
    """Update network status in database with optional error message"""
    try:
        import mysql.connector
        
        conn = mysql.connector.connect(**DB_CONFIG, connect_timeout=10)
        cursor = conn.cursor()
        
        if error_msg:
            cursor.execute(
                "UPDATE networks SET status = %s, error_message = %s WHERE id = %s",
                (status, error_msg, network_id)
            )
        else:
            cursor.execute(
                "UPDATE networks SET status = %s, error_message = NULL WHERE id = %s",
                (status, network_id)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB update error: {e}")

