from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
CONFIG_DIR = BASE_DIR / "config"
TOKEN_FILE = CONFIG_DIR / "google_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def is_available():
    return CREDENTIALS_FILE.exists()


def _service():
    if not is_available():
        return None
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
    except ImportError:
        return None
    credentials = None
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "rb") as token:
                credentials = pickle.load(token)
        except Exception:
            credentials = None
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception:
            credentials = None
    if not credentials:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            credentials = flow.run_local_server(port=0)
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(credentials, token)
        except Exception as error:
            print("Google Drive authentication failed:", error)
            return None
    return build("drive", "v3", credentials=credentials)


def upload_file(file_path, filename=None):
    service = _service()
    if service is None:
        return None
    try:
        from googleapiclient.http import MediaFileUpload
        name = filename or Path(file_path).name
        metadata = {"name": name}
        media = MediaFileUpload(str(file_path), resumable=True)
        result = service.files().create(body=metadata, media_body=media, fields="id,name").execute()
        return result.get("id")
    except Exception as error:
        print("Google Drive upload failed:", error)
        return None


def download_file(file_id, destination):
    service = _service()
    if service is None:
        return False
    try:
        from googleapiclient.http import MediaIoBaseDownload
        import io
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "wb") as file:
            file.write(buffer.getvalue())
        return True
    except Exception as error:
        print("Google Drive download failed:", error)
        return False
