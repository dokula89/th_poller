#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SplashScreen class
Extracted from config_utils.py (lines 478-567)
"""

from config_core import *

class SplashScreen:
    """Preloader splash screen with progress bar"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Loading Queue Poller...")
        self.root.overrideredirect(True)
        
        # Center on screen
        w, h = 400, 180
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Style
        bg = "#101214"
        fg = "#E8EAED"
        accent = "#58A6FF"
        
        frame = tk.Frame(self.root, bg=bg, bd=2, relief="solid", highlightthickness=0)
        frame.pack(fill="both", expand=True)

        # Close (X) button in the top-right corner
        topbar = tk.Frame(frame, bg=bg)
        topbar.pack(fill="x", side="top")
        close_btn = tk.Label(topbar, text="✕", fg="#95A5A6", bg=bg, font=("Segoe UI", 10), padx=6, cursor="hand2")
        close_btn.pack(side="right")
        def _on_close(_e=None):
            try:
                self.close()
            finally:
                try:
                    self.root.destroy()
                except Exception:
                    pass
                os._exit(0)
        close_btn.bind("<Button-1>", _on_close)
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#E74C3C"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#95A5A6"))
        try:
            self.root.protocol("WM_DELETE_WINDOW", _on_close)
        except Exception:
            pass
        
        # Logo/Title
        title = tk.Label(frame, text="🚀 Queue Poller", font=("Segoe UI", 16, "bold"), fg=accent, bg=bg)
        title.pack(pady=(20, 10))
        
        # Status label
        self.status_label = tk.Label(frame, text="Initializing...", font=("Segoe UI", 9), fg=fg, bg=bg)
        self.status_label.pack(pady=5)
        
        # Progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Splash.Horizontal.TProgressbar", 
                       troughcolor=bg,
                       background=accent,
                       bordercolor=bg,
                       lightcolor=accent,
                       darkcolor=accent)
        
        self.progress = ttk.Progressbar(frame, style="Splash.Horizontal.TProgressbar", 
                                       length=300, mode='determinate', maximum=100)
        self.progress.pack(pady=10)
        
        # Version/info
        info = tk.Label(frame, text="v2.0 • Python Tkinter", font=("Segoe UI", 8), fg="#A0A6AD", bg=bg)
        info.pack(pady=(10, 15))
        
        self.root.update()
    
    def update_progress(self, value: int, message: str = ""):
        """Update progress bar (0-100) and optional status message"""
        try:
            self.progress['value'] = value
            if message:
                self.status_label.config(text=message)
            self.root.update()
        except:
            pass
    
    def close(self):
        """Close splash screen"""
        try:
            self.root.destroy()
        except:
            pass

