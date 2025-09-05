#!/usr/bin/env python3
import asyncio
import configparser
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient, functions, types
from telethon.errors.rpcerrorlist import (ApiIdInvalidError,
                                           PasswordHashInvalidError,
                                           PhoneCodeExpiredError,
                                           PhoneCodeInvalidError,
                                           SessionPasswordNeededError)
from telethon.tl.types import PeerChannel, PeerChat, PeerUser

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)


class TelegramDataExtractor:
    """
    A tool to extract master chat lists and folder information from Telegram.
    """

    def __init__(self, config: dict):
        """Initializes the extractor with configuration."""
        self.config = config
        session_path = Path(__file__).parent / self.config['session_name']
        self.client = TelegramClient(
            str(session_path),
            self.config['api_id'],
            self.config['api_hash']
        )

    async def _handle_login(self) -> bool:
        """Handles the client connection and interactive login process with retries."""
        phone_number = self.config['phone_number']

        await self.client.connect()

        if await self.client.is_user_authorized():
            return True

        logging.info("First time use or session expired. Please sign in.")
        sent_code = None
        while not await self.client.is_user_authorized():
            try:
                if not sent_code:
                    sent_code = await self.client.send_code_request(phone_number)

                await self.client.sign_in(
                    phone_number,
                    input('Enter the code you received (or press Ctrl+C to exit): '),
                    phone_code_hash=sent_code.phone_code_hash
                )

            except PhoneCodeInvalidError:
                print("❌ Invalid code. Please try again.")
            except PhoneCodeExpiredError:
                print("❌ The code has expired. A new code will be requested.")
                sent_code = None
            except SessionPasswordNeededError:
                while True:
                    try:
                        await self.client.sign_in(password=input('Your 2FA password: '))
                        break
                    except PasswordHashInvalidError:
                        print("❌ Incorrect password. Please try again.")
            except (ApiIdInvalidError, ValueError):
                logging.error("❌ Fatal: Your API_ID or API_HASH is invalid. Please check your config.ini.")
                return False
            except Exception as e:
                logging.error(f"❌ An unexpected error occurred during login: {e}")
                return False

        return True

    def _get_chat_type_string(self, dialog) -> str:
        """Helper to determine the string representation of a chat type."""
        if dialog.is_group:
            return "Group"
        if dialog.is_channel:
            return "Channel"
        if dialog.is_user:
            return "Bot" if getattr(dialog.entity, 'bot', False) else "Personal"
        return "Unknown"

    def _get_rule_based_chat_names(self, folder: types.DialogFilter, all_dialogs: list) -> list[str]:
        """
        Filters a list of all dialogs to find chats matching the folder's rules.
        This does not handle explicitly included/excluded peers, only rule-based ones.
        """
        matching_names = []
        for dialog in all_dialogs:
            # --- Rule-based Exclusions ---
            # These rules apply to chats that would otherwise be included by the rules below.
            if (folder.exclude_muted and dialog.muted) or \
               (folder.exclude_read and dialog.unread_count == 0 and not dialog.unread_mark) or \
               (folder.exclude_archived and dialog.archived):
                continue

            # --- Rule-based Inclusions ---
            entity = dialog.entity
            # Note: A 'contact' is a user you have in your address book.
            is_contact = getattr(entity, 'contact', False)
            is_bot = getattr(entity, 'bot', False)
            # A 'non_contact' is a user you've messaged but is not in your contacts.
            is_personal_non_contact = dialog.is_user and not is_contact and not is_bot

            if (folder.contacts and is_contact) or \
               (folder.groups and dialog.is_group) or \
               (folder.broadcasts and dialog.is_channel) or \
               (folder.bots and is_bot) or \
               (folder.non_contacts and is_personal_non_contact):
                matching_names.append(dialog.name)

        return matching_names

    async def _extract_master_list(self):
        """Logic for Function 1: Master Chat List Extractor."""
        print("\n--- Master Chat List Extractor ---")
        print("Choose chat types to include:")
        print("  1. Personal Chats (DMs)")
        print("  2. Groups & Supergroups")
        print("  3. Channels")
        print("  4. Bots")
        print("  5. All (include everything)")

        while True:
            try:
                choice = input("Enter your choice (e.g., 1,3,4 or 5): ")
                choices = {int(c.strip()) for c in choice.split(',')}
                if not all(1 <= c <= 5 for c in choices):
                    raise ValueError
                break
            except ValueError:
                print("Invalid input. Please enter numbers from 1 to 5, separated by commas.")

        filters = {1: "Personal", 2: "Group", 3: "Channel", 4: "Bot"}
        selected_types = {filters[c] for c in choices if c in filters}
        if 5 in choices:
            selected_types.update(filters.values())

        logging.info(f"Fetching chats of types: {', '.join(selected_types or ['All'])}...")

        extracted_data = []
        async for dialog in self.client.iter_dialogs():
            chat_type = self._get_chat_type_string(dialog)
            if not selected_types or chat_type in selected_types:
                extracted_data.append({
                    "chat_name": dialog.name,
                    "chat_type": chat_type,
                    "chat_id": dialog.id,
                    "is_archived": dialog.archived,
                })

        logging.info(f"Found {len(extracted_data)} matching chats.")
        if extracted_data:
            self._export_data(extracted_data, self.config['default_master_list_output'])
        else:
            print("No chats found matching your criteria.")

    async def _get_names_for_peers(self, peers: list[PeerUser | PeerChat | PeerChannel]) -> list[str]:
        """
        Given a list of peer objects, resolves their names concurrently.
        """
        if not peers:
            return []
        
        tasks = [self.client.get_entity(p) for p in peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        names = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                peer = peers[i]
                peer_id = getattr(peer, 'channel_id', getattr(peer, 'user_id', 'N/A'))
                names.append(f"Unknown/Inaccessible Entity (ID: {peer_id})")
            else:
                names.append(getattr(res, 'title', getattr(res, 'first_name', f'User {res.id}')))
        return names

    async def _extract_folders(self):
        """Logic for Function 2: Advanced Folder Extractor."""
        logging.info("Fetching folder information...")
        try:
            dialog_filters_container = await self.client(functions.messages.GetDialogFiltersRequest())
        except Exception as e:
            logging.error(f"Could not fetch dialog filters: {e}")
            return
        
        # LUX: FIX - Iterate over the .filters attribute of the container object, not the object itself.
        folders = [f for f in dialog_filters_container.filters if isinstance(f, types.DialogFilter)]
    
        if not folders:
            print("No chat folders found in your account.")
            return

        logging.info("Prefetching all dialogs for efficient rule matching...")
        all_dialogs = await self.client.get_dialogs()
        logging.info(f"Found {len(all_dialogs)} total dialogs to filter from.")

        print("\n--- Folder Information Extractor ---")
        print("Available folders:")
        for i, folder in enumerate(folders):
            print(f"  {i + 1}. {folder.title.text}")
        print(f"  {len(folders) + 1}. All Folders")

        while True:
            try:
                choice_str = input(f"Choose folders to export (e.g., 1,3 or {len(folders) + 1} for all): ")
                choices = {int(c.strip()) for c in choice_str.split(',')}
                if not all(1 <= c <= len(folders) + 1 for c in choices):
                    raise ValueError
                break
            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        selected_folders = []
        if len(folders) + 1 in choices:
            selected_folders = folders
        else:
            selected_folders = [folders[i - 1] for i in choices if 1 <= i <= len(folders)]

        extracted_data = []
        for folder in selected_folders:
            logging.info(f"Processing folder: {folder.title.text}...")

            # 1. Get chats from specific lists (pinned, explicitly included/excluded)
            pinned_names = await self._get_names_for_peers(folder.pinned_peers)
            explicitly_included_names = await self._get_names_for_peers(folder.include_peers)
            explicitly_excluded_names = await self._get_names_for_peers(folder.exclude_peers)

            # 2. Get chats that match the folder's rules (e.g., "All Channels")
            rule_based_names = self._get_rule_based_chat_names(folder, all_dialogs)

            # 3. Combine and de-duplicate the included lists
            # A folder's total included chats are the union of explicit adds and rule-based matches.
            combined_included_set = set(explicitly_included_names) | set(rule_based_names)

            # 4. Final included list is the combined list MINUS the explicitly excluded ones
            final_included_names = sorted([
                name for name in combined_included_set 
                if name not in explicitly_excluded_names
            ])

            extracted_data.append({
                'folder_name': folder.title.text, 'folder_id': folder.id, 'emoticon': folder.emoticon or "None",
                'pinned_chats': pinned_names,
                'included_chats': final_included_names,
                'excluded_chats': explicitly_excluded_names,
                'rule_contacts': folder.contacts, 'rule_non_contacts': folder.non_contacts,
                'rule_groups': folder.groups, 'rule_channels': folder.broadcasts, 'rule_bots': folder.bots,
                'rule_exclude_muted': folder.exclude_muted, 'rule_exclude_read': folder.exclude_read,
                'rule_exclude_archived': folder.exclude_archived
            })

        if extracted_data:
            self._export_data(extracted_data, self.config['default_folder_output'])
        else:
            print("No folders were selected or processed.")

    def _export_data(self, data: list[dict], base_filename: str):
        """Handles the final export to either CSV or JSON."""
        if not data:
            logging.warning("Export called with no data. Nothing to do.")
            return
            
        print("\n--- Export Data ---")
        print("  1. CSV (Recommended for spreadsheets like LibreOffice Calc)")
        print("  2. JSON (For developers & archiving)")

        while True:
            choice = input("Enter your choice (1 or 2): ")
            if choice in ('1', '2'):
                break
            print("Invalid input. Please enter 1 or 2.")

        date_str = datetime.now().strftime("%Y-%m-%d")

        if choice == '1':
            filename = f"{base_filename}_{date_str}.csv"
            logging.info(f"Exporting to {filename}...")
            try:
                # To handle lists in CSV, we will join them into a string.
                processed_data = []
                for row in data:
                    processed_row = {}
                    for key, value in row.items():
                        if isinstance(value, list):
                            processed_row[key] = ", ".join(map(str, value))
                        else:
                            processed_row[key] = value
                    processed_data.append(processed_row)

                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
                    writer.writeheader()
                    writer.writerows(processed_data)
                print(f"✅ Successfully exported data to {filename}")
            except IOError as e:
                logging.error(f"❌ Failed to write to CSV file: {e}")

        elif choice == '2':
            filename = f"{base_filename}_{date_str}.json"
            logging.info(f"Exporting to {filename}...")
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Successfully exported data to {filename}")
            except IOError as e:
                logging.error(f"❌ Failed to write to JSON file: {e}")

    async def run(self):
        """Main execution method."""
        try:
            if not await self._handle_login():
                return

            print("✅ Connection to Telegram successful.")
            
            while True:
                print("\n" + "=" * 20 + " MAIN MENU " + "=" * 20)
                print("1. Master Chat List (Extract all chats by type)")
                print("2. Folder Information (Export specific folder data)")
                print("3. Exit")
                
                main_choice = input("Enter your choice: ")

                if main_choice == '1':
                    await self._extract_master_list()
                elif main_choice == '2':
                    await self._extract_folders()
                elif main_choice == '3':
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        
        except KeyboardInterrupt:
            print("\nCaught Ctrl+C, exiting gracefully.")
        except Exception as e:
            logging.error(f"❌ A critical error occurred during operation: {e}")
        finally:
            if self.client.is_connected():
                logging.info("Disconnecting from Telegram.")
                await self.client.disconnect()


def get_config():
    """Reads and validates the config.ini file."""
    config_path = Path('config.ini')
    if not config_path.is_file():
        logging.critical(f"❌ Config file not found at '{config_path}'. Please create it.")
        return None

    parser = configparser.ConfigParser()
    parser.read(config_path)

    try:
        return {
            'api_id': parser.getint('telegram', 'api_id'),
            'api_hash': parser.get('telegram', 'api_hash'),
            'phone_number': parser.get('telegram', 'phone_number'),
            'session_name': parser.get('settings', 'session_name'),
            'default_master_list_output': parser.get('settings', 'default_master_list_output'),
            'default_folder_output': parser.get('settings', 'default_folder_output'),
        }
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.critical(f"❌ Config file is missing a required section or option: {e}")
        return None
    except ValueError:
        logging.critical(f"❌ api_id in config.ini is not a valid number.")
        return None

if __name__ == "__main__":
    app_config = get_config()
    if app_config:
        extractor = TelegramDataExtractor(app_config)
        asyncio.run(extractor.run())