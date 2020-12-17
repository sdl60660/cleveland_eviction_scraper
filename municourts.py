from bs4 import BeautifulSoup
import requests

import csv
import json
import time
import os
from datetime import datetime, timedelta
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from anticaptchaofficial.imagecaptcha import *

import pickle
from collections import Counter

START_PAGE = 'https://clevelandmunicipalcourt.org/public-access'

class MuniCourtCrawler():

    def __init__(self, output_file, headless=True):
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--no-sandbox')
        if headless:
            chrome_options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.cookies = pickle.load(open("cookies.pkl", "rb"))
        self.outfile = output_file

    
    def __repr__(self):
        return ('<Selenium Driver for CLE Municipal Courts. Current Page: {}>'.format(str(self.driver.current_url)))
    

    def enter_site(self):
        self.driver.get(START_PAGE)
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)
        self.driver.implicitly_wait(8)

        # Click "I Accept" button on intial homepage
        try:
            self.click_button_name(button_name="   I Accept   ")
        except:
            time.sleep(4)
            self.click_button_name(button_name="   I Accept   ")


        # If captcha, solve using anticaptcha
        try:
            captcha_image = self.driver.find_element_by_xpath('//img[@class="captchaImg"]')

            # Solve captcha multiple times and use consensus answer
            captcha_text = self.solve_captcha(captcha_image)
            self.driver.set_window_size(1000, 1000)
            self.driver.back()

            # Put captcha answer in the answer box
            self.fill_box(element_id=None, element_xpath='//input[@class="captchaTxt"]', text=captcha_text)
            time.sleep(1)

        except NoSuchElementException:
            pass

        # Get to search page
        for button in ["Click Here"]:
            try:
                self.click_button_name(button_name=button)
            except:
                time.sleep(4)
                self.click_button_name(button_name=button)

        pickle.dump(self.driver.get_cookies(), open("cookies.pkl","wb"))
        # print(self.driver.get_cookies())
    

    def navigate_to_search_menu(self, menu_name):
        if not self.is_element_on_page('//span[text()="{}"]'.format(menu_name)):
            raise ValueError("Not a valid search menu name. At the time this was built, the search menu options were: 'Name Search'," + 
                            "'Ticket/Citation # Search', 'Case Number Search', and 'Case Type Search'. It's possible that these values " + 
                            "have changed, but regardless, the value you entered is not on the search menu page.")

        self.click_button_name(button_name=menu_name)


    def grab_captcha_image(self, captcha_image, filename):
        # Get image source
        src = captcha_image.get_attribute('src')

        # Download image
        self.driver.get(src)
        self.driver.set_window_size(300, 300)
        self.driver.save_screenshot(filename)


    def solve_captcha(self, captcha_image):
        captcha_image_filename = "captcha.png"

        # save captcha image to "captcha.png" file
        self.grab_captcha_image(captcha_image, captcha_image_filename)
        
        # Init captcha solver
        solver = imagecaptcha()
        # solver.set_verbose(1)

        # If you're someone else using this code, you'll need to get your own key here: https://anti-captcha.com/
        with open("captcha_key.txt", "r") as f:
            captcha_api_key = f.read()
            solver.set_key(captcha_api_key)

        # Have anticaptcha attempt the captcha five times and use the consensus answer (since they don't always get it right on one shot)
        total_attempts = 5
        captcha_attempt_answers = []
        print("Anticaptcha will be asked to solve captcha five times and we'll submit the consensus answer (since they do occasionally make mistakes)")
        for attempt in range(0, total_attempts):
            print("Solving captcha, attempt {} of {}".format(attempt+1, total_attempts))

            # Solve the captcha text and return answer
            captcha_text = solver.solve_and_return_solution(captcha_image_filename)
            if captcha_text != 0:
                print(f"captcha text {captcha_text}")
                captcha_attempt_answers.append(captcha_text)
            else:
                print(f"task finished with error {solver.error_code}")
                captcha_attempt_answers.append("[Unsolved]")

        answer_counts = Counter(captcha_attempt_answers)
        if "[Unsolved]" in answer_counts.keys() and answer_counts["[Unsolved]"] > 2:
            print("Captcha could not be solved on greater than 2 of 5 attempts. Try running everything again to generate a fresh captcha.")
            import sys
            sys.exit(0)

        consensus_answer = answer_counts.most_common(1)[0][0]
        return consensus_answer

    
    def set_search_options(self):
        time.sleep(0.5)

        # Hard-coded selection for 'Number of Results'
        self.click_button_xpath(button_xpath='//*[@name="bodyLayout:topSearchPanel:pageSize"]/option[@value="2"]')
        # Hard-coded selection for 'Case Type': "CVG - LANDLORD/TENANT" (Pre-select, this needs to be "clicked" twice)
        self.click_button_xpath(button_xpath='//*[@name="caseCd"]/option[7]')

        # tracker.click_button_xpath(button_xpath='//*[@name="ptyCd"]/option[12]')
        # tracker.click_button_xpath(button_xpath='//*[@id="id22"]/option[@value="2"]')
        time.sleep(0.5)

        # Hard-coded selection for 'Case Type': "CVG - LANDLORD/TENANT"
        self.click_button_xpath(button_xpath='//*[@name="caseCd"]/option[7]')

        # Hard-coded selection for 'Party Type'
        for x in range(2):
            self.scroll_to_element(element_xpath='//*[@name="ptyCd"]/option[12]')
            time.sleep(0.5)
    
    
    def fill_dates_and_press(self, date_string):
        # Fill Start Date box
        self.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:beginDate"]', text=date_string)
        time.sleep(0.2)

        # Fill End Date box
        self.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:endDate"]', text=date_string)

        # Press Submit button
        self.click_button_xpath(button_xpath='//*[@name="submitLink"]')
        #tracker.wait_until_loaded('//*[@id="grid"]/tbody/tr//a')

    
    def scrape_page_results(self, current_page):
        # Find case elements on the page
        try:
            rows = self.get_num_table_rows()
        except:
            time.sleep(2)
            rows = self.get_num_table_rows()
        
        rows = min(40, rows - (40 * (current_page - 1)))
        
        # For each case element
        for row_num in range(rows):
            try:
                row = self.get_table_row((row_num+1))
                # Follow case link
                row.click()

                # Parse/store data
                csv_dict = self.parse_data()
                self.store_data(csv_dict)

                # Go back to previous page with other case elements
                self.back_page()
            except Exception as e:
                time.sleep(1)
                print(e)


    def search_date(self, date, current_page_index):
        # IMPORTANT: Can only run starting from "Case Type Search" menu (will return to this menu at function end)
        
        # If not search menu page, throw error and exit
        if not self.is_element_on_page('//span[text()="Case Type Search"]'):
            raise RuntimeError("The search_date method can only be run from the search page. Crawler must be navigated to that page before running (using 'enter_site', then 'navigate_to_search_menu')")
        # If not on the "Case Type Search" tab of the search menu, throw error and exit
        if 'selected' not in self.driver.find_element_by_xpath('//span[text()="Case Type Search"]/ancestor::li').get_attribute("class"):
            raise RuntimeError("The search_date method can only be run from the 'Case Type Search' tab. Crawler must be navigated to that tab before running (using 'navigate_to_search_menu)")

        date_string = datetime.strftime(date, '%m/%d/%Y')
        print(date_string)

        self.set_search_options()
        self.fill_dates_and_press(date_string)
        
        while self.is_element_on_page('//span[@class="feedbackPanelERROR"]'):
            self.set_search_options()
            self.fill_dates_and_press(date_string)
            # errors = self.driver.find_elements_by_xpath('//span[@class="feedbackPanelERROR"]')

        num_pages = self.get_num_results_pages()
        print(num_pages)
        print(current_page_index)
        
        # Click on the page button for corresponding page number if we're looking for someting other than page 1
        if current_page_index > 1:
            self.click_button_xpath('//*[@title="Go to page {}"]'.format(current_page_index))
        
        self.scrape_page_results(current_page_index)

        # Try to return to search page and increment date
        # If the site sends us back to the welcome page, which seems to happen after a lot of quick scraping, re-enter with 'Click Here' button
        # self.click_button_name(button_name="Search")
        # if self.is_element_on_page(element_xpath='//span[text()="Click Here"]'):
        #     self.click_button_name(button_name="Click Here")

        if current_page_index == num_pages:
            date += timedelta(days=1)
            current_page_index = 1
        else:
            current_page_index += 1

        return date, current_page_index


    def click_button_name(self, button_name):
        button = self.driver.find_element_by_link_text(button_name).click()


    def click_button_xpath(self, button_xpath):
        button = self.driver.find_element_by_xpath(button_xpath).click()


    def is_element_on_page(self, element_xpath):
        matching_elements = self.driver.find_elements(By.XPATH, element_xpath)
        return len(matching_elements) > 0


    def scroll_to_element(self, element_xpath):
        element = self.driver.find_element_by_xpath(element_xpath)
        actions = ActionChains(self.driver)
        actions.move_to_element(element)
        actions.click()
        actions.perform()


    def fill_box(self, element_id, element_xpath, text):
        if element_id:
            self.driver.find_element_by_id(element_id).clear()
            element = self.driver.find_element_by_id(element_id)
        elif element_xpath:
            self.driver.find_element_by_xpath(element_xpath).clear()
            element = self.driver.find_element_by_xpath(element_xpath)
        else:
            raise ValueError('Must specify either an element_id or element_xpath')
        element.send_keys(text)

    
    def get_num_results_pages(self):
        # Split the result string, which will either be in the format "Displaying 100 of ___ total matches." if > 100 or "Displaying all ___ matches." if <= 100
        # Find the last integer in the string, which should be the total number of results from the date
        try:
            total_results = [int(x) for x in self.driver.find_element_by_id("srchResultNotice").text.split(" ") if MuniCourtCrawler.is_int(x)][-1]
            # Round down for now
            total_results = min(100, total_results)
        except:
            total_results = 0
        
        # CourtView will display a max of three pages of results and a max of 100 items, so find how many pages we'd expect from the results.
        # If there are more than 100 results for the selected date, we have a small problem that we can work on later
        # There are 40 results to a page, so floor divide by 40 (and add one)
        num_pages = min(3, ((total_results // 41) + 1))
        
        return num_pages


    def get_num_table_rows(self):
        text = self.driver.find_elements_by_xpath('*//div[@id="srchResultNotice"]')
        if len(text) == 0:
            return 0
        elif ' of ' in text[0].text:
            num_rows = int(text[0].text.split(' ')[3])
            return num_rows
        else:
            num_rows = int(text[0].text.split(' ')[2])
            return num_rows


    def get_table_row(self, num):
        return self.driver.find_elements_by_xpath('//*[@id="grid"]/tbody/tr[{}]//a'.format(num))[0]


    def parse_to_soup(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup


    def parse_data(self):
        soup = self.parse_to_soup()

        data_dict = {}

        # Case Name
        try:
            case_name = self.driver.find_elements_by_xpath('*//div[@id="titleBar"]//h2')[0].text.replace('\t', '').replace('\n', '').strip(' ')
        except:
            time.sleep(4)
            case_name = self.driver.find_elements_by_xpath('*//div[@id="titleBar"]//h2')[0].text.replace('\t', '').replace('\n', '').strip(' ')

        data_dict['Case Name'] = case_name

        # Case Number
        case_number = ' '.join(case_name.split(' ')[:3])
        data_dict['Case Number'] = case_number

        # Case Status, File Date, Action
        table = soup.find('table')
        cells = table.find_all('td')

        for cell in cells:
            data = cell.find_all('dd')
            title = cell.find_all('dt')

            if len(title) == 1:
                for field in {'Case Status', 'File Date', 'Action'}:
                    if field in title[0].text:
                        data_dict[field] = data[0].text

        # Address, Defendants, Plaintiff
        defendants = []
        plaintiffs = []

        parties = soup.find('div', attrs={'id':'ptyContainer'})
        rows = parties.find_all('div', attrs={'class': 'rowodd'}) + parties.find_all('div', attrs={'class': 'roweven'})

        for row in rows:
            try:
                header = row.find_all('div',attrs={'class': 'subSectionHeader2'})[0]
                text = header.find_all('h5')[0].text.replace('\n','').replace('\t','')
            except:
                continue

            if text.split(' - ')[1] == 'DEFENDANT':
                defendants.append(text.split(' - ')[0])

            elif text.split(' - ')[1] == 'PLAINTIFF':
                plaintiffs.append(text.split(' - ')[0])
                try:
                    data_dict['Plaintiff Address'], data_dict['Plaintiff City'] = MuniCourtCrawler.get_address_info(row)
                except:
                    data_dict['Plaintiff Address'], data_dict['Plaintiff City'] = 'Address Error', 'Address Error'

            elif text.split(' - ')[1] == 'PROPERTY ADDRESS':
                try:
                    data_dict['Property Address'], data_dict['Property City'] = MuniCourtCrawler.get_address_info(row)
                except:
                    data_dict['Plaintiff Address'], data_dict['Plaintiff City'] = 'Address Error', 'Address Error'

        data_dict['Plaintiff'] = '; '.join(plaintiffs)
        data_dict['Defendants'] = '; '.join(defendants)

        # Costs
        costs_table = soup.find('div', attrs={'id':'financialInfo'}).find('table')
        # try:
        data_dict['Costs'] = costs_table.find('tfoot').find_all('th',attrs={'class': 'currency'})[0].text
        # except:
            # data_dict['Costs'] = ''


        # Disposition Status, Disposition Date

        disposition_table = soup.find('div', attrs={'id':'dispositionInfo'}).find('table').find('tbody')
        data_dict['Disposition Status'] = disposition_table.find_all('td')[0].text
        data_dict['Disposition Date'] = disposition_table.find_all('td')[-1].text

        return data_dict


    def store_data(self, csv_dict):
        date_string = datetime.today().strftime('%Y%m%d')
        case_number = csv_dict['Case Number']

        try:
            # Keep record of scrape on specific date (as data will change)
            with open(f'page_source_files/{date_string}/{case_number}.html', 'w') as f:
                f.write(self.driver.page_source)

            # Add or replace to store of all files
            with open(f'page_source_files/all_data/{case_number}.html', 'w') as f:
                f.write(self.driver.page_source)
        except FileNotFoundError:
            os.mkdir(os.getcwd() + '/page_source_files/' + datetime.today().strftime('%Y%m%d'))
            with open(f'page_source_files/{date_string}/{case_number}.html', 'w') as f:
                f.write(self.driver.page_source)

        # NEW FIELDS HERE
        MuniCourtCrawler.write_to_csv(self.outfile, csv_dict)


    def back_page(self):
        self.driver.back()


    def quit(self):
        self.driver.quit()


    @staticmethod
    def write_to_csv(filename, dictionary):
        # If output file doesn't exist yet, create and add header. Otherwise, we're appending to an existing file
        if os.path.isfile(filename) == False:
            with open(filename, 'w') as f:
                fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
                'Defendants', 'Property Address', 'Property City',
                'Plaintiff', 'Plaintiff Address', 'Plaintiff City',
                'Costs', 'Disposition Status', 'Disposition Date']
                out_csv = csv.DictWriter(f, fieldnames=fields)
                out_csv.writeheader()

        with open(filename, 'a') as f:
            fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
                      'Defendants', 'Property Address', 'Property City',
                      'Plaintiff', 'Plaintiff Address', 'Plaintiff City',
                      'Costs', 'Disposition Status', 'Disposition Date']
            out_csv = csv.DictWriter(f, fieldnames=fields)
            out_csv.writerow(dictionary)


    @staticmethod
    def get_address_info(row):
        contact_data = row.find('div', attrs={'class': 'box ptyContact'})
        address = contact_data.find('dl').find('dd')
        address_line_1 = address.find('div',attrs={'class': 'addrLn1'}).text
        # address_line_2 = address.find('div',attrs={'class': 'addrLn2'}).text
        try:
            city = address.find_all('span')[0].text.title() + ', ' + address.find_all('span')[1].text
        except:
            city = 'Cleveland, OH'

        return address_line_1, city
    

    @staticmethod
    def is_int(a):
        try:
            return int(a)
        except ValueError:
            return False


def create_page_source_directories():
    # Create directory to store page source files (if it doesn't already exist)
    try:
        os.mkdir(os.getcwd() + '/page_source_files')
    except FileExistsError:
        pass

    # Create directory (if it doesn't exist) within page_source_files to store this day's raw source files (as they may change over time)
    try:
        os.mkdir(os.getcwd() + '/page_source_files/' + datetime.today().strftime('%Y%m%d'))
    except FileExistsError:
        pass

    # Create directory (if it doesn't exist) within page_source_files to store all most up-to-date source files for given cases
    try:
        os.mkdir(os.getcwd() + '/page_source_files/all_data')
    except FileExistsError:
        pass