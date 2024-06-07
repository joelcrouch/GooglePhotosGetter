

## Python Google  Photo downloader/deleter app.
##  How did i do this?
1  Set up Google cloud. 
    a. Enable the photos library API
    b Download the Oauth 2.0 client credentials json file.
2. Install the requuired libraries with pip:
   '''
   bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 requests flask
   '''

3.  Create a directory for your project, mine is called photo_updater, and create a Python script, 'app.py'. You will also need a 'templates' folder for HTML templates.  Also probably a 'styles.css' as well.

The following is app.py: 

'''
python  
from flask import Flask, redirect, url_for, session, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import requests

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Path to your client_secret.json file
CLIENT_SECRETS_FILE = "path/to/your/client_secret.json"

# This scope allows read-only access to the authenticated user's photos library
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# OAuth 2.0 endpoints
REDIRECT_URI = 'http://localhost:5000/oauth2callback'


@app.route('/')
def index():
    return 'Welcome to the Google Photos Downloader App! <a href="/authorize">Authorize</a>'


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

    return redirect(url_for('download_photos'))


@app.route('/download_photos')
def download_photos():
    if 'credentials' not in session:
        return redirect('authorize')
    
    credentials = Credentials(**session['credentials'])
    service = build('photoslibrary', 'v1', credentials=credentials)
    
    results = service.mediaItems().list(pageSize=10).execute()
    items = results.get('mediaItems', [])
    
    if not items:
        return 'No photos found.'
    
    for item in items:
        download_photo(item['baseUrl'], item['filename'])
    
    return 'Photos downloaded successfully.'


def download_photo(url, filename):
    response = requests.get(url)
    with open(f'photos/{filename}', 'wb') as f:
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

The following is the index.html in 'templates' folder:

'''
HTML

<!doctype html>
<html>
<head>
    <title>Google Photos Downloader</title>
</head>
<body>
    <h1>Google Photos Downloader</h1>
    <a href="/authorize">Authorize Google Photos Access</a>
</body>
</html>
'''

And naively, that should run. :  python3 app.py

But that rascal only does the first 10 photos. The first ten photos starting where?  Not super useful.  However, it is a great test of wethier it works in general.  So lets add some 'pagination'. First amend this function-download photos to this:  

'''
python
def download_photos():
    if 'credentials' not in session:
        return redirect('authorize')
    
    credentials = Credentials(**session['credentials'])
    service = build('photoslibrary', 'v1', credentials=credentials)
    
    next_page_token = None
    if not os.path.exists('photos'):
        os.makedirs('photos')
    
    while True:
        results = service.mediaItems().list(pageSize=100, pageToken=next_page_token).execute()
        items = results.get('mediaItems', [])
        
        if not items:
            break
        
        for item in items:
            download_photo(item['baseUrl'], item['filename'])
        
        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break
    
    return 'All photos downloaded successfully.'
'''


Add some verbiage to th download_photos function to create a diriectory:  

'''
python

def download_photo(url, filename):
    response = requests.get(url)
    file_path = os.path.join('photos', filename)
    with open(file_path, 'wb') as f:
        f.write(response.content)

'''

Cool.  That oughtta do the trick.  

Ok. Great. You have managed to download the 100 gigs of photos of your kid's gaptoothed smile. But you are still at the same problem that brought you here.  You want to have some space on your google drive.  100 GB's oughtta be enough.  So lets delete some (read most)
of the photos on google drive after you have downloaded them.  So the above script saves the photos with the same name/metadata they are saved on google drive. In other words you an iterate through the directory of photos create in the download_photo, compare the name/metadata, and delete the photo on google drive that matches.  That should free up some space.
(OOOOmph, I am just setting myself up here for a home-based cloud system, clearly, Blargh)

Anyways, in order to do that you have to a) add some scope to the app b) add some matching functionality.  Question?  Should we do this all at once in one fell swooop? Or run the 'getter' script, make sure we have good copies of the data, then run the 'deleter' script?  I am more prone to the latter.  It seems safer. Definitely take longer the first time you want to delete 100 gigs of photos.  


So change te Scopes line to this:

'''
python
SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
'''
The previous Scopes was a read-only, but you need a delete feature, so here we are. 

Replace the last line in 'download_photos' to this:
'''
return 'All photos downloaded successfully. <a href="/delete_photos">Delete downloaded photos from Google Photos</a>'
'''
You will need a new html file as well.
or will you. I go back and forth with adding more hoopity-hoop-ha for users to click through.  Maybe later.


Anyways here is the meat of the deletion: 

'''
python

@app.route('/delete_photos')
def delete_photos():
    if 'credentials' not in session:
        return redirect('authorize')
    
    credentials = Credentials(**session['credentials'])
    service = build('photoslibrary', 'v1', credentials=credentials)
    
    local_files = set(os.listdir('photos'))
    
    next_page_token = None
    while True:
        results = service.mediaItems().list(pageSize=100, pageToken=next_page_token).execute()
        items = results.get('mediaItems', [])
        
        if not items:
            break
        
        for item in items:
            if item['filename'] in local_files:
                delete_photo(service, item['id'])
        
        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break
    
    return 'Downloaded photos deleted from Google Photos.'


def delete_photo(service, media_item_id):
    service.mediaItems().delete(mediaItemId=media_item_id).execute()

'''

HMMMM.  It seems like when i am using the first script, it is coming in no particular order.  How can i download them and put them in order in folders corresponding to the day-year, eg jan, 2024?  