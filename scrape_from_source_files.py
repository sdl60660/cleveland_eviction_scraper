
from municourts import MuniCourtCrawler, create_page_source_directories

from datetime import datetime
import sys
import os


def main(page_source_directory, outfile_path):	
    crawler = MuniCourtCrawler(outfile_path, headless=True)
    
    if os.path.splitext(outfile_path)[1] == '.json':
        crawler.outfile_format = 'json'
        crawler.set_case_dict()
    
    for html_file in os.listdir(page_source_directory):
        print(html_file)

        # Open Existing Scraped HTML File
        with open((page_source_directory.strip('/') + '/' + html_file)) as f:
            file_data = f.read()

            # Parse File
            data_dict = crawler.parse_data(page_source=file_data)

            # Store Date
            crawler.store_data(data_dict, dump_source_file=False)
    
    if os.path.splitext(outfile_path)[1] == '.json':
        crawler.dump_case_dict()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('USAGE: python scrape_open_cases.py [page_source_file_directory] [outfile]')
        sys.exit(0)
    
    page_source_directory = sys.argv[1]
    outfile = sys.argv[2]
    
    main(page_source_directory, outfile)