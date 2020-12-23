
# Update existing data/pull down new data. This updates the full_data file, and creates a separate update file.
python update_data.py data/full_data.json

# Convert the JSON versions of the full data file and update file to CSV files, to be uploaded too
python convert_json_records_to_csv.py data/full_data.json data/full_data.csv 

# Upload/update full data files, annual data files, update file in Drive folder
python send_data_to_gdrive.py
