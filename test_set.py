import scrape_date_range
import scrape_from_source_files
# import scrape_open_cases

import os
import csv
import json
from datetime import datetime

from municourts import MuniCourtCrawler

# ======================================================== #
# ============ Test cases to be run by pytest ============ #
# ======================================================== #


def test_enter_site_solve_captcha():
    crawler = MuniCourtCrawler(output_file='test_data/dummy_file.json', headless=True)

    # Clear cookies
    crawler.cookies = []

    # Run enter_site(), which clicks 'Accept' button, solves captcha and clicks 'Click Here' button to get to search page
    crawler.enter_site()
    
    # If we've successfully gotten through the captcha (and clicked the next button, which should be trivial),
    # the "Search" header should exist on the page. Obviously if they change the layout of this page, this test will fail, 
    # but if they do that, things will need to change anyway. 
    assert crawler.is_element_on_page('//div[@class="sectionHeader"]/h2[text()="Search"]')


def test_parser():
    test_fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action', 'Property Address']
    crawler = MuniCourtCrawler(output_file='test_data/dummy_file.json', headless=True)

    with open('test_data/test_source_file.html', 'r') as f:
        file_data = f.read()
        data_dict = crawler.parse_data(page_source=file_data)
        test_data = crawler.write_to_json(data_dict)
    
    with open('test_data/true_source_file_output.json', 'r') as f:
        true_data = json.load(f)
    
    assert all([test_data[field] == true_data[field] for field in test_fields])


def test_general_date_crawler_json():
    start_date = datetime.strptime('01/14/2011', '%m/%d/%Y')
    end_date = datetime.strptime('01/16/2011', '%m/%d/%Y')
    
    test_file = 'sample_test.json'

    scrape_date_range.date_range_crawl(start_date, end_date, test_file)
    
    with open(test_file, 'r') as f:
        data = json.load(f)
    
    os.remove(test_file)
    assert len(data) == 53
    

def test_general_date_crawler_csv():
    start_date = datetime.strptime('01/14/2011', '%m/%d/%Y')
    end_date = datetime.strptime('01/16/2011', '%m/%d/%Y')
    
    test_file = 'sample_test.csv'

    scrape_date_range.date_range_crawl(start_date, end_date, test_file)
    
    with open(test_file, 'r') as f:
        data = [x for x in csv.DictReader(f)]

    os.remove(test_file)
    assert len(data) == 53


# Design some test for the update_data function using some dummy data (existing file with three or four entries, some of which should update)