
import json
import csv

import time
import sys
import os
from datetime import datetime, timedelta

from municourts import MuniCourtCrawler, create_page_source_directories
import scrape_date_range


def get_data_array(datafile):
	with open(datafile, 'r') as f:
		if os.path.splitext(existing_data_path)[1] == '.json':
			data = json.load(f)
		else:
			data = [x for x in csv.DictReader(f)]
	
	return data


def parse_existing_data(existing_data_path):
	data = get_data_array(existing_data_path)
	
	open_case_numbers = [x['Case Number'] for x in data if x['Case Status'] == 'OPEN']
	
	case_dates = [x['File Date'] for x in data]
	last_date = max(case_dates, key=lambda x: datetime.strptime(x, '%m/%d/%Y'))

	return open_case_numbers, last_date


def main(existing_data_path, outfile_path):
	if os.path.splitext(existing_data_path)[1] != os.path.splitext(outfile_path)[1]:
		raise ValueError("Data may output in either CSV or JSON, but the format of the existing datafile and the output file must match. You've provided different file types.")

	# Get array of all open cases (to update) and find last date in existing data (for start date of new data)
	open_cases, file_end_date = parse_existing_data(existing_data_path)
	print(len(open_cases), file_end_date)

	# Start gathering new data from ten days before last day in existing data, since cases seem to sometimes be added
	# retroactively (not usually this far back, but better to be safe). End date is just today.
	start_date = datetime.strptime(file_end_date, '%m/%d/%Y') - timedelta(days=10)
	end_date = datetime.today()

	# Run a date range call from the scrape_date_range file and save into output file, which will then be updated with
	scrape_date_range.date_range_crawl(start_date, end_date, outfile_path)

	# Start up new crawler to pull updated data on all cases that were open on last update
	crawler = MuniCourtCrawler(outfile_path, headless=True)
	crawler.enter_site()

	error_count = 0
	for i, case_number in enumerate(open_cases):
		print(i, case_number)

		try:
			crawler.navigate_to_search_menu("Case Number Search")
			crawler.search_case_number(case_number)
		except:
			print('Case Number Search Error')
			error_count += 1

			time.sleep(2)
			crawler.enter_site()
			
		if error_count > 5: 
			break
	
	# The dump_case_dict() method will automatically concatenate with existing file, meaning this is automatically incorporating
	# data from the date crawl at the beginning. If data format is CSV, it's appending by default, so the same thing applies.
	if crawler.outfile_format == "json":
		crawler.dump_case_dict()

		# Update the existing full datafile with new/updated data
		new_updated_data = { x['Case Number']: x for x in get_data_array(outfile_path) }
		existing_data = { x['Case Number']: x for x in get_data_array(existing_data_path) }

		# (Use in future, when whole project is kosher for python 3.9+)
		# existing_data |= new_updated_data
		existing_data.update(new_updated_data)

		
		with open(existing_data_path, 'w') as f:
			json.dump(list(existing_data.values()), f)

	else:
		new_updated_data = get_data_array(outfile_path)

		with open(existing_data_path, 'a') as f:
			out_csv = csv.DictWriter(f, fieldnames=list(new_updated_data[0].keys()))
			for row in new_updated_data:
				out_csv.writerow()


	# Tear down crawler
	crawler.quit()

		
if __name__ == "__main__":
	if len(sys.argv) < 2 or len(sys.argv) > 3:
		print('USAGE: python update_data.py [existing_data_filepath] [OPTIONAL: outdata_filepath]')
		sys.exit(1)

	existing_data_path = sys.argv[1]

	try:
		outfile_path = sys.argv[2]
	except IndexError:
		file_extension = os.path.splitext(existing_data_path)[1]
		date_string = datetime.strftime(datetime.now(), '%m-%d-%Y %H:%M')

		outfile_path = f'data/updates/data_update_({date_string}){file_extension}'
	
	# Create any necessary directories to store page source files
	create_page_source_directories()

	main(existing_data_path, outfile_path)