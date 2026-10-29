import subprocess
import os

chrome = r'C:\Users\RAJATH U\AppData\Local\Google\Chrome\Application\chrome.exe'
res = subprocess.run(
    [chrome, '--headless=new', '--screenshot=frontend_screenshot.png', '--window-size=1280,800', '--dump-dom', 'http://localhost:5173'],
    capture_output=True
)

with open('dumped_dom.html', 'wb') as f:
    f.write(res.stdout)

print('DOM written to dumped_dom.html, size:', len(res.stdout))
print('Screenshot written to frontend_screenshot.png, exists:', os.path.exists('frontend_screenshot.png'))

