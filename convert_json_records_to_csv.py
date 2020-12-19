

import json
import csv
import sys
import os
from datetime import datetime


ALL_CSV_FIELDS = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action',
            'Defendants', 'Property Address', 'Property City', 'Plaintiff', 'Plaintiff Address',
            'Plaintiff City', 'Costs', 'Disposition Status', 'Disposition Date', 'Defendant Alias',
            'Plaintiff Alias', 'Defendant Attorney', 'Defendant Attorney Address', 'Defendant Attorney City',
            'Defendant Attorney Phone', 'Plaintiff Attorney', 'Plaintiff Attorney Address', 
            'Plaintiff Attorney City', 'Plaintiff Attorney Phone', 'Prayer Amount', 'Last Updated']

TOP_LEVEL_FIELDS = ['Case Name', 'Case Number', 'Case Status', 'File Date', 'Action', 'Prayer Amount', 'Last Updated']

def flatten_record(record_dict):
    flat_record = {}

    for field in TOP_LEVEL_FIELDS:
        flat_record[field] = record_dict[field]

    flat_record['Plaintiff'] = record_dict['Party Information']['Plaintiff']['Name']
    flat_record['Plaintiff Address'] = record_dict['Party Information']['Plaintiff']['Address']['Street Address']
    flat_record['Plaintiff City'] = record_dict['Party Information']['Plaintiff']['Address']['City']
    flat_record['Plaintiff Alias'] = record_dict['Party Information']['Plaintiff']['Alias']

    flat_record['Defendants'] = record_dict['Party Information']['Defendant(s)']['Name']
    flat_record['Defendant Alias'] = record_dict['Party Information']['Defendant(s)']['Alias']

    flat_record['Disposition Status'] = record_dict['Disposition']['Disposition Status']
    flat_record['Disposition Date'] = record_dict['Disposition']['Disposition Date']

    flat_record['Property Address'] = record_dict['Property Address']['Street Address']
    flat_record['Property City'] = record_dict['Property Address']['City']

    flat_record['Plaintiff Attorney'] = record_dict['Party Information']['Plaintiff Attorney']['Name']
    flat_record['Plaintiff Attorney Address'] = record_dict['Party Information']['Plaintiff Attorney']['Address']['Street Address']
    flat_record['Plaintiff Attorney City'] = record_dict['Party Information']['Plaintiff Attorney']['Address']['City']
    flat_record['Plaintiff Attorney Phone'] = record_dict['Party Information']['Plaintiff Attorney']['Phone']

    flat_record['Defendant Attorney'] = record_dict['Party Information']['Defendant Attorney']['Name']
    flat_record['Defendant Attorney Address'] = record_dict['Party Information']['Defendant Attorney']['Address']['Street Address']
    flat_record['Defendant Attorney City'] = record_dict['Party Information']['Defendant Attorney']['Address']['City']
    flat_record['Defendant Attorney Phone'] = record_dict['Party Information']['Defendant Attorney']['Phone']
    
    flat_record['Costs'] = record_dict['Total Costs']
    
    return flat_record


def main(infile, outfile):

    # Load JSON data
    with open(infile, 'r') as f:
        json_data = json.load(f)
    
    json_data.sort(key=lambda x: datetime.strptime(x['File Date'], '%m/%d/%Y'))
    
    # Create new CSV with fieldnames as header
    with open(outfile, 'w') as f:
        out_csv = csv.DictWriter(f, fieldnames=ALL_CSV_FIELDS)
        out_csv.writeheader()

        print('Total Records:', len(json_data))

        # Iterate thorugh JSON records, flatten them, and add them to the CSV file
        for i, record in enumerate(json_data):
            
            # Output index number for user feedback when working with a very large file
            if i % 5000 == 0:
                print(i)

            row = flatten_record(record)
            out_csv.writerow(row)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('USAGE: python convert_json_records_to_csv.py [input JSON file] [output CSV file]')
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2]
    
    if os.path.splitext(infile)[1] != '.json' or os.path.splitext(outfile)[1] != '.csv':
        raise ValueError("Input datafile must be a JSON file and output datafile mut be a CSV file")

    main(infile, outfile)