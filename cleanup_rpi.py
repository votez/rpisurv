import base64
import urllib

import google.auth
from __future__ import print_function
import os.path
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from apiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']


def build_service(api, version):
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/pi/opt/token.json'):
        creds = Credentials.from_authorized_user_file('/home/pi/opt/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Credentials not valid")
            exit(-5)
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
     """
    service = build_service("drive", "v3")
    dryRun = os.environ.get('KEEP')
    currentFolder = os.environ.get('CURRENT_FOLDER', '1RoB8bBSurOYf23zFTjA92VWDGOB_rwBj')
    backupFolder = os.environ.get('BACKUP_FOLDER', '1ax6Bb-U9MCJvSuy9qGn-KFYx37yVQY3i')
    results = service.files().list(q=f"parents in '{currentFolder}'", pageSize=10,
                                   fields="nextPageToken, files(id, name)").execute()
    if (len(results.get('files', None)) == 0):
        print("No data in current folder, skip delete")
        return

    page_token = None
    counter = 0
    backupFolderInfo = service.files().get(fileId=backupFolder).execute().get('name', None)
    currentFolderInfo = service.files().get(fileId=currentFolder).execute().get('name', None)
    while True:
        print("Starting batch delete")
        results = service.files().list(q=f"parents in '{backupFolder}'", pageToken=page_token, pageSize=100,
                                       fields="nextPageToken, files(id, name)").execute()
        files = results.get('files', [])
        print(f"Removing {len(files)} items from {backupFolderInfo}")
        for item in files:
            if dryRun is None:
                service.files().delete(fileId=item["id"]).execute()
        page_token = results.get('nextPageToken', None)
        counter = counter + len(results.get('files', []))
        if page_token is None:
            break

    print(f"Removed {counter} items from {backupFolderInfo}")
    page_token = None
    counter = 0
    while True:
        print("Starting batch move")
        results = service.files().list(q=f"parents in '{currentFolder}'", pageToken=page_token, pageSize=100,
                                       fields="nextPageToken, files(id, name)").execute()
        files = results.get('files', [])
        print(f"Moving {len(files)} items from {currentFolderInfo} to {backupFolderInfo}")
        for item in results.get('files', []):
            service.files().update(fileId=item["id"], removeParents=currentFolder, addParents=backupFolder).execute()
        counter = counter + len(results.get('files', []))
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break
    print(f"Moved {counter} items from {currentFolderInfo} to {backupFolderInfo}")
