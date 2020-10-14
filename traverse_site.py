import municourts
from municourts import MuniCourtTracker

from captcha.recaptcha_v2 import RecaptchaV2

import time
import datetime
import sys
import csv

if len(sys.argv) != 4:
	print('USAGE: python traverse_site.py [start_date] [end_date] [filename]')
	sys.exit(0)

start_string = sys.argv[1]
end_string = sys.argv[2]

filename = sys.argv[3]

START_DATE = datetime.datetime.strptime(start_string, '%m/%d/%Y')
END_DATE = datetime.datetime.strptime(end_string, '%m/%d/%Y')

"""
with open(filename, 'w') as f:
	fields = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
	'Defendants', 'Property Address', 'Property City',
	'Plaintiff', 'Plaintiff Address', 'Plaintiff City',
	'Costs', 'Disposition Status', 'Disposition Date']
	out_csv = csv.DictWriter(f, fieldnames=fields)
	out_csv.writeheader()
"""

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

def main():	
	date = START_DATE
	tracker = MuniCourtTracker()
	
	# captcha = RecaptchaV2()
	# captcha.solve(tracker.driver, sitekey, apikey)

	while date != END_DATE:
		time.sleep(2)
		date_string = datetime.datetime.strftime(date, '%m/%d/%Y')
		print(date_string)

		# try:
		start_up(tracker)
		fill_dates_and_press(tracker, date_string)
		# except:
			# tracker.quit()
			# tracker = MuniCourtTracker()
			# time.sleep(2)
			# start_up(tracker)
			# fill_dates_and_press(tracker, date_string)
		
		errors = tracker.driver.find_elements_by_xpath('//*[@id="id3b"]/ul/li/span[@class="feedbackPanelERROR"]')
		while len(errors) > 0:
			start_up(tracker)
			tracker.click_button_xpath(button_xpath='//*[@id="id3a"]')
			errors = tracker.driver.find_elements_by_xpath('//*[@id="id3b"]/ul/li/span[@class="feedbackPanelERROR"]')

		# Find case elements on the page
		try:
			rows = tracker.get_num_table_rows()
		except:
			time.sleep(2)
			rows = tracker.get_num_table_rows()
		print(rows)
		
		# For each case element
		for row_num in range(rows):
			try:
				row = tracker.get_table_row((row_num+1))
				# Follow case link
				row.click()
			except:
				time.sleep(2)
				try:
					row = tracker.get_table_row((row_num+1))
					# Follow case link
					row.click()
				except IndexError:
					time.sleep(1)
					break

			time.sleep(1)

			# Parse/store data
			tracker.store_data(filename)

			# Go back to previous page with other case elements
			tracker.back_page()

		tracker.back_page()
		date += datetime.timedelta(days=1)

main()