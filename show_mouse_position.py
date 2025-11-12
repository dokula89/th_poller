import tkinter as tk
import pyautogui

def update_position():
    x, y = pyautogui.position()
    label.config(text=f"X: {x}  Y: {y}")
    root.after(50, update_position)

root = tk.Tk()
root.title("Mouse Position")
root.attributes('-topmost', True)  # Always on top
root.wm_attributes('-topmost', 1)  # Force always on top

# Position at top left
root.geometry("150x50+0+0")

label = tk.Label(root, font=("Courier", 12), bg="black", fg="lime", padx=10, pady=10)
label.pack()

update_position()
root.mainloop()
