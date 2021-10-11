from __future__ import print_function
import os.path
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import argparse

from datetime import datetime
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']
MIN_AREA = 150
SCALE = 720
# rpiFolder = '1bMnujx42DmxmhT2U-cXjuSijkvqLSxde'
# changesFolder = '1B4ZgTFazv5My3gSWAsjYg0dlLjaqy12a'
movementsFolder = '1tFNJX8-JuZqFQyKWkD_nfzW7c1RKNi-v'
movementsDebugFolder = '1eNIxIXKW0SpvprChaOO4boodHahsnaiE'
movementsPrevFolder = '1na6BYiqdXpa1nYQOirIkmwcFpjdsCQnl'
rpiFolder = '1RoB8bBSurOYf23zFTjA92VWDGOB_rwBj'
rpiPrevFolder = '1ax6Bb-U9MCJvSuy9qGn-KFYx37yVQY3i'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--source", default="1RoB8bBSurOYf23zFTjA92VWDGOB_rwBj", help="source folder")
    ap.add_argument("-d", "--destination", default="1ax6Bb-U9MCJvSuy9qGn-KFYx37yVQY3i", help="destination folder")
    ap.add_argument("-c", "--clear", default=False, action="store_true", help="clear destination folder")
    ap.add_argument("-t", "--token", default="/home/pi/opt/token.json", help="token file")
    ap.add_argument("--dry", default=False, action="store_true", help="token file")
    args = vars(ap.parse_args())

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(args.get("token")):
        creds = Credentials.from_authorized_user_file(args.get("token"), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Credentials not valid")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(args.get("token"), 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    source = args.get("source")
    destination = args.get("destination")
    source_folder = service.files().get(fileId=source).execute()
    source_folder_name = source_folder['name']
    print(f"Source directory {source_folder_name}")
    results = service.files().list(q=f"parents in '{source}'  and trashed = false", pageSize=10,
                                   fields="nextPageToken, files(id, name)").execute()
    if args.get("clear") and len(results.get('files', None)) == 0:
        print("No data in current folder, skip delete")
        return

    counter = 0
    page_token = None
    destination_folder = service.files().get(fileId=destination).execute()
    destination_folder_name = destination_folder['name']
    if args.get("clear"):
        print(f"Destination directory {destination_folder_name}")
        while True:
            print("Starting batch delete")
            results = service.files().list(q=f"parents in '{destination}'  and trashed = false", pageToken=page_token, pageSize=100,
                                           fields="nextPageToken, files(id, name)").execute()
            files = results.get('files', [])
            print(f"Removing {len(files)} items from {destination_folder_name}")
            for item in files:
                file_id = item["id"]
                file_name = item["name"]
                if not args.get("dry"):
                    print(f"  delete {file_name} {file_id}")
                    service.files().delete(fileId=file_id).execute()
                else:
                    print(f"  simulate delete {file_name} {file_id}")
            page_token = results.get('nextPageToken', None)
            counter = counter + len(results.get('files', []))
            if page_token is None:
                break

        print(f"Removed {counter} items from {source}")
    else:
        print("No clear command found, just copy")

    page_token = None
    counter = 0
    while True:
        print("Starting batch move")
        results = service.files().list(q=f"parents in '{source}'  and trashed = false", pageToken=page_token, pageSize=100,
                                       fields="nextPageToken, files(id, name)").execute()
        files = results.get('files', [])
        print(f"Moving {len(files)} items from {source_folder_name} to {destination_folder_name}")
        for item in results.get('files', []):
            file_id = item["id"]
            file_name = item["name"]
            if not args.get("dry"):
                print(f"   move {file_name} {file_id}")
                service.files().update(fileId=file_id, removeParents=source, addParents=destination).execute()
            else :
                print(f"   simulate move {file_name} {file_id}")
        counter = counter + len(results.get('files', []))
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break
    print(f"Moved {counter} items from {source_folder_name} to {destination_folder_name}")


if __name__ == '__main__':
    main()
