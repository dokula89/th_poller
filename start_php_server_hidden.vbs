Set WshShell = CreateObject("WScript.Shell")
' Run PowerShell script hidden
WshShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Users\dokul\Desktop\robot\th_poller\start_php_server.ps1""", 0, False
