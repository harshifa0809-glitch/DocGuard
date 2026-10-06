import sqlite3
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_FILE = DATABASE_DIR / "docguard.db"


# ============================================================
# CURRENT LOGGED-IN USER
# ============================================================

_current_user_id = None


def set_current_user_id(user_id):
    """
    Store the currently logged-in user's ID.
    All document operations will use this user ID.
    """

    global _current_user_id

    if user_id is None:
        _current_user_id = None
    else:
        _current_user_id = str(user_id)


def get_current_user_id():
    """
    Return the currently logged-in user's ID.
    """

    return _current_user_id


def clear_current_user_id():
    """
    Clear the currently logged-in user.
    """

    global _current_user_id

    _current_user_id = None


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# COLUMN CHECK
# ============================================================

def _column_exists(cursor, table_name, column_name):
    """
    Check whether a column already exists in a SQLite table.
    """

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    for column in columns:
        if column[1] == column_name:
            return True

    return False


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize():
    """
    Create the DocGuard database and required tables.
    """

    connection = connect()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # DOCUMENTS TABLE
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT,

            name TEXT NOT NULL,

            category TEXT NOT NULL,

            filename TEXT NOT NULL,

            stored_path TEXT NOT NULL,

            issue_date TEXT,

            expiry_date TEXT,

            reminder_days INTEGER DEFAULT 7,

            cloud_file_id TEXT,

            notification_sent INTEGER DEFAULT 0,

            last_notification_date TEXT,

            created_at TEXT NOT NULL

        )
        """
    )

    # --------------------------------------------------------
    # DATABASE MIGRATION
    # --------------------------------------------------------

    if not _column_exists(
        cursor,
        "documents",
        "user_id"
    ):
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN user_id TEXT
            """
        )

    if not _column_exists(
        cursor,
        "documents",
        "notification_sent"
    ):
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN notification_sent INTEGER DEFAULT 0
            """
        )

    if not _column_exists(
        cursor,
        "documents",
        "last_notification_date"
    ):
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN last_notification_date TEXT
            """
        )

    if not _column_exists(
        cursor,
        "documents",
        "cloud_file_id"
    ):
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN cloud_file_id TEXT
            """
        )

    if not _column_exists(
        cursor,
        "documents",
        "reminder_days"
    ):
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN reminder_days INTEGER DEFAULT 7
            """
        )

    connection.commit()

    connection.close()


# ============================================================
# OLD DOCUMENT MIGRATION
# ============================================================

def claim_orphan_documents(user_id):
    """
    Assign old documents that do not have a user ID
    to the currently logged-in user.

    This helps migrate documents from older versions
    of DocGuard.
    """

    if not user_id:
        return

    connection = connect()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE documents

        SET user_id = ?

        WHERE user_id IS NULL
        """,
        (str(user_id),)
    )

    connection.commit()

    connection.close()


# ============================================================
# ADD DOCUMENT
# ============================================================

def add_document(
    name,
    category,
    filename,
    stored_path,
    issue_date=None,
    expiry_date=None,
    reminder_days=7,
    cloud_file_id=None
):
    """
    Add a document belonging to the currently logged-in user.
    """

    connection = connect()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO documents
        (
            user_id,
            name,
            category,
            filename,
            stored_path,
            issue_date,
            expiry_date,
            reminder_days,
            cloud_file_id,
            notification_sent,
            last_notification_date,
            created_at
        )

        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            _current_user_id,
            name,
            category,
            filename,
            stored_path,
            issue_date,
            expiry_date,
            reminder_days,
            cloud_file_id,
            0,
            None,
            datetime.now().isoformat()
        )
    )

    document_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return document_id


# ============================================================
# GET DOCUMENTS FOR CURRENT USER
# ============================================================

def get_documents():
    """
    Return documents belonging to the currently logged-in user.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            SELECT *

            FROM documents

            ORDER BY id DESC
            """
        )

    else:

        cursor.execute(
            """
            SELECT *

            FROM documents

            WHERE user_id = ?

            ORDER BY id DESC
            """,
            (_current_user_id,)
        )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# GET ALL DOCUMENTS
# ============================================================

def get_all_documents_for_notifications():
    """
    Return all documents.

    Used by the background notification service.
    """

    connection = connect()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *

        FROM documents

        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# GET SINGLE DOCUMENT
# ============================================================

def get_document(document_id):
    """
    Get one document.

    If a user is logged in, only that user's document
    can be returned.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            SELECT *

            FROM documents

            WHERE id = ?
            """,
            (document_id,)
        )

    else:

        cursor.execute(
            """
            SELECT *

            FROM documents

            WHERE id = ?

            AND user_id = ?
            """,
            (
                document_id,
                _current_user_id
            )
        )

    row = cursor.fetchone()

    connection.close()

    return row


# ============================================================
# GET DOCUMENTS BY CATEGORY
# ============================================================

def get_documents_by_category(category):
    """
    Return documents from a specific category
    for the currently logged-in user.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            SELECT *

            FROM documents

            WHERE category = ?

            ORDER BY id DESC
            """,
            (category,)
        )

    else:

        cursor.execute(
            """
            SELECT *

            FROM documents

            WHERE category = ?

            AND user_id = ?

            ORDER BY id DESC
            """,
            (
                category,
                _current_user_id
            )
        )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# SET GOOGLE DRIVE FILE ID
# ============================================================

def set_cloud_file_id(
    document_id,
    cloud_file_id
):
    """
    Store Google Drive file ID for a document.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            UPDATE documents

            SET cloud_file_id = ?

            WHERE id = ?
            """,
            (
                cloud_file_id,
                document_id
            )
        )

    else:

        cursor.execute(
            """
            UPDATE documents

            SET cloud_file_id = ?

            WHERE id = ?

            AND user_id = ?
            """,
            (
                cloud_file_id,
                document_id,
                _current_user_id
            )
        )

    connection.commit()

    connection.close()


# ============================================================
# DELETE DOCUMENT
# ============================================================

def delete_document(document_id):
    """
    Delete a document from the database.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            DELETE FROM documents

            WHERE id = ?
            """,
            (document_id,)
        )

    else:

        cursor.execute(
            """
            DELETE FROM documents

            WHERE id = ?

            AND user_id = ?
            """,
            (
                document_id,
                _current_user_id
            )
        )

    connection.commit()

    connection.close()


# ============================================================
# COUNT DOCUMENTS
# ============================================================

def count_documents():
    """
    Return the number of documents
    belonging to the current user.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM documents
            """
        )

    else:

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM documents

            WHERE user_id = ?
            """,
            (_current_user_id,)
        )

    result = cursor.fetchone()

    connection.close()

    return result[0]


# ============================================================
# COUNT CATEGORY
# ============================================================

def count_category(category):
    """
    Return the number of documents
    in a specific category.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM documents

            WHERE category = ?
            """,
            (category,)
        )

    else:

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM documents

            WHERE category = ?

            AND user_id = ?
            """,
            (
                category,
                _current_user_id
            )
        )

    result = cursor.fetchone()

    connection.close()

    return result[0]


# ============================================================
# MARK NOTIFICATION AS SENT
# ============================================================

def mark_notification_sent(
    document_id,
    notification_date
):
    """
    Mark today's expiry notification as sent.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            UPDATE documents

            SET
                last_notification_date = ?,
                notification_sent = 1

            WHERE id = ?
            """,
            (
                notification_date,
                document_id
            )
        )

    else:

        cursor.execute(
            """
            UPDATE documents

            SET
                last_notification_date = ?,
                notification_sent = 1

            WHERE id = ?

            AND user_id = ?
            """,
            (
                notification_date,
                document_id,
                _current_user_id
            )
        )

    connection.commit()

    connection.close()


# ============================================================
# RESET ONE NOTIFICATION
# ============================================================

def reset_notification(document_id):
    """
    Reset notification status for a document.
    """

    connection = connect()

    cursor = connection.cursor()

    if _current_user_id is None:

        cursor.execute(
            """
            UPDATE documents

            SET
                last_notification_date = NULL,
                notification_sent = 0

            WHERE id = ?
            """,
            (document_id,)
        )

    else:

        cursor.execute(
            """
            UPDATE documents

            SET
                last_notification_date = NULL,
                notification_sent = 0

            WHERE id = ?

            AND user_id = ?
            """,
            (
                document_id,
                _current_user_id
            )
        )

    connection.commit()

    connection.close()


# ============================================================
# RESET ALL NOTIFICATIONS
# ============================================================

def reset_all_notifications():
    """
    Reset notification status for all documents.
    """

    connection = connect()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE documents

        SET
            last_notification_date = NULL,
            notification_sent = 0
        """
    )

    connection.commit()

    connection.close()


# ============================================================
# DATABASE TEST
# ============================================================

if __name__ == "__main__":

    initialize()

    print("=" * 60)
    print("DOCGUARD DATABASE")
    print("=" * 60)

    print("Database:")
    print(DATABASE_FILE)

    print()

    print("Current User:")
    print(_current_user_id)

    print()

    print("Total Documents:")
    print(count_documents())

    print("=" * 60)
