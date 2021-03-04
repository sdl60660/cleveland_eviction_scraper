from bs4 import BeautifulSoup
import requests

import csv
import json
import time
import os
import re
from datetime import datetime, timedelta
import urllib.request

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from selenium.common.exceptions import NoSuchElementException

from anticaptchaofficial.imagecaptcha import *

import pickle
from collections import Counter

START_PAGE = 'https://clevelandmunicipalcourt.org/public-access'

class MuniCourtCrawler():

    def __init__(self, output_file, headless=True):
        chrome_options = webdriver.ChromeOptions()

        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("enable-automation")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        if headless:
            chrome_options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(8)

        self.cookies = pickle.load(open("cookies.pkl", "rb"))
        self.outfile = output_file

        if os.path.splitext(output_file)[1] == '.json':
            self.outfile_format = 'json'
            self.set_case_dict()
        else:
            self.outfile_format = 'csv'

    
    def __repr__(self):
        return ('<Selenium Driver for CLE Municipal Courts. Current Page: {}>'.format(str(self.driver.current_url)))
    

    def enter_site(self):
        self.driver.get(START_PAGE)
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)

        # Click "I Accept" button on intial homepage
        for attempt in range(5):
            try:
                self.click_button_name(button_name="   I Accept   ")
                break
            except:
                time.sleep(1)

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
        for attempt in range(5):
            try:
                self.click_button_name(button_name="Click Here")
                break
            except:
                time.sleep(1)

        pickle.dump(self.driver.get_cookies(), open("cookies.pkl","wb"))
        self.cookies = self.driver.get_cookies()
    

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

        # Have anticaptcha attempt the captcha seven times and use the consensus answer (since they don't always get it right on one shot)
        total_attempts = 7
        captcha_attempt_answers = []
        print("Anticaptcha will be asked to solve captcha seven times and we'll submit the consensus answer (since they do occasionally make mistakes)")
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

    
    def set_case_dict(self):
        # Load existing data and transform from array of dicts into a dictionary that we can add to/update
        try:
            with open(self.outfile, 'r') as f:
                json_array = json.load(f)
                case_dict = { x['Case Number']: x for x in json_array }
        # If outfile isn't an existing file, just create a new, empty dict
        except FileNotFoundError:
            case_dict = {}
        # If outfile exists, but isn't in the correct format, throw and erro
        except TypeError:
            raise TypeError('If output file is an existing JSON, it must be in the format of an array of dicts.')
        
        self.case_dict = case_dict


    def dump_case_dict(self):
        case_array = list(self.case_dict.values())

        with open(self.outfile, 'w') as f:
            json.dump(case_array, f)


    def set_search_options(self, status_filter=None):
        time.sleep(0.3)

        # Hard-coded selection for 'Number of Results'
        select = Select(self.driver.find_element_by_xpath('//*[@name="bodyLayout:topSearchPanel:pageSize"]'))
        select.select_by_visible_text("40")
        time.sleep(0.3)
        
        # Hard-coded selection for 'Case Type': "CVG - LANDLORD/TENANT" (Pre-select, this needs to be "clicked" twice)
        select = Select(self.driver.find_element_by_xpath('//*[@name="caseCd"]'))
        select.deselect_all()
        select.select_by_visible_text("CVG  -  LANDLORD/TENANT")
        time.sleep(0.3)

        # Hard-coded selection for 'Party Type'
        for _ in range(2):
            self.scroll_to_element(element_xpath='//*[@name="ptyCd"]/option[text()="PROPERTY ADDRESS"]')
            time.sleep(0.3)
        
        # Select 'Case Status' if a status_filter is set
        if status_filter:
            select = Select(self.driver.find_element_by_xpath('//*[@name="statCd"]'))
            select.deselect_all()
            select.select_by_visible_text(status_filter)
            time.sleep(0.3)

    
    def fill_dates_and_press(self, date, end_date=None):
        date_string = datetime.strftime(date, '%m/%d/%Y')
        
        if end_date:
            end_date_string = datetime.strftime(end_date, '%m/%d/%Y')
            print(f"{date_string} to {end_date_string}")
        else:
            print(date_string)

        # Fill Start Date box
        self.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:beginDate"]', text=date_string)
        time.sleep(0.2)

        # Fill End Date box
        if end_date:
            self.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:endDate"]', text=end_date_string)
        else:
            self.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:endDate"]', text=date_string)

        # Press Submit button
        self.click_button_xpath(button_xpath='//*[@name="submitLink"]')
        #tracker.wait_until_loaded('//*[@id="grid"]/tbody/tr//a')


    def fill_case_number_and_press(self, case_number):
        # Fill Case Number box
        self.fill_box(element_id="caseDscr", element_xpath=None, text=case_number)

        # Press Submit button
        self.click_button_xpath(button_xpath='//*[@name="submitLink"]')

    
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
            row = self.get_table_row((row_num+1))
            
            # Follow case link
            row.click()

            # Parse/store data
            data_dict = self.parse_data()
            self.store_data(data_dict)

            # Go back to previous page with other case elements
            self.back_page()
            time.sleep(0.1)


    def search_dates(self, start_date, end_date, status_filter=None):
        current_page_index = 1
        
        while True:
            self.enter_site()
            time.sleep(1)
            self.navigate_to_search_menu("Case Type Search")
            num_pages, current_page_index = self.search_date_page(start_date, current_page_index, status_filter, to_date=end_date)
            if current_page_index == num_pages:
                return
            else:
                current_page_index += 1


    def search_date(self, date, status_filter=None):
        current_page_index = 1
        
        while True:
            self.enter_site()
            time.sleep(1)
            self.navigate_to_search_menu("Case Type Search")          
            num_pages, current_page_index = self.search_date_page(date, current_page_index, status_filter)
            if current_page_index == num_pages:
                return
            else:
                current_page_index += 1


    def search_date_page(self, date, current_page_index=1, status_filter=None, to_date=None):
        # IMPORTANT: Can only run starting from "Case Type Search" menu (will return to this menu at function end)
        
        # If not search menu page, throw error and exit
        if not self.is_element_on_page('//span[text()="Case Type Search"]'):
            raise RuntimeError("The search_date method can only be run from the search page. Crawler must be navigated to that page before running (using 'enter_site', then 'navigate_to_search_menu')")
        # If not on the "Case Type Search" tab of the search menu, throw error and exit
        if 'selected' not in self.driver.find_element_by_xpath('//span[text()="Case Type Search"]/ancestor::li').get_attribute("class"):
            raise RuntimeError("The search_date method can only be run from the 'Case Type Search' tab. Crawler must be navigated to that tab before running (using 'navigate_to_search_menu)")

        self.set_search_options(status_filter)
        self.fill_dates_and_press(date, end_date=to_date)
        
        while self.is_element_on_page('//span[@class="feedbackPanelERROR"]'):
            self.set_search_options(status_filter)
            self.fill_dates_and_press(date, end_date=to_date)
            # errors = self.driver.find_elements_by_xpath('//span[@class="feedbackPanelERROR"]')

        num_pages = self.get_num_results_pages()
        print(num_pages)
        print(current_page_index)
        
        # Click on the page button for corresponding page number if we're looking for someting other than page 1
        if current_page_index > 1:
            self.click_button_xpath('//*[@title="Go to page {}"]'.format(current_page_index))
        
        self.scrape_page_results(current_page_index)

        return num_pages, current_page_index


    def search_case_number(self, case_number):
        # IMPORTANT: Can only run starting from "Case Number Search" menu (will return to this menu at function end)
        
        # If not search menu page, throw error and exit
        if not self.is_element_on_page('//span[text()="Case Number Search"]'):
            raise RuntimeError("The search_date method can only be run from the search page. Crawler must be navigated to that page before running (using 'enter_site', then 'navigate_to_search_menu')")
        # If not on the "Case Type Search" tab of the search menu, throw error and exit
        if 'selected' not in self.driver.find_element_by_xpath('//span[text()="Case Number Search"]/ancestor::li').get_attribute("class"):
            raise RuntimeError("The search_date method can only be run from the 'Case Number Search' tab. Crawler must be navigated to that tab before running (using 'navigate_to_search_menu)")

        self.fill_case_number_and_press(case_number)
        # Attempt again if error
        while self.is_element_on_page('//span[@class="feedbackPanelERROR"]'):
            self.fill_case_number_and_press(case_number)
        
        self.click_button_name(button_name=case_number)

        data_dict = self.parse_data()
        self.store_data(data_dict)

        self.click_button_name(button_name="Search")



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


    def parse_to_soup(self, page_source=None):
        if not page_source:
            page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        return soup


    def parse_data(self, page_source=None):
        soup = self.parse_to_soup(page_source)

        data_dict = {}

        # Case Name
        try:
            case_name = soup.find('div', attrs={'id': 'titleBar'}).find('h2').text.replace('\t', '').replace('\n', '').strip(' ')
        except:
            time.sleep(3)
            case_name = soup.find('div', attrs={'id': 'titleBar'}).find('h2').text.replace('\t', '').replace('\n', '').strip(' ')

        case_name = ' '.join(case_name.split())
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

        # Initialize all of these to prevent future key errors for rare (*very rare* exceptions)
        for field in ['Defendant Alias', 'Plaintiff Alias', 'Defendant Attorney', 'Defendant Attorney Address', \
                    'Defendant Attorney City', 'Defendant Attorney Phone', 'Plaintiff Attorney', 'Plaintiff Attorney Address', \
                    'Plaintiff Attorney City', 'Plaintiff Attorney Phone']:
            data_dict[field] = ''

        for row in rows:
            try:
                header = row.find_all('div',attrs={'class': 'subSectionHeader2'})[0]
                text = header.find_all('h5')[0].text.replace('\n','').replace('\t','')
            except:
                continue

            if text.split(' - ')[-1] == 'DEFENDANT':
                defendants.append(text.split(' - ')[0])

                try:
                    data_dict['Defendant Address'], data_dict['Defendant City'], data_dict['Defendant Zipcode'] = MuniCourtCrawler.get_address_info(row)
                except:
                    data_dict['Defendant Address'], data_dict['Defendant City'], data_dict['Defendant Zipcode']  = 'Address Error', 'Address Error', ''

                # Get Attorney Info
                data_dict['Defendant Attorney'], data_dict['Defendant Attorney Address'], \
                data_dict['Defendant Attorney City'], data_dict['Defendant Attorney Phone'], data_dict['Defendant Attorney Zipcode'] = MuniCourtCrawler.get_attorney_info(row)

                if row.find('h5', text="Alias").parent.find('dd', attrs={'class': 'ptyAfflName'}):
                    data_dict['Defendant Alias'] = row.find('h5', text="Alias").parent.find('dd', attrs={'class': 'ptyAfflName'}).text

            elif text.split(' - ')[-1] == 'PLAINTIFF':
                plaintiffs.append(text.split(' - ')[0])
                try:
                    data_dict['Plaintiff Address'], data_dict['Plaintiff City'], data_dict['Plaintiff Zipcode'] = MuniCourtCrawler.get_address_info(row)
                except:
                    data_dict['Plaintiff Address'], data_dict['Plaintiff City'], data_dict['Plaintiff Zipcode']  = 'Address Error', 'Address Error', ''
                
                # Get Attorney Info
                data_dict['Plaintiff Attorney'], data_dict['Plaintiff Attorney Address'], \
                data_dict['Plaintiff Attorney City'], data_dict['Plaintiff Attorney Phone'], data_dict['Plaintiff Attorney Zipcode'] = MuniCourtCrawler.get_attorney_info(row)

                if row.find('h5', text="Alias").parent.find('dd', attrs={'class': 'ptyAfflName'}):
                    data_dict['Plaintiff Alias'] = row.find('h5', text="Alias").parent.find('dd', attrs={'class': 'ptyAfflName'}).text

            elif text.split(' - ')[-1] == 'PROPERTY ADDRESS':
                try:
                    data_dict['Property Address'], data_dict['Property City'], data_dict['Property Zipcode'] = MuniCourtCrawler.get_address_info(row)
                except:
                    data_dict['Property Address'], data_dict['Property City'], data_dict['Property Zipcode'] = 'Address Error', 'Address Error', ''

        for field in [  'Property Address', 'Property City', 'Property Zipcode', 'Plaintiff Address',
                        'Plaintiff City', 'Plaintiff Zipcode', 'Defendant Address', 'Defendant City',
                        'Defendant Zipcode', 'Plaintiff Attorney', 'Plaintiff Attorney Address', 'Plaintiff Attorney City',
                        'Plaintiff Attorney Phone', 'Plaintiff Attorney Zipcode']:
            if field not in data_dict.keys():
                data_dict[field] = 'MISSING FROM RECORD'
        
        data_dict['Plaintiff'] = '; '.join(plaintiffs)
        data_dict['Defendants'] = '; '.join(defendants)

        # Events
        try:
            data_dict['Events'] = MuniCourtCrawler.process_event_data(soup)
        except AttributeError:
            data_dict['Events'] = []

        # Docket Information
        try:
            data_dict['Docket Information'] = MuniCourtCrawler.process_docket_data(soup)
        except AttributeError:
            data_dict['Docket Information'] = []

        # Costs
        costs_table = soup.find('div', attrs={'id':'financialInfo'}).find('table')
        data_dict['Costs'] = costs_table.find('tfoot').find_all('th',attrs={'class': 'currency'})[0].text

        # Disposition Status, Disposition Date
        disposition_table = soup.find('div', attrs={'id':'dispositionInfo'}).find('table').find('tbody')
        data_dict['Disposition Status'] = disposition_table.find_all('td')[0].text
        data_dict['Disposition Date'] = disposition_table.find_all('td')[-1].text

        # Prayer Amount
        data_dict['Prayer Amount'] = ''
        additional_fields_box = soup.find('div', attrs={'id': 'additionalFieldsInfo'})
        if additional_fields_box:
            prayer_amount_row = additional_fields_box.find('dt', text=re.compile("PRAYER AMOUNT*"))
            if prayer_amount_row:
                data_dict['Prayer Amount'] = prayer_amount_row.findNext('dd').text
        
        # Last Updated Time Stamp
        data_dict['Last Updated'] = datetime.strftime(datetime.today(), '%m/%d/%Y')

        return data_dict


    def store_data(self, data_dict, dump_source_file=True):
        case_number = data_dict['Case Number']

        if dump_source_file:
            self.dump_page_source_file(case_number)

        # NEW FIELDS HERE
        if self.outfile_format == 'csv':
            self.write_to_csv(data_dict)
        elif self.outfile_format == 'json':
            self.write_to_json(data_dict)


    def dump_page_source_file(self, case_number):
        date_string = datetime.today().strftime('%Y%m%d')

        try:
            # Keep record of scrape on specific date (as data will change)
            # with open(f'page_source_files/{date_string}/{case_number}.html', 'w') as f:
            #     f.write(self.driver.page_source)

            # Add or replace to store of all files
            with open(f'page_source_files/all_data/{case_number}.html', 'w') as f:
                f.write(self.driver.page_source)

        except FileNotFoundError:
            print('Directory Error')
            # os.mkdir(os.getcwd() + '/page_source_files/' + datetime.today().strftime('%Y%m%d'))
            # with open(f'page_source_files/{date_string}/{case_number}.html', 'w') as f:
            #     f.write(self.driver.page_source)


    def back_page(self):
        self.driver.back()


    def quit(self):
        self.driver.quit()


    def write_to_csv(self, data_dictionary):
        # If output file doesn't exist yet, create and add header. Otherwise, we're appending to an existing file
        csv_fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
                    'Defendants', 'Defendant Address', 'Defendant City', 'Defendant Zipcode', 'Property Address', 'Property City',
                    'Property Zipcode', 'Plaintiff', 'Plaintiff Address', 'Plaintiff City', 'Plaintiff Zipcode', 'Costs', 
                    'Disposition Status', 'Disposition Date', 'Defendant Alias', 'Plaintiff Alias', 'Defendant Attorney', 
                    'Defendant Attorney Address', 'Defendant Attorney City', 'Defendant Attorney Zipcode',
                    'Defendant Attorney Phone', 'Plaintiff Attorney', 'Plaintiff Attorney Address', 
                    'Plaintiff Attorney City', 'Plaintiff Attorney Zipcode', 'Plaintiff Attorney Phone', 'Prayer Amount', 'Last Updated']

        if os.path.isfile(self.outfile) == False:
            with open(self.outfile, 'w') as f:
                out_csv = csv.DictWriter(f, fieldnames=csv_fields)
                out_csv.writeheader()

        with open(self.outfile, 'a') as f:
            out_csv = csv.DictWriter(f, fieldnames=csv_fields)
            data_dictionary = {k:v for k,v in data_dictionary.items() if k in csv_fields}
            out_csv.writerow(data_dictionary)
    

    def write_to_json(self, data_dictionary):
        output_json = {
            'Case Name': data_dictionary['Case Name'],
            'Case Number': data_dictionary['Case Number'],
            'Case Status': data_dictionary['Case Status'],
            'File Date': data_dictionary['File Date'],
            'Action': data_dictionary['Action'],
            'Party Information': {
                'Plaintiff': {
                    'Name': data_dictionary['Plaintiff'],
                    'Address':  { 
                        'Street Address': data_dictionary['Plaintiff Address'],
                        'City': data_dictionary['Plaintiff City'],
                        'Zipcode': data_dictionary['Plaintiff Zipcode']
                    },
                    'Alias': data_dictionary['Plaintiff Alias']
                },
                'Defendant(s)': {
                    'Name': data_dictionary['Defendants'],
                    'Address': { 
                        'Street Address': data_dictionary['Defendant Address'],
                        'City': data_dictionary['Defendant City'],
                        'Zipcode': data_dictionary['Defendant Zipcode']
                    },
                    'Alias': data_dictionary['Defendant Alias']
                },
                'Plaintiff Attorney': {
                    'Name': data_dictionary['Plaintiff Attorney'],
                    'Address':  { 
                        'Street Address': data_dictionary['Plaintiff Attorney Address'],
                        'City': data_dictionary['Plaintiff Attorney City'],
                        'Zipcode': data_dictionary['Plaintiff Attorney Zipcode']
                    },
                    'Phone': data_dictionary['Plaintiff Attorney Phone']
                },
                'Defendant Attorney': {
                    'Name': data_dictionary['Defendant Attorney'],
                    'Address':  { 
                        'Street Address': data_dictionary['Defendant Attorney Address'],
                        'City': data_dictionary['Defendant Attorney City'],
                        'Zipcode': data_dictionary['Defendant Attorney Zipcode']
                    },
                    'Phone': data_dictionary['Defendant Attorney Phone']
                }
            },
            'Property Address': {
                'Street Address': data_dictionary['Property Address'],
                'City': data_dictionary['Property City'],
                'Zipcode': data_dictionary['Property Zipcode']
            },
            'Events': data_dictionary['Events'],
            'Docket Information': data_dictionary['Docket Information'],
            'Prayer Amount': data_dictionary['Prayer Amount'],
            'Disposition': {
                'Disposition Status': data_dictionary['Disposition Status'],
                'Disposition Date': data_dictionary['Disposition Date']
            },
            'Total Costs': data_dictionary['Costs'],
            'Last Updated': data_dictionary['Last Updated']
        }
        
        self.case_dict[data_dictionary['Case Number']] = output_json
        return output_json


    @staticmethod
    def get_address_info(row):
        contact_data = row.find('div', attrs={'class': 'box ptyContact'})
        address = contact_data.find('dl').find('dd')
        address_line_1 = address.find('div', attrs={'class': 'addrLn1'}).text
        # address_line_2 = address.find('div', attrs={'class': 'addrLn2'}).text

        try:
            city = address.find_all('span')[0].text.title() + ', ' + address.find_all('span')[1].text
        except:
            city = 'Cleveland, OH'
        
        try:
            zipcode = address.find_all('span')[2].text.strip()
        except:
            zipcode = ''
        
        return ' '.join(address_line_1.split()), city.strip(), zipcode
    

    @staticmethod
    def get_attorney_info(row):
        attorney_data_div = row.find('h5', text='Party Attorney').parent.find('div')
        if not attorney_data_div:
            return '', '', '', '', ''
        
        # Attorney Name
        attorney_name = attorney_data_div.find('dt', text=re.compile("Attorney*")).findNext('dd').text

        full_address_element = attorney_data_div.find('dt', text=re.compile('Address*')).findNext('dd')
        
        # Attorney Address
        try:
            line1 = full_address_element.find('div', attrs={'class':'addrLn1'}).text.strip()
            line2 = full_address_element.find('div', attrs={'class':'addrLn2'}).text.strip()
            line3 = full_address_element.find('div', attrs={'class':'addrLn3'}).text.strip()

            attorney_address = line1
            for line in [line2, line3]:
                if line != '':
                    attorney_address += '\n' + line
        except AttributeError:
            attorney_address = ''

        # Attorney City
        city_spans = full_address_element.find_all('span')
        attorney_city = ', '.join([x.text.strip() for x in city_spans[:2]])

        # Attroney Zipcode
        try:
            attorney_zipcode = city_spans[2].text.strip()
        except:
            attorney_zipcode = ''

        # Attorney Phone
        attorney_phone = attorney_data_div.find('dt', text=re.compile('Phone*')).findNext('dd').text

        if not MuniCourtCrawler.is_int(attorney_phone.replace('(', '').replace(')','').replace('-','').replace(' ','')):
            attorney_phone = ''

        return attorney_name, attorney_address, attorney_city, attorney_phone, attorney_zipcode
    
    @staticmethod
    def process_event_data(soup):
        all_event_data = []

        events_table = soup.find('h4', text='Events').parent.parent.table
        events = events_table.find('tbody').find_all('tr')
        for event in events:
            fields = event.find_all('td')

            event_data = {
                'Event Date': fields[0].text,
                'Event Type': fields[2].text,
                'Event Result': fields[3].text
            }

            all_event_data.append(event_data)
        
        return all_event_data
    

    @staticmethod
    def process_docket_data(soup):
        all_docket_data = []

        docket_table = soup.find('h4', text='Docket Information').parent.parent.table
        docket_items = docket_table.find('tbody').find_all('tr')
        for docket_item in docket_items:
            fields = docket_item.find_all('td')

            docket_data = {
                'Docket Item Date': fields[0].text,
                'Docket Item Text': fields[1].text,
                'Docket Item Amount Owed': fields[2].text
            }

            all_docket_data.append(docket_data)
        
        return all_docket_data
        

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
    # try:
    #     os.mkdir(os.getcwd() + '/page_source_files/' + datetime.today().strftime('%Y%m%d'))
    # except FileExistsError:
    #     pass

    # Create directory (if it doesn't exist) within page_source_files to store all most up-to-date source files for given cases
    try:
        os.mkdir(os.getcwd() + '/page_source_files/all_data')
    except FileExistsError:
        pass
