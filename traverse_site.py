
from municourts import MuniCourtCrawler

import time
from datetime import datetime
import sys
import os


def main(start_date, end_date, outfile_path):	
	date = start_date
	crawler = MuniCourtCrawler(outfile_path, headless=True)
	current_page_index = 1

	error_count = 0

	while date != end_date:
		try:
			crawler.enter_site()
			crawler.navigate_to_search_menu("Case Type Search")
			date, current_page_index = crawler.search_date(date, current_page_index)
		except:
			# crawler.quit()
			# crawler.enter_site()
			# crawler.navigate_to_search_menu("Case Type Search")
			print('Date Search Error')
			error_count += 1
			time.sleep(2)
		
		if error_count > 5: 
			break
		
if __name__ == "__main__":
	if len(sys.argv) != 4:
		print('USAGE: python traverse_site.py [start_date] [end_date] [filename]')
		sys.exit(0)

	start_string = sys.argv[1]
	end_string = sys.argv[2]
	filename = sys.argv[3]

	start_date = datetime.strptime(start_string, '%m/%d/%Y')
	end_date = datetime.strptime(end_string, '%m/%d/%Y')

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

	main(start_date, end_date, filename)