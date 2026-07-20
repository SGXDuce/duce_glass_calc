# AS 1288 Glass Thickness Calculator - EXE Launcher
# Starts the Flask server and opens the calculator in the default browser
# Duce Timber Windows and Doors

import datetime
import os
import sys
import threading
import webbrowser
import time

# When running as a PyInstaller EXE, files are unpacked to a temp folder
# referenced by sys._MEIPASS. This makes sure Flask can find templates,
# static files, and the data CSVs regardless of where the EXE is run from.
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from app import app, EXPIRY_DATE


def open_browser():
    """
    Waits briefly for the Flask server to start, then opens the
    calculator in the user's default web browser.
    """
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    print()
    print('=' * 65)
    print('  AS 1288 Glass Thickness Calculator')
    print('  Duce Timber Windows and Doors')
    print('=' * 65)
    print()

    if datetime.datetime.now() > EXPIRY_DATE:
        print(f'  This testing version has expired ({EXPIRY_DATE.strftime("%d %B %Y")}).')
        print('  Please contact the tool maintainer for the current version.')
        print()
        input('  Press Enter to close this window...')
        sys.exit(0)

    print('  Starting the calculator...')
    print('  Your browser will open automatically.')
    print()
    print('  IMPORTANT: Keep this window open while using the calculator.')
    print('  Closing this window will shut down the calculator.')
    print()

    # Open the browser in a separate thread so it does not block Flask
    threading.Thread(target=open_browser, daemon=True).start()

    # Run Flask without debug mode for production use
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)