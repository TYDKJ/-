from flask import Flask, request, jsonify
import yt_dlp, os, tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

app = Flask(__name__)

def drive_service():
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

@app.route('/download', methods=['POST'])
def download():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL'}), 400
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ydl_opts = {
                'outtmpl': f'{tmp}/%(title)s.%(ext)s',
                'format': 'best[ext=mp4]/best',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
                title = info.get('title', 'video')

            svc = drive_service()
            folder_id = os.environ.get('DRIVE_FOLDER_ID', '')
            meta = {'name': title + '.mp4'}
            if folder_id:
                meta['parents'] = [folder_id]
            media = MediaFileUpload(filepath, mimetype='video/mp4', resumable=True)
            f = svc.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            svc.permissions().create(
                fileId=f['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            return jsonify({'success': True, 'link': f['webViewLink'], 'title': title})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
