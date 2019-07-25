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

No external config necessary. Run with a Chrome driver and instance.

This software is provided without support, warranty, or guarantee.
Use at your own risk.
'''

import logging
from logging.config import dictConfig
import os
import pickle
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options



class SupportScraper:
    '''
    A web scraping utility that downloads release notes from a firewall.
    Does NOT use elasticsearch.

    Non-keyword arguments:
    ip -- the IP of the firewall to scrape
    username -- the firewall username
    password -- the firewall password
    chrome_driver -- the name of the Chrome driver to use
    binary_location -- the path to the Chrome binary
    download_dir -- where to download the notes to

    '''
    def __init__(self,
                 chrome_driver='chromedriver',
                 binary_location='/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
                 download_dir='contentpacks'):
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

        self._login()


    def __del__(self):
        self._driver.close()


    def _login(self):
        '''Log into support portal.'''
        self._driver.get(f"https://support.paloaltonetworks.com/")
        # Try using cookies
        try:
            cookies = pickle.load(open("cookies.pkl", "rb"))
            for cookie in cookies:
                self._driver.add_cookie(cookie)
        except FileNotFoundError:
            # We can create the cookie file later.
            pass

        # Until somebody drops the 2FA, use a manual login to save cookies if necessary. Cookies expire daily.
        if self._driver.current_url == 'https://support.paloaltonetworks.com/Support/Index':
            # Looks like we're not logged in.
            logging.info("Cookies expired or do not yet exist. Please log in.")
            self._driver.get(f'https://identity.paloaltonetworks.com/idp/startSSO.ping?PartnerSpId=supportCSP&TargetResource=https://support.paloaltonetworks.com')
            # Log in now. You have 1 minute.
            sleep(30)
            pickle.dump(self._driver.get_cookies() , open("cookies.pkl","wb"))
            # Now we're logged in. Carry on with the rest of the script.
            logging.info("Finished logging in.")


    def _find_update_page(self, update_type):
        '''Navigate to get the links and details.'''
        self._driver.get(f"https://support.paloaltonetworks.com/Updates/{update_type}Updates/")

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
                    self.contents[update_type][header] = []
                else:
                    # It's an update
                    tds = tr.find_elements_by_xpath('./td')
                    showing_tds = [td for td in tds if 'display: none' not in td.get_attribute('style')]
                    update = {}
                    update['version'] = showing_tds[1].get_attribute('innerHTML')
                    update['date'] = showing_tds[2].get_attribute('innerHTML')
                    update['notes'] = showing_tds[3]
                    update['download'] = showing_tds[4]
                    self.contents[update_type][header].append(update)
                    logging.debug(len(self.contents[update_type]))
        
        # Save this as the base window before getting adventurous.
        self._main_handle = self._driver.current_window_handle
        self._on_update_page = update_type
        logging.debug(f"Finished reading in updates for {update_type} Updates.")


    def download_latest_release(self, update_type, key, is_notes):
        '''
        Download the page source of only the latest update.
        
        Non-keyword arguments:
        update_type - a string determining update page to get from (Dynamic or Software)
        key - a string showing the section to go through and download a release from
        is_notes - a bool of whether you want release notes OR the raw files
        '''
        logging.info(f"Downloading the single latest {update_type} {'update notes' if is_notes else 'raw update'} from {key} from the support portal.")
        if self._on_update_page != update_type:
            self._find_update_page(update_type)
        # Get the absolute latest release notes
        latest = max(self.contents[update_type][key], key=lambda x: x['date'])
        self._download_release(update_type, key, is_notes, latest)


    def download_all_available_releases(self, update_type, key, is_notes):
        '''
        Download the page source for all releases of a certain type on the support portal.

        Non-keyword arguments:
        update_type - a string determining update page to get from (Dynamic or Software)
        key - a string showing the section to go through and download a release from
        is_notes - a bool of whether you want release notes OR the raw files
        '''
        logging.info(f"Downloading all {update_type} releases for {key} from the support portal.")
        if self._on_update_page != update_type:
            self._find_update_page(update_type)
        for ver in self.contents[update_type][key]:
            self._download_release(update_type, key, is_notes, ver)


    def _download_release(self, update_type, key, is_notes, release):
        '''
        Download the specified release from the support portal.
        '''
        logging.debug(f"Downloading {update_type} {key} {'notes' if is_notes else 'raw files'} from version {release['version']} from support portal.")
        while True:
            try:
                release['notes' if is_notes else 'download'].click()
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
                filename = f"Updates_{update_type}_{key}_{release['version']}.html"
                with open(filename, 'w') as file:
                    file.write(self._driver.page_source)
                # Go back to previous page
                self._driver.close()
                self._driver.switch_to.window(self._main_handle)



if __name__ == '__main__':
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
            'level': 'DEBUG',
            'handlers': ['wsgi']
        }
    })

    scraper = SupportScraper(chrome_driver='/Users/gserate/_dev/pandorica/vanilladriver',
                             binary_location='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                             download_dir="/Users/gserate/_dev/content_notes")

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
