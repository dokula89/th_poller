Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\dokul\Desktop\robot\th_poller"
WshShell.Run ".venv\Scripts\pythonw.exe config_hud.py", 0, False
