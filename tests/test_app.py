import unittest
from unittest.mock import patch
from flask import url_for
from app import app, create_download_directory, DOWNLOAD_DIR

class TestApp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_splash_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to Google Photos Management App', response.data)

    def test_authorize_redirect(self):
        with self.app as c:
            response = c.get('/authorize')
            self.assertEqual(response.status_code, 302)  # Should redirect

    @patch('app.Flow')
    def test_oauth2callback(self, mock_flow):
        mock_flow_instance = mock_flow.from_client_secrets_file.return_value
        mock_flow_instance.fetch_token.return_value = True
        mock_flow_instance.credentials.token = 'fake_token'
        mock_flow_instance.credentials.refresh_token = 'fake_refresh_token'
        mock_flow_instance.credentials.client_id = 'fake_client_id'
        mock_flow_instance.credentials.client_secret = 'fake_client_secret'
        mock_flow_instance.credentials.token_uri = 'fake_token_uri'
        mock_flow_instance.credentials.scopes = ['https://www.googleapis.com/auth/photoslibrary']

        with self.app as c:
            with c.session_transaction() as sess:
                sess['state'] = 'fake_state'

            response = c.get('/oauth2callback?state=fake_state&code=fake_code')
            self.assertEqual(response.status_code, 302)  # Should redirect to options

    def test_options_page_get(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['credentials'] = {
                    'token': 'fake_token',
                    'refresh_token': 'fake_refresh_token',
                    'client_id': 'fake_client_id',
                    'client_secret': 'fake_client_secret',
                    'token_uri': 'fake_token_uri',
                    'scopes': ['https://www.googleapis.com/auth/photoslibrary']
                }

            response = c.get('/options')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Google Photos Management Options', response.data)

    def test_options_page_post(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['credentials'] = {
                    'token': 'fake_token',
                    'refresh_token': 'fake_refresh_token',
                    'client_id': 'fake_client_id',
                    'client_secret': 'fake_client_secret',
                    'token_uri': 'fake_token_uri',
                    'scopes': ['https://www.googleapis.com/auth/photoslibrary']
                }

            response = c.post('/options', data={
                'default_photos_per_week': '5',
                'start_date_1': '2020-11-01',
                'end_date_1': '2020-11-07',
                'photos_per_week_1': '10',
                'start_date_2': '2023-07-01',
                'end_date_2': '2023-07-07',
                'photos_per_week_2': '13'
            })

            self.assertEqual(response.status_code, 302)  # Should redirect after form submission

    @patch('app.build')
    def test_download_photos(self, mock_build):
        mock_service = mock_build.return_value
        mock_media_items = [
            {
                'baseUrl': 'http://example.com/photo1',
                'filename': 'photo1.jpg',
                'mediaMetadata': {'creationTime': '2023-05-01T00:00:00Z'}
            },
            {
                'baseUrl': 'http://example.com/photo2',
                'filename': 'photo2.jpg',
                'mediaMetadata': {'creationTime': '2023-05-02T00:00:00Z'}
            }
        ]
        mock_service.mediaItems().list().execute.return_value = {
            'mediaItems': mock_media_items
        }

        with self.app as c:
            with c.session_transaction() as sess:
                sess['credentials'] = {
                    'token': 'fake_token',
                    'refresh_token': 'fake_refresh_token',
                    'client_id': 'fake_client_id',
                    'client_secret': 'fake_client_secret',
                    'token_uri': 'fake_token_uri',
                    'scopes': ['https://www.googleapis.com/auth/photoslibrary']
                }

            response = c.get('/download_photos')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'All photos downloaded successfully.', response.data)

if __name__ == '__main__':
    unittest.main()