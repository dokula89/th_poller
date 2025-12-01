"""
Add defensive check for DB_CONFIG in upload function
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add check after exec to ensure DB_CONFIG was loaded
old_code = '''            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')
            
            self.window.after(0, lambda: self.append_log(f"Config loaded: host={DB_CONFIG.get('host')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}"))'''

new_code = '''            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')
            
            if DB_CONFIG is None:
                self.window.after(0, lambda: self.append_log("✗ ERROR: DB_CONFIG not found in config file!"))
                self.window.after(0, lambda: self.append_log(f"Available keys: {list(config_globals.keys())}"))
                raise ValueError("DB_CONFIG not found in config_hud_db.py")
            
            self.window.after(0, lambda: self.append_log(f"Config loaded: host={DB_CONFIG.get('host')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}"))'''

content = content.replace(old_code, new_code)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added defensive DB_CONFIG check")
