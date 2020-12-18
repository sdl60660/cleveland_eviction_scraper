
from municourts import MuniCourtCrawler, create_page_source_directories

from datetime import datetime
import sys
import os


ERROR_FILE_CONTENT = '<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body></body></html>'


def main(page_source_directory, outfile_path):	
    crawler = MuniCourtCrawler(outfile_path, headless=True)
    
    if os.path.splitext(outfile_path)[1] == '.json':
        crawler.outfile_format = 'json'
        crawler.set_case_dict()
    
    errors = []
    
    for i, html_file in enumerate(os.listdir(page_source_directory)):
        if not html_file.endswith('.html'):
            continue

        print(i, html_file)

        # Open Existing Scraped HTML File
        with open((page_source_directory.strip('/') + '/' + html_file), 'r') as f:
            file_data = f.read()

            if str(file_data) == ERROR_FILE_CONTENT:
                errors.append(html_file.strip('.html'))
                continue

            # Parse File
            data_dict = crawler.parse_data(page_source=file_data)

            # Store Date
            crawler.store_data(data_dict, dump_source_file=False)
    
    if crawler.outfile_format == "json":
        crawler.dump_case_dict()
    
    print('Error list:', errors)
    
    crawler.quit()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('USAGE: python scrape_open_cases.py [page_source_file_directory] [outfile]')
        sys.exit(0)
    
    page_source_directory = sys.argv[1]
    outfile = sys.argv[2]
    
    main(page_source_directory, outfile)