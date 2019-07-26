# Support Scraper

Scrapes the support portal for specified release notes. Written for Python 3.7. 

## Setup
Download [Google Chrome](https://www.google.com/chrome/) and a corresponding [Chrome driver](https://sites.google.com/a/chromium.org/chromedriver/downloads).

Create the file `~/.panrc` that looks like this:
```
BINARY_LOCATION=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
DRIVER=${HOME}/vanilladriver
LOGGING_LEVEL=INFO
DEFAULT_DOWNLOAD_DIR=${HOME}/Downloads
```
`BINARY_LOCATION`: path to your Chrome executable
`DRIVER`: path to your Chrome driver
`LOGGING_LEVEL`: defines what log messages to print to console; one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`
`DEFAULT_DOWNLOAD_DIR`: path to the directory where Chrome dumps download files by default

Install the `requirements.txt` file, preferably in a virtual environment. From this repository: 
```
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

## Use
Source your virtual environment:
```
source .env/bin/activate
```

Run the script:
```
python -m 