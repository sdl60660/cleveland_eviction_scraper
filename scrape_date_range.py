
from municourts import MuniCourtCrawler, create_page_source_directories

import time
from datetime import datetime, timedelta
import sys
import os


def date_range_crawl(start_date, end_date, outfile_path):	
	crawler = MuniCourtCrawler(outfile_path, headless=True)
	date = start_date

	while date.date() != end_date.date():
		for attempt in range(3):
			try:
				crawler.search_date(date, status_filter=None)
				date += timedelta(days=1)
				break
			except:
				print('Date Search Error on attempt {}'.format(attempt))
				time.sleep(2)
	
	if crawler.outfile_format == "json":
		crawler.dump_case_dict()
	
	crawler.quit()

		
if __name__ == "__main__":
	if len(sys.argv) != 4:
		print('USAGE: python scrape_date_range.py [start_date] [end_date] [filename]')
		sys.exit(1)

	start_string = sys.argv[1]
	end_string = sys.argv[2]
	filename = sys.argv[3]

	start_date = datetime.strptime(start_string, '%m/%d/%Y')
	end_date = datetime.strptime(end_string, '%m/%d/%Y')

	# Create any necessary directories to store page source files
	create_page_source_directories()

	date_range_crawl(start_date, end_date, filename)