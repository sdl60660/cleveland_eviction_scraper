
from municourts import MuniCourtCrawler, create_page_source_directories

import time
from datetime import datetime
import sys


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
			print('Date Search Error')
			error_count += 1
			time.sleep(2)
		
		if error_count > 5: 
			break
		
if __name__ == "__main__":
	if len(sys.argv) != 4:
		print('USAGE: python scrape_date_range.py [start_date] [end_date] [filename]')
		sys.exit(0)

	start_string = sys.argv[1]
	end_string = sys.argv[2]
	filename = sys.argv[3]

	start_date = datetime.strptime(start_string, '%m/%d/%Y')
	end_date = datetime.strptime(end_string, '%m/%d/%Y')

	# Create any necessary directories to store page source files
	create_page_source_directories()

	main(start_date, end_date, filename)