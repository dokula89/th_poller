# Websites Auto Capture - Required Changes

## 1. Fix MySQL Error (Line ~11712)
```python
# FIND:
log_cursor.execute("INSERT INTO pending_jobs_log (checked_at) VALUES (%s)", (current_time,))

# REPLACE WITH:
log_cursor.execute("INSERT INTO pending_jobs_log (checked_at, label) VALUES (%s, %s)", (current_time, 'auto_check'))
```

## 2. Complete First-Run Logic Replacement (Line ~9748-9900)

Replace the entire first_run block starting from `if is_first_run:` with:

```python
if is_first_run:
    # Open browser first
    if idx == 0:
        time.sleep(5)
    else:
        webbrowser.open(site_url, new=0)
        time.sleep(3)
    
    # Show mode toggle popup
    mode_popup = tk.Toplevel(activity_win)
    mode_popup.title("Extraction Mode")
    mode_popup.configure(bg="#1C2833")
    mode_popup.attributes('-topmost', True)
    mode_popup.overrideredirect(True)
    
    screen_w = pyautogui.size()[0]
    screen_h = pyautogui.size()[1]
    popup_w = int(screen_w * 0.18)
    popup_h = 280
    popup_x = 10
    popup_y = int(screen_h * 0.3)
    mode_popup.geometry(f"{popup_w}x{popup_h}+{popup_x}+{popup_y}")
    
    tk.Label(mode_popup, text="🎯 Choose Mode",
            font=("Segoe UI", 10, "bold"), bg="#1C2833", fg="#F39C12").pack(pady=(10, 5))
    
    mode_status = tk.Label(mode_popup, text="Select extraction method:",
                          font=("Segoe UI", 9), bg="#1C2833", fg="#ECF0F1")
    mode_status.pack(pady=5)
    
    coords_label = tk.Label(mode_popup, text="",
                           font=("Segoe UI", 8), bg="#1C2833", fg="#BDC3C7")
    coords_label.pack(pady=5)
    
    profile_label = tk.Label(mode_popup, text="📋 Profile: Old Win",
                            font=("Segoe UI", 8), bg="#1C2833", fg="#9B59B6")
    profile_label.pack(pady=5)
    
    selected_mode = {'value': None}
    mode_chosen = {'done': False}
    
    def choose_headless():
        selected_mode['value'] = 'headless'
        mode_status.config(text="✅ Headless selected", fg="#9B59B6")
        mode_chosen['done'] = True
    
    def choose_browser():
        selected_mode['value'] = 'browser'
        mode_status.config(text="✅ Browser selected", fg="#3498DB")
        mode_chosen['done'] = True
    
    btn_frame = tk.Frame(mode_popup, bg="#1C2833")
    btn_frame.pack(pady=10)
    
    tk.Button(btn_frame, text="🤖 Headless\n(Auto + Record)", bg="#9B59B6", fg="white",
             font=("Segoe UI", 9, "bold"), command=choose_headless,
             width=15, height=2).pack(pady=5)
    
    tk.Button(btn_frame, text="🌐 Browser\n(Manual)", bg="#3498DB", fg="white",
             font=("Segoe UI", 9, "bold"), command=choose_browser,
             width=15, height=2).pack(pady=5)
    
    # Wait for selection
    wait_start = time.time()
    while not mode_chosen['done'] and time.time() - wait_start < 30:
        time.sleep(0.2)
    
    if selected_mode['value'] == 'headless' and webdriver:
        # HEADLESS MODE
        self._root.after(0, lambda: log_activity("🤖 Headless extraction..."))
        self._root.after(0, lambda: extraction_method_lbl.config(text="Method: Headless", fg="#9B59B6"))
        coords_label.config(text="Extracting...")
        
        try:
            chrome_opts = ChromeOptions()
            chrome_opts.add_argument("--headless")
            chrome_opts.add_argument("--disable-gpu")
            chrome_opts.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=chrome_opts)
            driver.get(site_url)
            time.sleep(3)
            
            page_html = driver.page_source
            driver.quit()
            
            save_path = websites_dir / f"gp_id-{site_id}.html"
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            self._root.after(0, lambda: log_activity("✅ HTML saved!"))
            self._root.after(0, lambda: extraction_method_lbl.config(text="Method: Headless ✅", fg="#27AE60"))
            coords_label.config(text="✅ Saved! Click element:", fg="#27AE60")
            
            # Inject highlighter in visible browser
            time.sleep(1)
            pyautogui.click(screen_w * 0.6, screen_h * 0.5)
            time.sleep(0.3)
            pyautogui.press('f12')
            time.sleep(0.5)
            pyautogui.click(int(screen_w * 0.35), int(screen_h * 0.95))
            time.sleep(0.3)
            pyautogui.click(int(screen_w * 0.6), int(screen_h * 0.98))
            time.sleep(0.3)
            
            highlighter_script = '''document.addEventListener('mouseover',e=>{document.querySelectorAll('.copilot-highlight-temp').forEach(el=>el.classList.remove('copilot-highlight-temp'));if(e.target.classList)e.target.classList.add('copilot-highlight-temp')});let s=document.createElement('style');s.innerHTML='.copilot-highlight-temp{outline:3px solid #00ff00!important;background:rgba(0,255,0,0.1)!important}';document.head.appendChild(s);'''
            pyautogui.typewrite(highlighter_script, interval=0.005)
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.5)
            pyautogui.press('f12')
            
            # Record coords
            recorded_click = {'x': None, 'y': None}
            def on_click(x, y, button, pressed):
                if pressed and x > screen_w * 0.2:
                    recorded_click['x'] = x
                    recorded_click['y'] = y
                    coords_label.config(text=f"✅ ({x}, {y})", fg="#27AE60")
                    return False
            
            listener = mouse.Listener(on_click=on_click)
            listener.start()
            
            wait_start = time.time()
            while time.time() - wait_start < 60:
                if recorded_click['x']:
                    break
                time.sleep(0.3)
            listener.stop()
            
            if recorded_click['x']:
                recorded_selections[site_id] = {
                    'click_x': recorded_click['x'],
                    'click_y': recorded_click['y']
                }
            
            # Update DB
            if db_cursor and db_conn:
                try:
                    db_cursor.execute("UPDATE google_addresses SET extraction_method = 'headless' WHERE id = %s", (site_id,))
                    db_conn.commit()
                except:
                    pass
            
            mode_popup.destroy()
            continue
            
        except Exception as headless_err:
            log_to_file(f"[Websites Capture] Headless failed: {headless_err}")
            coords_label.config(text=f"Failed!", fg="#E74C3C")
            selected_mode['value'] = 'browser'
    
    if selected_mode['value'] == 'browser':
        # BROWSER MODE
        self._root.after(0, lambda: log_activity("🌐 Browser mode..."))
        self._root.after(0, lambda: extraction_method_lbl.config(text="Method: Browser", fg="#3498DB"))
        coords_label.config(text="Choose action below")
        
        menu_action = {'value': None}
        # Continue with existing action dialog code...
```

## Summary of Changes:
1. **Fixed MySQL error** - added 'label' field to INSERT
2. **Mode toggle on left** - Headless/Browser buttons in popup
3. **Headless still opens browser** - for visual coord recording
4. **Records coords in both modes** - saves to recorded_selections dict
5. **Updates extraction_method field** - 'headless' or 'browser' in DB
