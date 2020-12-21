
import json
import csv

import time
import sys
import os
from datetime import datetime, timedelta

from municourts import MuniCourtCrawler, create_page_source_directories
from utils import get_year_range, OrderedCounter
import scrape_date_range


def get_data_array(datafile):
	with open(datafile, 'r') as f:
		if os.path.splitext(existing_data_path)[1] == '.json':
			data = json.load(f)
		else:
			data = [x for x in csv.DictReader(f)]
	
	return data


def parse_existing_data(data):
	case_dates = [x['File Date'] for x in data]
	last_date = max(case_dates, key=lambda x: datetime.strptime(x, '%m/%d/%Y'))

	return last_date


def get_chunk_date_range(next_start_date, year_counter, counter_keys, max_chunk_size):
	start_date = end_date = next_start_date
	
	# num_records will need to remain <= 100. Initialize it with the number of records on the start date.
	num_records = year_counter[start_date]
	remaining_dates = counter_keys[counter_keys.index(start_date)+1:]

	# Iterate through each date remaining in the date list (days with open cases on the given year)
	# When the number of records exceeds 100, break, with the date before that as the last date in the chunk's date range
	for remaining_date in remaining_dates:
		if num_records + year_counter[remaining_date] > max_chunk_size:
			break
		else:
			num_records += year_counter[remaining_date]
			end_date = remaining_date
	
	return start_date, end_date, num_records


def update_open_cases(outfile_path, data, case_status):
	# Get array of all open/re-open cases (to update)
	open_cases = [x for x in data if x['Case Status'] == case_status]

	# case_dates = list(set([x['File Date'] for x in open_cases]))
	case_dates = sorted([datetime.strptime(x['File Date'], '%m/%d/%Y') for x in open_cases])
	print(case_status, len(open_cases))

	# Start up new crawler to pull updated data on all cases that were open on last update
	crawler = MuniCourtCrawler(outfile_path, headless=True)		

	# Find all years with open case dates
	case_years = sorted(list(set([int(x.year) for x in case_dates])))

	# Iterate through each year and find date ranges with <= 100 open records to search/retrieve records
	max_chunk_size = 100
	for record_year in case_years:
		# Only cases in the specified year
		subset = [x for x in case_dates if int(x.year) == record_year]
		print(record_year, len(subset))

		# Get a count of the cases by each date
		year_counter = OrderedCounter(subset)
		counter_keys = list(year_counter.keys())

		next_start_date = counter_keys[0]
	
		# Work our way through the date list, creating chunks with <= 100 records for a search
		while True:
			# Find a date range chunk
			start_date, end_date, num_records = get_chunk_date_range(next_start_date, year_counter, counter_keys, max_chunk_size)
			
			# Crawl this date range, storing records on crawler object
			# crawler.search_dates(start_date, end_date, status_filter=case_status)
			max_attempts = 3
			for attempt in range(max_attempts):
				try:
					crawler.search_dates(start_date, end_date, status_filter=case_status)
					break
				except:
					print(f'Date Search Error on attempt {attempt+1} of {max_attempts}. These happen rarely and unpredictably due to selenium misfires.')
					time.sleep(2)
			
			# If we're at the end of the list, break and start the next year's dates
			if end_date == counter_keys[-1]:
				break
			else:
				next_start_date = counter_keys[(counter_keys.index(end_date) + 1)]
			
	# The dump_case_dict() method will automatically concatenate with existing file, meaning this is automatically incorporating
	# data from the date crawl at the beginning. If data format is CSV, it's appending by default, so the same thing applies.
	if crawler.outfile_format == "json":
		crawler.dump_case_dict()
	
	# Tear down crawler
	crawler.quit()


def find_and_update_reopened_cases(outfile_path, existing_data_path, data):
	crawler = MuniCourtCrawler(outfile_path, headless=True)

	start_year, end_year = get_year_range(existing_data_path)
	for record_year in range(start_year, end_year+1):
		start_date = datetime(year=record_year, month=1, day=1)
		end_date = datetime(year=record_year, month=12, day=31)

		crawler.search_dates(start_date, end_date, status_filter="REOPEN (RO)")
	
	# The dump_case_dict() method will automatically concatenate with existing file, meaning this is automatically incorporating
	# data from the date crawl at the beginning. If data format is CSV, it's appending by default, so the same thing applies.
	if crawler.outfile_format == "json":
		crawler.dump_case_dict()
	
	# Tear down crawler
	crawler.quit()


def concatenate_and_dump_data(outfile_path, existing_data_path):
	if os.path.splitext(outfile_path)[1] == '.json':
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


def main(existing_data_path, outfile_path):
	if os.path.splitext(existing_data_path)[1] != os.path.splitext(outfile_path)[1]:
		raise ValueError("Data may output in either CSV or JSON, but the format of the existing datafile and the output file must match. You've provided different file types.")

	# Parse file, regardless of format, and return data array
	data = get_data_array(existing_data_path)

	# Find last date in existing data (for start date of new data)
	file_end_date = parse_existing_data(data)
	# print(file_end_date)

	# Start gathering new data from ten days before last day in existing data, since cases seem to sometimes be added
	# retroactively (not usually this far back, but better to be safe). End date is just today.
	start_date = datetime.strptime(file_end_date, '%m/%d/%Y') - timedelta(days=10)
	end_date = datetime.today()

	# Run a date range call from the scrape_date_range file and save into output file, which will then be updated with
	scrape_date_range.date_range_crawl(start_date, end_date, outfile_path)

	# Run over all dates with open cases with a date search (this is faster than search each case by case number)
	# We'll also update cases that we *know* are re-opened as of the last update and that may have closed since...
	# but we'll need to do a separate search for cases that have been re-opened since last update.
	for case_status in ['OPEN', "REOPEN (RO)"]:
		update_open_cases(outfile_path, data, case_status)

	# Find and update any re-opened cases. We'll use a date range serach and just search by year since there would never be more than 100 re-opened cases in a year
	find_and_update_reopened_cases(outfile_path, existing_data_path, data)

	# Combine updated/new case data with existing data and dump into full data file
	concatenate_and_dump_data(outfile_path, existing_data_path)

		
if __name__ == "__main__":
	if len(sys.argv) < 2 or len(sys.argv) > 3:
		print('USAGE: python update_data.py [existing_data_filepath] [OPTIONAL: outdata_filepath]')
		sys.exit(1)

	existing_data_path = sys.argv[1]

	try:
		outfile_path = sys.argv[2]
	except IndexError:
		file_extension = os.path.splitext(existing_data_path)[1]
		date_string = datetime.strftime(datetime.now(), '%m-%d-%Y')

		outfile_path = f'data/updates/data_update_({date_string}){file_extension}'
	
	# Create any necessary directories to store page source files
	create_page_source_directories()

	main(existing_data_path, outfile_path)