# 2017 data on evictions

from bs4 import BeautifulSoup
import requests

import csv, json
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

START_PAGE = 'https://clevelandmunicipalcourt.org/public-access'

class MuniCourtTracker():

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.driver.get(START_PAGE)
        self.driver.implicitly_wait(2)

        # Get to search page
        for button in ["   I Accept   ", "Click Here", "Case Type Search"]:
            try:
                self.click_button_name(button_name=button)
                time.sleep(1)
            except:
                time.sleep(10)
                self.click_button_name(button_name=button)

    def __repr__(self):
        return ('<Selenium Driver for CLE Municipal Courts. Current Page: {}>'.format(str(self.driver.current_url)))

    def click_button_name(self, button_name):
        button = self.driver.find_element_by_link_text(button_name).click()

    def click_button_xpath(self, button_xpath):
        button = self.driver.find_element_by_xpath(button_xpath).click()

    def scroll_to_element(self, element_xpath):
        element = self.driver.find_element_by_xpath(element_xpath)
        actions = ActionChains(self.driver)
        actions.move_to_element(element)
        actions.click()
        actions.perform()

    def fill_box(self, element_id, text):
        self.driver.find_element_by_id(element_id).clear()
        element = self.driver.find_element_by_id(element_id)
        element.send_keys(text)

    def get_num_table_rows(self):
        text = self.driver.find_elements_by_xpath('*//div[@id="srchResultNotice"]')
        if len(text) == 0:
            return 0
        else:
            num_rows = int(text[0].text.split(' ')[2])
            return num_rows

    def get_table_row(self, num):
        return self.driver.find_elements_by_xpath('//*[@id="grid"]/tbody/tr[{}]//a'.format(num))[0]

    def search_records(self):
        pass

    def parse_to_soup(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

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


    def store_data(self, filename):
        soup = self.parse_to_soup()

        csv_dict = {}

        # Case Name
        case_name = self.driver.find_elements_by_xpath('*//div[@id="titleBar"]//h2')[0].text.replace('\t', '').replace('\n', '').strip(' ')
        csv_dict['Case Name'] = case_name

        # Case Number
        case_number = ' '.join(case_name.split(' ')[:3])
        csv_dict['Case Number'] = case_number

        # Case Status, File Date, Action
        table = soup.find('table')
        cells = table.find_all('td')

        for cell in cells:
            data = cell.find_all('dd')
            title = cell.find_all('dt')

            if len(title) == 1:
                for field in {'Case Status', 'File Date', 'Action'}:
                    if field in title[0].text:
                        csv_dict[field] = data[0].text

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
                    csv_dict['Plaintiff Address'], csv_dict['Plaintiff City'] = MuniCourtTracker.get_address_info(row)
                except:
                    csv_dict['Plaintiff Address'], csv_dict['Plaintiff City'] = 'Address Error', 'Address Error'

            elif text.split(' - ')[1] == 'PROPERTY ADDRESS':
                try:
                    csv_dict['Property Address'], csv_dict['Property City'] = MuniCourtTracker.get_address_info(row)
                except:
                    csv_dict['Plaintiff Address'], csv_dict['Plaintiff City'] = 'Address Error', 'Address Error'

        csv_dict['Plaintiff'] = '; '.join(plaintiffs)
        csv_dict['Defendants'] = '; '.join(defendants)

        # Costs
        costs_table = soup.find('div', attrs={'id':'financialInfo'}).find('table')
        # try:
        csv_dict['Costs'] = costs_table.find('tfoot').find_all('th',attrs={'class': 'currency'})[0].text
        # except:
            # csv_dict['Costs'] = ''


        # Disposition Status, Disposition Date

        disposition_table = soup.find('div', attrs={'id':'dispositionInfo'}).find('table').find('tbody')
        csv_dict['Disposition Status'] = disposition_table.find_all('td')[0].text
        csv_dict['Disposition Date'] = disposition_table.find_all('td')[-1].text


        # NEW FIELDS HERE

        MuniCourtTracker.write_to_csv(filename, csv_dict)

    @staticmethod
    def write_to_csv(filename, dictionary):
        with open(filename, 'a') as f:
            fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
                      'Defendants', 'Property Address', 'Property City',
                      'Plaintiff', 'Plaintiff Address', 'Plaintiff City',
                      'Costs', 'Disposition Status', 'Disposition Date']
                      # NEW FIELDS HERE
            out_csv = csv.DictWriter(f, fieldnames=fields)
            out_csv.writerow(dictionary)

    def back_page(self):
        self.driver.execute_script("window.history.go(-1)")

    def quit(self):
        self.driver.quit()
