# Tfolex: Telegram Folder & Chat List Extractor

![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)

Tfolex is a command-line utility designed to extract and export your Telegram chat lists and the detailed structure of your chat folders into organized CSV or JSON files.

It's a perfect tool for archiving, analysis, or simply getting a comprehensive overview of your Telegram account's organization.

## Why Use Tfolex?

-   **Digital Archiving:** Create a backup of your folder structures and a master list of all chats you are a part of.
-   **Data Analysis:** Export your chat list to a spreadsheet to sort, filter, and analyze your communication patterns.
-   **Migration & Tooling:** Get a clean list of chat names and their corresponding IDs, which can be used for other scripts or bots.
-   **Account Cleanup:** Quickly identify old, archived, or unused chats, groups, and channels.

## Features

-   **Interactive CLI Menu:** Easy-to-use menu system for choosing operations.
-   **Master Chat List Extractor:**
    -   Fetch all chats from your account.
    -   Filter by type: Personal DMs, Groups, Channels, and Bots.
    -   Exports `Chat Name`, `Chat ID`, `Chat Type`, and `Archived Status`.
-   **Advanced Folder Extractor:**
    -   Extracts detailed information for selected (or all) chat folders.
    -   Lists pinned, included, and excluded chats within each folder.
    -   Shows the rules used to build the folder (e.g., include all channels, exclude muted, etc.).
-   **Flexible Export Options:** Save extracted data as:
    -   **CSV:** Ideal for use in spreadsheets like LibreOffice Calc or Microsoft Excel.
    -   **JSON:** Best for developers, archiving, and programmatic use.
-   **Secure & Session-Based:** Handles 2FA (Two-Factor Authentication) and creates a local session file for quick, subsequent logins without re-entering credentials.

---

## Prerequisites

1.  **Python 3.8+**
2.  **A Telegram Account**
3.  **Telegram API Credentials (API ID and Hash)**
    -   You must obtain these from Telegram. It's a simple, one-time process.
    -   Log in to [my.telegram.org](https://my.telegram.org) with your phone number.
    -   Go to "API development tools" and fill out the form (app name and short name can be anything, e.g., "Tfolex Utility").
    -   You will be given an `api_id` and `api_hash`. **Keep these secret!**

---

## Installation & Setup

**1. Clone the Repository**

```bash
git clone https://github.com/dragon-Elec/Tfolex.git
cd Tfolex
```

**2. Set up a Virtual Environment (Recommended)**

This isolates the project's dependencies from your system.

*   On Linux/macOS:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
*   On Windows:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

**3. Install Dependencies**

The only external library needed is `telethon`.

```bash
pip install telethon
```

**4. Create the Configuration File**

Create a file named `config.ini` in the same directory as the script. Copy the contents below and fill in your details.

```ini
[telegram]
; Get these from my.telegram.org
api_id = 12345678
api_hash = your_long_api_hash_string_here
phone_number = +12345678900 ; Use your full number with country code

[settings]
; The script will create a session file with this name
session_name = my_telegram_session

; Default names for the output files (date will be appended)
default_master_list_output = master_chat_list
default_folder_output = folder_export
```

---

## How to Use

**1. Run the Script**

Make sure your virtual environment is activated, then run:

```bash
python3 "tfolextractA {stable}.py"
```

**2. First-Time Login**

The first time you run the script, `telethon` will need to authorize your session:
-   It will ask for the code sent to your Telegram app.
-   If you have 2FA enabled, it will ask for your password.

A `.session` file (e.g., `my_telegram_session.session`) will be created. On subsequent runs, you will be logged in automatically.

**3. Main Menu**

You will see the main menu:

```text
==================== MAIN MENU ====================
1. Master Chat List (Extract all chats by type)
2. Folder Information (Export specific folder data)
3. Exit
Enter your choice:
```

-   Choose `1` to extract a list of your chats. You'll be asked which chat types to include.
-   Choose `2` to extract data about your chat folders. You'll be asked to select which folders to export.
-   Choose `3` to exit the program.

**4. Export Format**

After extracting the data, you will be prompted to choose an export format:

```text
--- Export Data ---
  1. CSV (Recommended for spreadsheets like LibreOffice Calc)
  2. JSON (For developers & archiving)
Enter your choice (1 or 2):
```

The file will be saved in the same directory (e.g., `folder_export_2025-10-27.csv`).

---

## Example Output

#### Master List (CSV)

`master_chat_list_2025-10-27.csv`

| chat_name             | chat_type | chat_id    | is_archived |
| --------------------- | --------- | ---------- | ----------- |
| Project Discussion    | Group     | -10012...  | False       |
| Alice Smith           | Personal  | 55443322   | True        |
| Tech News             | Channel   | -10098...  | False       |
| Telegram Bot          | Bot       | 88776655   | False       |

#### Folder Info (JSON)

`folder_export_2025-10-27.json`

```json
[
  {
    "folder_name": "Work",
    "folder_id": 1,
    "emoticon": "💼",
    "pinned_chats": [
      "Team Standup",
      "Project Phoenix"
    ],
    "included_chats": [
      "Team Standup",
      "Project Phoenix",
      "Marketing Dept",
      "John Doe"
    ],
    "excluded_chats": [],
    "rule_contacts": true,
    "rule_non_contacts": false,
    "rule_groups": true,
    "rule_channels": false,
    "rule_bots": false,
    "rule_exclude_muted": true,
    "rule_exclude_read": false,
    "rule_exclude_archived": true
  }
]
```

## License

This project is licensed under the **GNU General Public License v2.0**. See the `LICENSE` file in the repository for the full text.

## Disclaimer

This is a third-party tool. Use it responsibly and be mindful of Telegram's Terms of Service regarding API usage. Your API credentials and session file are stored locally on your machine and are not sent anywhere else.
```
