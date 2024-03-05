Script that automatically skips to songs waiting in mediashare queue and sends play/pause signals when a mediashare is playing.

[Download here](../../releases)

Windows might complain that the program contains a virus. This is a false positive because the exe is created with pyinstaller, a tool that others have used to create malware. Virus scanners will therefore see pyinstallers code as malware, even though it's not.

On first run the script will ask for a JWT token for your streamelements user. You can find this by going [here](https://streamelements.com/dashboard/account/channels).  
It will then open a website that asks you to login with twitch and grant access.  
This information is stored in MediashareAutoskip.ini so that you don't have to redo these steps every time. If you want to login again, just delete this file.

Exit the script by pressing ctrl+c or by closing the terminal.
