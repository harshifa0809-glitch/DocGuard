# DocGuard – Secure Offline Document Vault & Expiry Management

DocGuard is a desktop application built with Python and CustomTkinter that stores important documents in an **encrypted local vault** and reminds you before they **expire**.

Documents such as ID proofs, insurance papers and vehicle documents are easy to lose track of, and their expiry dates are easy to miss. DocGuard keeps them in one protected place, shows how many days are left, and sends notifications before it is too late.

## Features

| Feature | Description |
|---|---|
| Encrypted Vault | Every file is encrypted with Fernet before it is stored |
| Multi-user | Documents are linked to the user ID; PIN-based login |
| Categories | Identity, Education, Vehicle, Insurance, Financial, Medical, Property, Other |
| Search | Quick document search |
| Expiry Center | Lists documents expiring within the next 60 days |
| Notifications | Reminders start 7 days before expiry, at most once per day |
| Background checker | Reminders can continue even when the app is closed (Windows Task Scheduler) |
| Google Drive | Optional backup and restore of encrypted files |
| Auto Lock | Vault locks after 15 minutes of inactivity |

## Project Structure

```
DocGuard/
├── app.py                   # Main CustomTkinter application (UI)
├── docguard_security.py     # PIN verification and encryption helpers
├── docguard_vault.py        # Encrypted file storage in the local vault
├── docguard_database.py     # SQLite database (users, documents, notifications)
├── docguard_background.py   # Background expiry checker / notifications
├── cloud_manager.py         # Google Drive backup and restore
├── config/                  # Configuration (Google Drive credentials go here)
├── database/                # SQLite database (created locally, not committed)
├── vault/                   # Encrypted documents (created locally, not committed)
└── requirements.txt
```

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/<your-username>/DocGuard.git
   cd DocGuard
   ```
2. (Optional) create a virtual environment
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   ```
3. Install the dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application
   ```bash
   python app.py
   ```

## Google Drive backup (optional)

Backup and restore need your own Google API credentials. Create an OAuth client in Google Cloud Console, enable the Drive API, and place the downloaded credentials file in the `config/` folder. Credentials and tokens are excluded by `.gitignore` and must never be committed. Backups contain only encrypted files.

## Security

- PIN verification uses PBKDF2-HMAC-SHA256 with a per-account salt.
- Documents are encrypted with Fernet (from the `cryptography` library) before being written to the vault.
- The encryption key is held for the active session and cleared when the vault locks.
- The vault, database and credentials are never stored in this repository.

## Technology Stack

Python · CustomTkinter · SQLite · cryptography (Fernet) · Plyer · Google Drive API · Windows Task Scheduler

## Current Status

- Implemented: encrypted vault, expiry tracking and reminders, closed-app Windows notifications, multiple users, Google Drive backup/restore, automatic lock
- Future scope: mobile push notifications

## Team

- Harshifa Shaikh
- Toufiq Shaikh
- Sneha Thevar

SE-AIDS(H), Batch H2 – SIES Graduate School of Technology, Navi Mumbai
