from __future__ import print_function
import pickle
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from credentials.google_drive_config import hard_coded_folder_ids

from convert_json_records_to_csv import convert_to_csv
from utils import get_year_range

import csv
import json
from datetime import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('credentials/google_token.pickle'):
        with open('credentials/google_token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/google_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('credentials/google_token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def get_folder_id_with_name(service, folder_name):
    response = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",
                                    spaces='drive',
                                    fields='nextPageToken, files(id, name)'
                                    ).execute()
    return response.get('files', [])[0].get('id')


def get_file_id_with_name(service, file_name, parent_foldername):
    parent_folder_id = hard_coded_folder_ids[parent_foldername]
    response = service.files().list(q=f"mimeType='{get_mime_type(file_name)}' and name='{file_name}' and '{parent_folder_id}' in parents",
                                    spaces='drive',
                                    fields='nextPageToken, files(id, name)'
                                    ).execute()
    return response.get('files', [])[0].get('id')


def upload_file(service, local_filepath, drive_filename, drive_foldername):
    file_metadata = {
        'name': drive_filename,
        'parents': [hard_coded_folder_ids[drive_foldername]]
    }

    media = MediaFileUpload(local_filepath, mimetype=get_mime_type(local_filepath), resumable=True)
    file = service.files().create(  body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()

    print(f"Uploaded File: {drive_filename}, ID: {file.get('id')}")


def update_file(service, local_filepath, drive_filename, file_id):
    file_metadata = {
        'name': drive_filename
    }

    media = MediaFileUpload(local_filepath, mimetype=get_mime_type(local_filepath), resumable=True)
    file = service.files().update(  fileId=file_id,
                                    body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()

    print(f"Updated File: {drive_filename}, ID: {file.get('id')}")


def get_mime_type(filepath):
    if os.path.splitext(filepath)[1] == '.json':
        return 'application/json'
    else:
        return 'text/csv'


def get_year_data(basefile, select_year):
    if os.path.splitext(basefile)[1] == '.json':
        json_input = True
    else:
        json_input = False

    with open(basefile, 'r') as f:
        if json_input:
            data = json.load(f)
        else:
            data = [x for x in csv.DictReader(f)]
    
    year_data = [x for x in data if int(datetime.strptime(x['File Date'], '%m/%d/%Y').year) == select_year]

    if json_input:
        out_filename = f'data/upload_data/all_{select_year}_data.json'
        with open(out_filename, 'w') as f:
            json.dump(year_data, f)
    else:
        out_filename = f'data/upload_data/all_{select_year}_data.csv'
        fields = list(year_data[0].keys())

        with open(out_filename, 'w') as f:
            out_csv = csv.DictWriter(f, fieldnames=fields)
            out_csv.writeheader()
            for row in year_data:
                out_csv.writerow(row)
    
    return out_filename


def upload_or_update_file(service, local_filepath, parent_foldername):
    drive_filename = local_filepath.split('/')[-1]
    try:
        file_id = get_file_id_with_name(service, file_name=drive_filename, parent_foldername=parent_foldername)
        update_file(service, local_filepath=local_filepath, drive_filename=drive_filename, file_id=file_id)
    except IndexError:
        upload_file(service, local_filepath=local_filepath, drive_filename=drive_filename, drive_foldername=parent_foldername)


def main():
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    # Upload/Update Full Files
    for local_filepath in ['data/full_data.csv', 'data/full_data.json']:
        upload_or_update_file(service, local_filepath, parent_foldername='Full Data (since 2011)')

    # Upload/Update Annual Files
    start_year, end_year = get_year_range('data/full_data.csv')
    for year in range(start_year, end_year+1):
        for basefile in ['data/full_data.csv', 'data/full_data.json']:
            local_filepath = get_year_data(basefile, year)
            upload_or_update_file(service, local_filepath, parent_foldername='Yearly Data')
            os.remove(local_filepath)

    # Upload latest update file (either by taking time off of filename and using today's date or finding latest with os)
    update_files = [f'data/updates/{x}' for x in os.listdir('data/updates/') if '.json' in x]
    latest_file = max(update_files, key=os.path.getctime)
    
    convert_to_csv(latest_file, latest_file.replace('.json', '.csv'))
    for local_filepath in [latest_file, latest_file.replace('.json', '.csv')]:
        upload_or_update_file(service, local_filepath=local_filepath, parent_foldername='Daily Update Data (New/Updated Records)')
        # os.remove(local_filepath)


if __name__ == '__main__':
    main()