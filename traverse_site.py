import municourts
from municourts import MuniCourtTracker

from captcha.recaptcha_v2 import RecaptchaV2

import time
from datetime import datetime, timedelta
import sys
import csv
import os


def is_int(a):
	try:
		return int(a)
	except ValueError:
		return False

if len(sys.argv) != 4:
	print('USAGE: python traverse_site.py [start_date] [end_date] [filename]')
	sys.exit(0)


start_string = sys.argv[1]
end_string = sys.argv[2]
filename = sys.argv[3]

START_DATE = datetime.strptime(start_string, '%m/%d/%Y')
END_DATE = datetime.strptime(end_string, '%m/%d/%Y')

try:
	os.mkdir(os.getcwd() + '/page_source_files/' + datetime.today().strftime('%Y%m%d'))
except FileExistsError:
	pass


# If output file doesn't exist yet, create and add header. Otherwise, we're appending to an existing file
if os.path.isfile(filename) == False:
	with open(filename, 'w') as f:
		fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
		'Defendants', 'Property Address', 'Property City',
		'Plaintiff', 'Plaintiff Address', 'Plaintiff City',
		'Costs', 'Disposition Status', 'Disposition Date']
		out_csv = csv.DictWriter(f, fieldnames=fields)
		out_csv.writeheader()

def start_up(tracker):
	time.sleep(2)

	# Hard-coded selection for 'Number of Results'
	tracker.click_button_xpath(button_xpath='//*[@name="bodyLayout:topSearchPanel:pageSize"]/option[@value="2"]')
	# Hard-coded selection for 'Case Type': "CVG - LANDLORD/TENANT" (Pre-select, this needs to be "clicked" twice)
	tracker.click_button_xpath(button_xpath='//*[@name="caseCd"]/option[7]')

	# tracker.click_button_xpath(button_xpath='//*[@name="ptyCd"]/option[12]')
	# tracker.click_button_xpath(button_xpath='//*[@id="id22"]/option[@value="2"]')
	time.sleep(0.5)

	# Hard-coded selection for 'Case Type': "CVG - LANDLORD/TENANT"
	tracker.click_button_xpath(button_xpath='//*[@name="caseCd"]/option[7]')
	# time.sleep(0.5)

	# Hard-coded selection for 'Party Type'
	for x in range(2):
		tracker.scroll_to_element(element_xpath='//*[@name="ptyCd"]/option[12]')
		time.sleep(0.5)


def fill_dates_and_press(tracker, date_string):
	# Fill Start Date box
	tracker.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:beginDate"]', text=date_string)
	time.sleep(0.2)

	# Fill End Date box
	tracker.fill_box(element_id=None, element_xpath='//*[@name="fileDateRange:endDate"]', text=date_string)

	# Press Submit button
	tracker.click_button_xpath(button_xpath='//*[@name="submitLink"]')
	#tracker.wait_until_loaded('//*[@id="grid"]/tbody/tr//a')


def scrape_page_results(tracker, current_page):
	# Find case elements on the page
	try:
		rows = tracker.get_num_table_rows()
	except:
		time.sleep(2)
		rows = tracker.get_num_table_rows()
	
	rows = min(40, rows - (40 * (current_page - 1)))
	
	# For each case element
	for row_num in range(rows):
		try:
			row = tracker.get_table_row((row_num+1))
			# print('row', row)
			# Follow case link
			row.click()
		except:
			time.sleep(1)
			try:
				row = tracker.get_table_row((row_num+1))
				print('row backup', row)
				# Follow case link
				row.click()
			except IndexError:
				print('error')
				time.sleep(1)
				break

		time.sleep(2)

		# Parse/store data
		tracker.store_data(filename)

		# Go back to previous page with other case elements
		tracker.back_page()
		time.sleep(1)


def main():	
	date = START_DATE
	tracker = MuniCourtTracker()
	current_page_index = 1
	
	# captcha = RecaptchaV2()
	# captcha.solve(tracker.driver, sitekey, apikey)

	while date != END_DATE:
		time.sleep(1)
		date_string = datetime.strftime(date, '%m/%d/%Y')
		print(date_string)

		try:
			start_up(tracker)
			fill_dates_and_press(tracker, date_string)
		except:
			tracker.quit()
			tracker = MuniCourtTracker()
			time.sleep(2)
			start_up(tracker)
			fill_dates_and_press(tracker, date_string)
		
		errors = tracker.driver.find_elements_by_xpath('//*[@id="id3b"]/ul/li/span[@class="feedbackPanelERROR"]')
		while len(errors) > 0:
			start_up(tracker)
			tracker.click_button_xpath(button_xpath='//*[@id="id3a"]')
			errors = tracker.driver.find_elements_by_xpath('//*[@id="id3b"]/ul/li/span[@class="feedbackPanelERROR"]')

		# Split the result string, which will either be in the format "Displaying 100 of ___ total matches." if > 100 or "Displaying all ___ matches." if <= 100
		# Find the last integer in the string, which should be the total number of results from the date

		try:
			total_results = [int(x) for x in tracker.driver.find_element_by_id("srchResultNotice").text.split(" ") if is_int(x)][-1]
		except:
			total_results = 0


		if total_results > 100:
			# print("LONG DAY", date)
			# date += datetime.timedelta(days=1)
			# continue

			# Round down for now
			total_results = 100

		# CourtView will display a max of three pages of results and a max of 100 items, so find how many pages we'd expect from the results.
		# If there are more than 100 results for the selected date, we have a small problem that we can work on later
		# There are 40 results to a page, so floor divide by 40 (and add one)
		num_pages = min(3, ((total_results // 41) + 1))
		print(num_pages)

		if num_pages == 1:
			scrape_page_results(tracker, current_page_index)
			tracker.back_page()
			date += timedelta(days=1)
		else:
			print(current_page_index)
			tracker.click_button_xpath('//*[@title="Go to page {}"]'.format(current_page_index))
			scrape_page_results(tracker, current_page_index)

			if current_page_index == num_pages:
				current_page_index = 1
				tracker.back_page()
				time.sleep(1)
				date += timedelta(days=1)
			else:
				current_page_index += 1
				tracker.back_page()
				time.sleep(0.2)
				tracker.back_page()

		# tracker.back_page()
		# Return to search page and increment date
		# tracker.driver.get("")
		

main()