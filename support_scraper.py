# Copyright (c) 2019, Palo Alto Networks
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Author: Giselle Serate <gserate@paloaltonetworks.com>

'''
Palo Alto Networks support_scraper.py

Downloads the latest release notes and updates off the support portal.

Run with a Chrome driver and instance. Configure in a ~/.panrc file.

This software is provided without support, warranty, or guarantee.
Use at your own risk.
'''

import logging
from logging.config import dictConfig
import os
from time import sleep, time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options



class SupportScraper:
    '''
    A web scraping utility that downloads updates from the support portal.

    Non-keyword arguments:
    chrome_driver -- the name of the Chrome driver to use
    binary_location -- the path to the Chrome binary
    download_dir -- the default directory where Chrome downloads files
    login_time -- how long we wait for you to log in

    '''
    def __init__(self, chrome_driver='chromedriver',
                 binary_location='/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
                 download_dir=f"{os.getenv('HOME')}/Downloads", login_time=60):
        # Set up driver
        chrome_options = Options()
        chrome_options.binary_location = binary_location
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--disable-dev-shm-usage')
        # chrome_options.add_argument('--remote-debugging-port=9222')
        # chrome_options.add_argument('--headless')
        self._driver = webdriver.Chrome(executable_path=os.path.abspath(chrome_driver),
                                        options=chrome_options)

        # Init details
        self._download_dir = download_dir
        self.contents = {}
        self._main_handle = None
        self._on_update_page = None
        try:
            self._login_time = int(login_time)
        except ValueError:
            # Can't convert to an int; use a default.
            self._login_time = 60

        self._login()


    def __del__(self):
        # Wait for files to finish downloading before we close out.
        logging.info("Waiting for all files to finish downloading.")
        sleep(5)  # let the driver start downloading
        file_list = self._list_all_download_files()
        while 'Unconfirmed' in file_list or 'crdownload' in file_list:
            file_list = self._list_all_download_files()
            sleep(1)
        logging.info(f"Finished downloading everything. Any files downloaded may be found in {self._download_dir}")
        self._driver.close()


    def _login(self):
        '''Log into support portal.'''
        # Until somebody drops the 2FA, use a manual login.
        self._driver.get(f"https://support.paloaltonetworks.com/")
        logging.info("USER INTERACTION REQUIRED: Please log in.")
        self._driver.get(f'https://identity.paloaltonetworks.com/idp/startSSO.ping?PartnerSpId=supportCSP&TargetResource=https://support.paloaltonetworks.com')
        # Log in now. You have 1 minute.
        sleep(self._login_time)
        # Now we're logged in. Carry on with the rest of the script.
        logging.info("Finished waiting for you to log in.")


    def _find_update_page(self, update_type):
        '''
        Navigate to get the links and details.

        Non-keyword arguments:
        update_type -- a string determining update page to get from (Dynamic or Software)

        '''
        self._driver.get(f"https://support.paloaltonetworks.com/Updates/{update_type}Updates/")
        while self._driver.current_url == 'https://support.paloaltonetworks.com/Support/Index':
            # Keep trying to log in.
            self._login()
            self._driver.get(f"https://support.paloaltonetworks.com/Updates/{update_type}Updates/")
        logging.debug("Logged into support portal.")

        tbody = self._driver.find_element_by_xpath('//*[@id="Grid"]/table/tbody')
        trs = tbody.find_elements_by_xpath(".//tr")

        header = "NULL"
        try:
            self.contents[update_type]
        except KeyError:
            # Get new contents.
            self.contents[update_type] = {}

            for tr in trs:
                if tr.get_attribute('class') == 'k-grouping-row':
                    # It's a header
                    header = str(tr.find_element_by_xpath('./td/p').get_attribute('innerHTML')).split('>')[-1]
                    # Clean the header
                    header = ' '.join(header.split())
                    new_section = True
                elif new_section:
                    # It's an update
                    tds = tr.find_elements_by_xpath('./td')
                    showing_tds = [td for td in tds if 'display: none' not in td.get_attribute('style')]
                    update = {}
                    update['version'] = showing_tds[1].get_attribute('innerHTML')
                    update['date'] = showing_tds[2].get_attribute('innerHTML')
                    update['notes'] = showing_tds[3]
                    update['download'] = showing_tds[4]
                    self.contents[update_type][header] = update
                    new_section = False

        # Save this as the base window before getting adventurous.
        self._main_handle = self._driver.current_window_handle
        self._on_update_page = update_type
        logging.debug(f"Finished reading in updates for {update_type} Updates.")
        logging.debug(self.contents[update_type])


    def download_latest_release(self, update_type, key, is_notes):
        '''
        Download the page source of only the latest update.

        Non-keyword arguments:
        update_type -- a string determining update page to get from (Dynamic or Software)
        key -- a string showing the section to go through and download a release from
        is_notes -- a bool of whether you want release notes OR the raw files
        '''
        if self._on_update_page != update_type:
            self._find_update_page(update_type)

        logging.info(f"Downloading {update_type} {key} {'notes' if is_notes else 'raw files'} from version {self.contents[update_type][key]['version']} from support portal.")
        while True:
            try:
                self.contents[update_type][key]['notes' if is_notes else 'download'].click()
                break
            except ElementClickInterceptedException:
                # They're blocking the UI, try again.
                pass
        # Get the one window we've just opened (it will only open a new window for notes).
        for handle in self._driver.window_handles:
            if handle != self._main_handle:
                self._driver.switch_to.window(handle)
                # Save to disk
                os.chdir(self._download_dir)
                filename = f"Updates_{update_type}_{key}_{self.contents[update_type][key]['version']}.html"
                with open(filename, 'w') as file:
                    file.write(self._driver.page_source)
                # Go back to previous page
                self._driver.close()
                self._driver.switch_to.window(self._main_handle)


    def _list_all_download_files(self):
        '''
        See if there are any unfinished files in the download folder.
        '''
        for (_, _, filenames) in os.walk(self._download_dir):
            return str(filenames)



if __name__ == '__main__':
    # Load in config.
    home = os.getenv('HOME')
    env_path = os.path.join(home, '.panrc')
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    # Config logging.
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default'
        }},
        'root': {
            'level': os.getenv('LOGGING_LEVEL'),
            'handlers': ['wsgi']
        }
    })

    scraper = SupportScraper(chrome_driver=os.getenv('DRIVER'),
                             binary_location=os.getenv('BINARY_LOCATION'),
                             download_dir=os.getenv('DEFAULT_DOWNLOAD_DIR'),
                             login_time=os.getenv('LOGIN_TIME'))

    scraper.download_latest_release('Dynamic', 'Apps', False)

    scraper.download_latest_release('Dynamic', 'WF-500 Content', False)

    # PanOS
    scraper.download_latest_release('Software', 'PAN-OS for the PA-200 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-220 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-500 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-800 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-2000 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-3000 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-3200 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-4000 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-5000 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-5200 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-7000 Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for the PA-7000b Platform', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series Base Images', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series NSX Base Images', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series SDX Base Images', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series KVM Base Images', False)
    scraper.download_latest_release('Software', 'PAN-OS for VM-Series Hyper-V Base Image', False)

    scraper.download_latest_release('Software', 'GlobalProtect Agent Bundle', False)

    scraper.download_latest_release('Software', 'Panorama M Images', False)

    scraper.download_latest_release('Software', 'WF-500 Appliance Updates', False)
