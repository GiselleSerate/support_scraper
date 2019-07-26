# Support Scraper

Scrapes the Palo Alto Networks support portal for specified release notes or raw files. Written for Python 3.7. For this to work, you'll need a support portal login.

## Setup
Download [Google Chrome](https://www.google.com/chrome/) and a corresponding [Chrome driver](https://sites.google.com/a/chromium.org/chromedriver/downloads).

Create the file `~/.panrc` that looks like this:
```
BINARY_LOCATION=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
DRIVER=${HOME}/vanilladriver
LOGGING_LEVEL=INFO
DEFAULT_DOWNLOAD_DIR=${HOME}/Downloads
LOGIN_TIME=30
```
* `BINARY_LOCATION`: path to your Chrome executable
* `DRIVER`: path to your Chrome driver
* `LOGGING_LEVEL`: defines what log messages to print to console; one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`
* `DEFAULT_DOWNLOAD_DIR`: path to the directory where Chrome dumps download files by default
* `LOGIN_TIME`: number of seconds to wait for the user to log in

Install the `requirements.txt` file, preferably in a virtual environment. From this repository: 
```
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

## Use
Source your virtual environment: `source .env/bin/activate`

Run the script: `python support_scraper.py`

You will be prompted to interact with the Chrome window that pops up--when you hit the PAN single sign on window, log in with your email/password. Then input the 2FA code from your email. At this point, the script can be left alone; it will finish on its own.

Files will be downloaded to Chrome's default download directory. If the script doesn't stop when all downloads seem to have completed, you may have some aborted file downloads in this directory; if you delete these files, the scraper will finish gracefully.