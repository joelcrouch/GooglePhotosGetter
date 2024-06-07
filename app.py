from flask import Flask, redirect, url_for, session, request, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import requests
import random
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Path to your client_secret.json file
CLIENT_SECRETS_FILE = "path/to/your/client_secret.json"

# Scopes including delete permission
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']

# OAuth 2.0 endpoints
REDIRECT_URI = 'http://localhost:5000/oauth2callback'

# In-memory storage for user settings
user_settings = {}

# Define the directory name for downloading photos
DOWNLOAD_DIR = "google_photos_downloads"


def create_download_directory():
    """Create a directory for downloading Google Photos if it does not exist."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)


@app.route('/')
def splash():
    return render_template('splash.html')


@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI)
    
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    user_id = credentials.client_id  # or another unique user identifier
    user_settings[user_id] = {
        'credentials': session['credentials'],
        'default_photos_per_week': 0,
        'time_ranges': []
    }

    return redirect(url_for('options'))


@app.route('/options', methods=['GET', 'POST'])
def options():
    if request.method == 'POST':
        if 'credentials' not in session:
            return redirect(url_for('authorize'))

        user_id = session['credentials']['client_id']
        
        default_photos_per_week = int(request.form['default_photos_per_week'])
        time_ranges = []

        for i in range(1, 3):
            start_date = request.form.get(f'start_date_{i}')
            end_date = request.form.get(f'end_date_{i}')
            photos_per_week = int(request.form.get(f'photos_per_week_{i}', 0))
            if start_date and end_date and photos_per_week:
                time_ranges.append({
                    'start_date': start_date,
                    'end_date': end_date,
                    'photos_per_week': photos_per_week
                })
        
        user_settings[user_id]['default_photos_per_week'] = default_photos_per_week
        user_settings[user_id]['time_ranges'] = time_ranges

        return redirect(url_for('download_photos'))

    return render_template('options.html')


@app.route('/download_photos')
def download_photos():
    if 'credentials' not in session:
        return redirect('authorize')
    
    user_id = session['credentials']['client_id']
    credentials = Credentials(**user_settings[user_id]['credentials'])
    service = build('photoslibrary', 'v1', credentials=credentials)
    
    media_items = []
    next_page_token = None

    # Create the download directory
    create_download_directory()
    
    while True:
        results = service.mediaItems().list(pageSize=100, pageToken=next_page_token).execute()
        items = results.get('mediaItems', [])
        
        if not items:
            break
        
        media_items.extend(items)
        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break

    # Sort media items by creation time (most recent first)
    media_items.sort(key=lambda x: x['mediaMetadata']['creationTime'], reverse=True)

    # Download sorted media items
    for item in media_items:
        download_photo(item['baseUrl'], item['filename'])

    return 'All photos downloaded successfully. <a href="/delete_photos">Delete downloaded photos from Google Photos</a>'


def download_photo(url, filename):
    response = requests.get(url)
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(file_path, 'wb') as f:
        f.write(response.content)


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


if __name__ == '__main__':
    app.run('localhost', 5000, debug=True)

'''
Code was inspired by Dr. Wu-Chang Feng at Portland State University.

'''