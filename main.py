# main.py
import json
import os
import socket
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from main_ui import ZEMmacOSUI
from gib_macos_wrapper import GibMacOSWrapper
from logger import get_logger
from idm_downloader import IDMDownloader
from cleaner import Cleaner
from settings import SettingsManager, AppSettingsService
from update import AppUpdater


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    root.title("ZEMmacOS")
    root.geometry("1200x800")
    root.minsize(1000, 700)
    root.state('zoomed')

    ZEMmacOSApp(root)
    root.mainloop()


class ZEMmacOSApp(ZEMmacOSUI):
    def __init__(self, root):
        super().__init__(root)

        self.settings = SettingsManager()
        self.settings_service = AppSettingsService(self)
        self.updater = AppUpdater()

        self.logger = get_logger()
        self.logger.set_console_callback(self._console_output)

        self._timers = {}

        self.gib_wrapper = None
        self.download_threads = []
        self.cleaner = Cleaner(self)
        self.idm_downloaders = {}
        self.downloads = {}
        self.download_counter = 0
        self.download_lock = threading.Lock()
        self.fetch_lock = threading.Lock()
        self.fetch_in_progress = False

        self.set_callbacks(
            fetch_cb=self.on_fetch_clicked,
            download_cb=self.on_download_clicked,
            clear_cb=self.on_clear_console,
            settings_cb=self.save_settings,
            pause_cb=self.on_pause_download,
            resume_cb=self.on_resume_download,
            cancel_cb=self.on_cancel_download,
            copy_cb=self.on_copy_console,
            clean_cb=self.on_clean_temp,
            clean_logs_cb=self.on_clean_logs,
            theme_toggle_cb=self.toggle_theme,
            check_updates_cb=self.check_for_updates,
            retry_cb=self.on_retry_download,
        )

        self._network_pause_event = threading.Event()
        self._current_dialog_download_id = None
        self._max_retry_action = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.settings_service.apply_saved_theme()
        self.settings_service.check_first_run_directory()

        self.debug_log("APP", "SYSTEM", "Application starting...")
        self.debug_log("PERFORMANCE", "INFO", "ZEMmacOS v3.0", f"Python {sys.version}")
        self.log("=" * 60, "info")
        self.log("ZEMmacOS Application Started", "info")
        self.log(f"Log file: {self.logger.get_log_file_path()}", "info")
        self.log("=" * 60, "info")

        self.root.after(500, self._show_startup_toast)
        self.root.after(1000, self._auto_fetch)

    def check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def _show_startup_toast(self):
        self.show_toast("ZEMmacOS started successfully", "success", 2500)

    def _console_output(self, message, level):
        if hasattr(self, 'console'):
            self.console.append(message, level)

    def log(self, message, level="info"):
        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "success":
            self.logger.success(message)
        else:
            self.logger.info(message)

    def save_settings(self):
        if self.settings_service.save_ui_values():
            messagebox.showinfo("Success", "Settings saved successfully!")

    def _auto_fetch(self):
        self.log("Auto-fetching catalogue...", "info")
        self.on_fetch_clicked()

    def on_fetch_clicked(self):
        with self.fetch_lock:
            if self.fetch_in_progress:
                self.log("Catalogue fetch already in progress. Please wait...", "warning")
                return
            self.fetch_in_progress = True

        if hasattr(self, 'version_listbox'):
            self.version_listbox.delete(0, tk.END)
            self.version_listbox.insert(tk.END, "Fetching catalogue from Apple...")

        self.log("=" * 60, "info")
        self.log("FETCHING macOS CATALOGUE FROM APPLE", "info")
        self.log("=" * 60, "info")

        def fetch():
            retry_count = 0
            max_retries = 10
            self._network_pause_event.clear()
            self.debug_log("CATALOGUE", "INFO", "Catalogue fetch thread started")

            while True:
                try:
                    catalog = self.settings.get("catalog", "publicrelease")
                    self.debug_log("CATALOGUE", "INFO", f"Fetching catalogue: {catalog}")
                    self.debug_log("PERFORMANCE", "INFO", "Catalogue fetch - DNS lookup starting")
                    t0 = time.time()

                    self.gib_wrapper = GibMacOSWrapper(callback=self.log)
                    success = self.gib_wrapper.initialize(catalog=catalog, maxos=30)

                    t1 = time.time()
                    self.debug_log("PERFORMANCE", "INFO", f"Catalogue fetch - connection + download",
                                   f"{t1 - t0:.1f}s")

                    if not success:
                        self.debug_log("CATALOGUE", "ERROR", "Catalogue returned no results")
                        raise ConnectionError("Catalogue fetch returned no results")

                    products = self.gib_wrapper.get_product_display_list()
                    t2 = time.time()
                    self.debug_log("PERFORMANCE", "INFO", "Catalogue fetch - parse complete",
                                   f"Parse: {t2 - t1:.1f}s | Total: {t2 - t0:.1f}s")
                    self.debug_log("CATALOGUE", "SUCCESS", f"Found {len(products)} macOS versions")
                    self.root.after(0, self._update_version_list, products)
                    self.root.after(0, lambda: self.show_toast(f"Found {len(products)} macOS versions", "info", 3000))

                    self.log(" ", "output")
                    self.log("=" * 60, "info")
                    self.log(f"\u2713 CATALOGUE FETCH COMPLETED - Found {len(products)} versions", "success")
                    self.log("=" * 60, "info")
                    self.log(" ", "output")
                    self.log("INSTRUCTIONS:", "info")
                    self.log("1. Find the number next to the macOS version you want", "output")
                    self.log("2. Enter that number in the input box above", "output")
                    self.log("3. Press ENTER or click DOWNLOAD SELECTED to start downloading", "output")
                    self.log(" ", "output")
                    self.log("NOTE: Each macOS version contains MULTIPLE packages (5GB-12GB total)", "warning")
                    self.log("The downloader will download ALL packages sequentially.", "info")

                    self.root.after(0, self._close_network_dialog)
                    self.root.after(0, lambda: self.set_fetch_state(False))
                    with self.fetch_lock:
                        self.fetch_in_progress = False
                    return

                except Exception as e:
                    retry_count += 1
                    self.debug_log("NETWORK", "WARNING", "Internet disconnected",
                                   f"Fetch attempt {retry_count}/{max_retries}: {str(e)[:80]}")
                    self.debug_log("NETWORK", "INFO", f"Retry scheduled (30s) - retry {retry_count}/{max_retries}")

                    if retry_count > max_retries:
                        self.debug_log("NETWORK", "ERROR", "All 10 retries exhausted for fetch")
                        self.log("\u26a0 Catalogue fetch failed after 10 retries.", "error")
                        self._max_retry_action = None
                        self.root.after(0, lambda: self._update_to_max_retry_dialog(
                            on_resume_cb=self._on_fetch_max_retry_resume,
                            on_cancel_cb=self._on_fetch_max_retry_cancel,
                            on_keep_waiting_cb=self._on_fetch_max_retry_keep_waiting
                        ))
                        self._network_pause_event.clear()
                        while self._max_retry_action is None:
                            if self._network_pause_event.wait(timeout=5):
                                break
                            if self.check_internet():
                                self._max_retry_action = "resume"
                                break
                        action = self._max_retry_action
                        self._max_retry_action = None
                        if action == "resume":
                            retry_count = 0
                            self.debug_log("NETWORK", "SUCCESS", "Internet restored - resuming fetch retries")
                            self.root.after(0, self._auto_close_network_dialog)
                            continue
                        elif action == "cancel":
                            break
                        elif action == "keep_waiting":
                            retry_count = 0
                            continue
                        else:
                            break

                    self.debug_log("NETWORK", "INFO", f"Retry {retry_count}/{max_retries} - waiting 30s")
                    self.log(f"\U0001f504 Fetch retry {retry_count}/{max_retries} in 30s...", "warning")
                    self.root.after(0, lambda rc=retry_count: self._show_network_dialog(
                        rc, self._on_net_pause_fetch, self._on_fetch_retry_now
                    ))

                    # Poll for internet or user action every 1s for up to 30s
                    self._network_pause_event.clear()
                    user_paused = False
                    for remaining in range(30, 0, -1):
                        self.root.after(0, lambda s=remaining: self._update_dialog_countdown(s))
                        if self._network_pause_event.wait(timeout=1):
                            if self._max_retry_action == "retry_now":
                                self._max_retry_action = None
                                self.debug_log("NETWORK", "INFO", "User triggered retry now")
                                break
                            self.log("\u23f8 Fetch paused by user", "warning")
                            self.root.after(0, self._close_network_dialog)
                            user_paused = True
                            break
                        if self.check_internet():
                            self.debug_log("NETWORK", "SUCCESS", "Internet restored")
                            self.debug_log("NETWORK", "INFO", "Auto resume started")
                            self.root.after(0, self._auto_close_network_dialog)
                            break
                    if user_paused:
                        break

            self.root.after(0, lambda: self.set_fetch_state(False))
            with self.fetch_lock:
                self.fetch_in_progress = False

        threading.Thread(target=fetch, daemon=True).start()

    def _on_net_pause_fetch(self):
        self._network_pause_event.set()

    def _on_fetch_retry_now(self):
        self._max_retry_action = "retry_now"
        self._network_pause_event.set()

    def _on_fetch_max_retry_resume(self):
        self._max_retry_action = "resume"
        self._network_pause_event.set()

    def _on_fetch_max_retry_cancel(self):
        self._max_retry_action = "cancel"
        self._network_pause_event.set()

    def _on_fetch_max_retry_keep_waiting(self):
        self._max_retry_action = "keep_waiting"
        self._network_pause_event.set()

    def _update_version_list(self, products):
        if hasattr(self, 'version_listbox'):
            self.version_listbox.delete(0, tk.END)
            for product in products:
                self.version_listbox.insert(tk.END, product)

    def check_for_updates(self):
        def check():
            self.log("Checking for updates...", "info")
            result = self.updater.check_for_updates()

            if result.get("error"):
                self.root.after(0, lambda: messagebox.showerror("Update Error", result["error"]))
            elif result.get("update_available"):
                msg = f"New Update Available!\n\nVersion {result['latest_version']} is available.\n\nWould you like to open the website to download?"
                def ask():
                    if messagebox.askyesno("Update Available", msg):
                        import webbrowser
                        webbrowser.open("https://www.websmithdigital.com")
                self.root.after(0, ask)
            else:
                self.root.after(0, lambda: messagebox.showinfo("Up to Date", "Software is up to date."))

        threading.Thread(target=check, daemon=True).start()

    def on_download_clicked(self):
        index_str = self.index_entry.get().strip() if hasattr(self, 'index_entry') else ""

        if not index_str:
            return

        if not index_str.isdigit():
            return

        dl_dir = self.settings.get("download_directory")
        if not dl_dir:
            messagebox.showwarning("Directory Required", "Please set a download directory in Settings first.")
            self.show_settings()
            return

        idx = int(index_str)
        if hasattr(self, 'gib_wrapper') and self.gib_wrapper and self.gib_wrapper.initialized:
            if idx < 1 or idx > len(self.gib_wrapper.products):
                messagebox.showerror("Invalid Index", f"Index must be between 1 and {len(self.gib_wrapper.products)}")
                return

        # Auto-select and highlight in version listbox
        if hasattr(self, 'version_listbox') and self.version_listbox.size() > 0:
            try:
                idx_int = int(index_str) - 1
                if 0 <= idx_int < self.version_listbox.size():
                    self.version_listbox.selection_clear(0, tk.END)
                    self.version_listbox.selection_set(idx_int)
                    self.version_listbox.activate(idx_int)
                    self.version_listbox.see(idx_int)
            except (ValueError, tk.TclError):
                pass

        self._download_macos_version(index_str)
        if hasattr(self, 'index_entry'):
            self.index_entry.delete(0, tk.END)

    def _download_macos_version(self, index_str):
        if not self.gib_wrapper or not self.gib_wrapper.initialized:
            self.log("No catalogue loaded. Click FETCH CATALOGUE first.", "error")
            messagebox.showerror("Error", "Please fetch catalogue first")
            return

        try:
            index = int(index_str)
        except ValueError:
            self.log(f"Invalid index: {index_str}. Please enter a number.", "error")
            return

        if index < 1 or index > len(self.gib_wrapper.products):
            self.log(f"Invalid index: {index}. Choose 1-{len(self.gib_wrapper.products)}", "error")
            return

        product = self.gib_wrapper.products[index - 1]
        packages = product.get("packages", [])

        if not packages:
            self.log("No download packages found for this version", "error")
            return

        product_name = f"{product.get('title', 'macOS')}_{product.get('version', 'unknown')}_{product.get('build', 'unknown')}"
        product_name = product_name.replace(" ", "_").replace("/", "_").replace(":", "_")

        base_download_dir = self.settings.get("download_directory")
        if not base_download_dir:
             base_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "macOS")

        download_dir = os.path.join(base_download_dir, product_name)
        num_threads = int(self.settings.get("download_threads", 8))

        with self.download_lock:
            self.download_counter += 1
            download_id = f"macOS_{self.download_counter}_{int(time.time())}"

        self.debug_log("DOWNLOAD", "INFO", "Download requested",
                       f"Index: {index} | Product: {product.get('title')} {product.get('version')}")
        self.debug_log("DOWNLOAD", "INFO", f"Total packages: {len(packages)} | Threads: {num_threads}")
        self.debug_log("PERFORMANCE", "INFO", "Download start sequence initiated")
        self.root.after(0, lambda: self.show_toast(f"Downloading: {product.get('title')} {product.get('version')}", "info", 3000))
        self.log("=" * 60, "info")
        self.log(f"\U0001f4e5 DOWNLOADING: {product.get('title')} {product.get('version')}", "info")
        self.log(f"\U0001f4e6 Total packages: {len(packages)}", "info")
        self.log(f"\U0001f4c1 Save to: {download_dir}", "output")
        self.log("=" * 60, "info")

        idm_downloader = IDMDownloader(
            callback=lambda data: self._handle_idm_callback(download_id, data),
            num_threads=num_threads
        )

        with self.download_lock:
            self.idm_downloaders[download_id] = idm_downloader
            self.downloads[download_id] = {
                "product": product,
                "packages": packages,
                "download_dir": download_dir,
                "product_name": product_name,
                "status": "downloading",
                "current_package": 0,
                "total_packages": len(packages),
                "start_time": time.time(),
                "url": None,
                "idm_downloader": idm_downloader,
                "retry_count": 0,
                "connection_lost": False,
            }

        def start_download():
            try:
                os.makedirs(download_dir, exist_ok=True)
                downloaded_count = 0
                failed_count = 0

                for i, pkg in enumerate(packages, 1):
                    with self.download_lock:
                        if self.downloads.get(download_id, {}).get("status") == "cancelled":
                            break

                    url = pkg.get("URL")
                    if not url:
                        self.log(f"\u26a0 Package {i}/{len(packages)} has no URL - skipping", "warning")
                        failed_count += 1
                        continue

                    filename = os.path.basename(url)
                    if not filename:
                        filename = f"package_{i}.pkg"

                    with self.download_lock:
                        if download_id in self.downloads:
                            self.downloads[download_id]["current_package"] = i
                            self.downloads[download_id]["url"] = url

                    self.debug_log("DOWNLOAD", "INFO", f"Package {i}/{len(packages)}: {filename}")
                    self.debug_log("NETWORK", "INFO", f"URL: {url[:120]}...")
                    pkg_t0 = time.time()

                    headers = {"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"}
                    result = idm_downloader.download(url, filename, download_dir, headers=headers)
                    pkg_t1 = time.time()

                    self.debug_log("PERFORMANCE", "INFO", f"Package {i} completed",
                                   f"Duration: {pkg_t1 - pkg_t0:.1f}s | Status: {result['status']}")

                    if result["status"] == "completed":
                        downloaded_count += 1
                        self.log(f"\u2705 Completed package {i}/{len(packages)}", "success")
                        self.root.after(0, self._close_network_dialog)
                        self.debug_log("DOWNLOAD", "SUCCESS", f"Package {i}/{len(packages)} completed")
                        self.debug_log("DOWNLOAD", "SUCCESS", "Download continued successfully")
                        with self.download_lock:
                            if download_id in self.downloads:
                                self.downloads[download_id]["retry_count"] = 0
                    elif result["status"] == "paused":
                        self.log(f"\u23f8 Package {i}/{len(packages)} paused", "warning")
                        with self.download_lock:
                            if download_id in self.downloads:
                                self.downloads[download_id]["status"] = "paused"
                        self.root.after(0, self.update_button_states)
                        return
                    elif result["status"] == "cancelled":
                        self.log(f"\u23f9 Package {i}/{len(packages)} cancelled", "warning")
                        break
                    elif result["status"] == "failed":
                        err = result.get("error", "")
                        is_network_error = any(word in err.lower() for word in
                            ["connectionerror", "timeout", "connection", "reset", "refused",
                             "resolve", "network", "eof", "read timed out"])

                        if is_network_error:
                            with self.download_lock:
                                if download_id in self.downloads:
                                    dl_retry_count = self.downloads[download_id].get("retry_count", 0) + 1
                                    self.downloads[download_id]["retry_count"] = dl_retry_count
                                    self.downloads[download_id]["connection_lost"] = True
                                    self.downloads[download_id]["status"] = "retrying"

                            self.debug_log("NETWORK", "WARNING", "Internet disconnected",
                                           f"Download attempt {dl_retry_count}/10: {err[:80]}")
                            self.debug_log("NETWORK", "INFO", f"Retry scheduled (30s) - retry {dl_retry_count}/10")
                            idm_downloader.clear_state(url)

                            if dl_retry_count == 1:
                                self._current_dialog_download_id = download_id
                                self._network_pause_event.clear()
                                self.root.after(0, lambda rc=1: self._show_network_dialog(
                                    rc, self._on_net_pause_download, self._on_download_retry_now
                                ))

                            if dl_retry_count <= 10:
                                self.debug_log("NETWORK", "INFO", f"Retry {dl_retry_count}/10 - waiting 30s")
                                self.log(f"\U0001f504 Network issue - retry {dl_retry_count}/10 in 30s...", "warning")
                                self.root.after(0, lambda rc=dl_retry_count, fn=filename:
                                    self.update_download_progress(0, 0, 0, 0, 0, fn, "retrying"))
                                self.root.after(0, lambda rc=dl_retry_count:
                                    self._update_network_dialog(rc))

                                self._network_pause_event.clear()
                                user_paused = False
                                for remaining in range(30, 0, -1):
                                    self.root.after(0, lambda s=remaining: self._update_dialog_countdown(s))
                                    if self._network_pause_event.wait(timeout=1):
                                        if self._max_retry_action == "retry_now":
                                            self._max_retry_action = None
                                            self.debug_log("NETWORK", "INFO", "User triggered retry now")
                                            break
                                        self.log("\u23f8 Download paused by user via network dialog", "warning")
                                        self.root.after(0, self._close_network_dialog)
                                        with self.download_lock:
                                            if download_id in self.downloads:
                                                self.downloads[download_id]["status"] = "paused"
                                        self.root.after(0, self.update_button_states)
                                        user_paused = True
                                        break
                                    if self.check_internet():
                                        self.debug_log("NETWORK", "SUCCESS", "Internet restored")
                                        self.debug_log("NETWORK", "INFO", "Auto resume started")
                                        self.root.after(0, self._auto_close_network_dialog)
                                        break
                                if user_paused:
                                    return

                                i -= 1
                                with self.download_lock:
                                    if download_id in self.downloads:
                                        self.downloads[download_id]["status"] = "downloading"
                                continue
                            else:
                                self.debug_log("NETWORK", "ERROR", "All 10 retries exhausted",
                                               "Download paused automatically")
                                self.log("\u26a0 Internet connection lost. Download paused.", "error")
                                self.root.after(0, lambda f=filename: self.update_download_progress(
                                    0, 0, 0, 0, 0, f, "paused"))

                                self._max_retry_action = None
                                self.root.after(0, lambda: self._update_to_max_retry_dialog(
                                    on_resume_cb=self._on_download_max_retry_resume,
                                    on_cancel_cb=self._on_download_max_retry_cancel,
                                    on_keep_waiting_cb=self._on_download_max_retry_keep_waiting
                                ))
                                self._network_pause_event.clear()
                                while self._max_retry_action is None:
                                    if self._network_pause_event.wait(timeout=5):
                                        break
                                    if self.check_internet():
                                        self._max_retry_action = "resume"
                                        break
                                action = self._max_retry_action
                                self._max_retry_action = None
                                if action == "resume":
                                    self.debug_log("NETWORK", "SUCCESS", "Internet restored - resuming download")
                                    self.root.after(0, self._auto_close_network_dialog)
                                    idm_downloader.clear_state(url)
                                    with self.download_lock:
                                        if download_id in self.downloads:
                                            self.downloads[download_id]["retry_count"] = 0
                                            self.downloads[download_id]["status"] = "downloading"
                                    i -= 1
                                    continue
                                elif action == "cancel":
                                    self.log("\u274c Download cancelled after max retries", "warning")
                                    with self.download_lock:
                                        if download_id in self.downloads:
                                            self.downloads[download_id]["status"] = "cancelled"
                                    break
                                elif action == "keep_waiting":
                                    with self.download_lock:
                                        if download_id in self.downloads:
                                            self.downloads[download_id]["retry_count"] = 0
                                            self.downloads[download_id]["status"] = "downloading"
                                    i -= 1
                                    continue
                                else:
                                    with self.download_lock:
                                        if download_id in self.downloads:
                                            self.downloads[download_id]["status"] = "paused"
                                    self.root.after(0, self.update_button_states)
                                    return
                        else:
                            failed_count += 1
                            self.log(f"\u274c Failed package {i}/{len(packages)}: {err[:80]}", "error")

                total_packages = len(packages)
                with self.download_lock:
                    if download_id in self.downloads:
                        if self.downloads[download_id].get("status") != "cancelled":
                            if failed_count == 0 and downloaded_count == total_packages:
                                self.downloads[download_id]["status"] = "completed"
                            elif downloaded_count > 0:
                                self.downloads[download_id]["status"] = "partial"
                            else:
                                self.downloads[download_id]["status"] = "failed"

                self.debug_log("DOWNLOAD", "INFO", "Download thread finished",
                               f"Completed: {downloaded_count}/{total_packages} | Failed: {failed_count}")
                self.log("=" * 60, "info")
                if downloaded_count == total_packages:
                    self.debug_log("DOWNLOAD", "SUCCESS", "All packages downloaded successfully")
                    self.log("\u2705 DOWNLOAD COMPLETED SUCCESSFULLY!", "success")
                else:
                    self.debug_log("DOWNLOAD", "WARNING", f"Download partial/fail: {downloaded_count}/{total_packages} packages")
                    self.log("\u274c DOWNLOAD FAILED OR PARTIAL", "error")
                self.log("=" * 60, "info")

                self.root.after(0, self._close_network_dialog)
                self._cleanup_download(download_id)
                self.update_button_states()
                if hasattr(self, 'index_entry'):
                    self.root.after(100, self.index_entry.focus_set)

            except Exception as e:
                self.log(f"\u274c Download error: {str(e)}", "error")
                self.root.after(0, lambda: self.show_toast(f"Download failed: {str(e)[:50]}", "error", 4000))
                self._cleanup_download(download_id)
                self.update_button_states()
                if hasattr(self, 'index_entry'):
                    self.root.after(100, self.index_entry.focus_set)

        thread = threading.Thread(target=start_download, daemon=True)
        thread.start()
        with self.download_lock:
            self.download_threads.append(thread)

    def _handle_idm_callback(self, download_id, data):
        if isinstance(data, dict):
            if data.get("type") == "progress":
                percentage = data.get("percentage", 0)
                downloaded = data.get("downloaded", 0)
                total = data.get("total", 0)
                speed = data.get("speed", 0)
                eta = data.get("eta", 0)
                filename = data.get("filename", "Unknown")
                status = data.get("status", "downloading")

                with self.download_lock:
                    if download_id in self.downloads:
                        old_status = self.downloads[download_id].get("status")
                        if status == "completed":
                            self.downloads[download_id]["status"] = "completed"
                            if old_status != "completed":
                                self.root.after(0, lambda: self.show_toast(f"Download completed: {filename}", "success", 4000))
                        elif status == "downloading" and old_status != "paused":
                            self.downloads[download_id]["status"] = "downloading"

                self.update_download_progress(percentage, downloaded, total, speed, eta, filename, status)

                if percentage > 0 and int(percentage) % 25 == 0 and not hasattr(self, f"_logged_{int(percentage)}_{download_id}"):
                    self.debug_log("DOWNLOAD", "INFO", f"Progress: {percentage:.0f}% | Speed: {speed/1024/1024:.1f} MB/s",
                                   f"Downloaded: {downloaded}/{total} bytes | ETA: {eta:.0f}s")
                    setattr(self, f"_logged_{int(percentage)}_{download_id}", True)

                if hasattr(self, 'console') and percentage > 0:
                    bar_length = 25
                    filled = int(bar_length * percentage / 100)
                    bar = "\u2588" * filled + "\u2591" * (bar_length - filled)
                    speed_str = f"{speed/1024/1024:.1f} MB/s" if speed > 0 else "0 B/s"
                    eta_str = f"{int(eta//60)}:{int(eta%60):02d}" if eta > 0 else "--:--"
                    self._direct_console_update(f"[{bar}] {percentage:.1f}% | {speed_str} | ETA: {eta_str}", "progress")

                self.update_button_states()

            elif data.get("type") == "log":
                self.log(data.get("message", ""), data.get("level", "info"))

    def _direct_console_update(self, message, level="progress"):
        if hasattr(self, 'console') and self.console.is_valid():
            try:
                self.console.update_progress_line(message)
            except Exception:
                self.console.append(message, level)

    def update_button_states(self):
        active_id = self._get_active_download_id()
        states = {"dl_pause_btn": tk.DISABLED, "dl_resume_btn": tk.DISABLED,
                  "dl_cancel_btn": tk.DISABLED, "dl_retry_btn": tk.DISABLED}

        if active_id and active_id in self.downloads:
            status = self.downloads[active_id].get("status", "")
            if status == "downloading":
                states["dl_pause_btn"] = tk.NORMAL
                states["dl_cancel_btn"] = tk.NORMAL
            elif status == "paused":
                states["dl_resume_btn"] = tk.NORMAL
                states["dl_cancel_btn"] = tk.NORMAL
                states["dl_retry_btn"] = tk.NORMAL

        for btn, state in states.items():
            if hasattr(self, btn):
                getattr(self, btn).config(state=state)

    def on_pause_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
                self.debug_log("DOWNLOAD", "WARNING", "Pause requested",
                               f"Download ID: {active_id}")
                self.debug_log("RESUME", "INFO", "Pausing - saving state")
                self.idm_downloaders[active_id].pause(url)
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "paused"
                self.log("\u23f8 Paused", "warning")
                self.update_button_states()

    def on_resume_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            info = self.downloads.get(active_id, {})
            url = info.get("url")
            filename = os.path.basename(url) if url else ""
            save_dir = info.get("download_dir")

            if url and filename and save_dir:
                self.debug_log("RESUME", "INFO", "Resume requested",
                               f"URL: {url[:80]}...")
                self.debug_log("RESUME", "INFO", "Checking existing file and HTTP Range support")
                self.log("\u25b6 Resuming", "info")
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "downloading"

                def resume():
                    res_t0 = time.time()

                    # Log resume byte position from state file
                    state_file = os.path.join(save_dir, filename + '.idmstate')
                    if os.path.exists(state_file):
                        try:
                            with open(state_file, 'r') as f:
                                state = json.load(f)
                                resume_byte = state.get("downloaded_bytes", 0)
                                self.debug_log("RESUME", "INFO", f"Resume from byte {resume_byte}")
                        except Exception:
                            pass

                    headers = {"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"}
                    downloader = self.idm_downloaders.get(active_id)
                    if not downloader:
                        return

                    self.debug_log("RESUME", "INFO", "Calling IDM downloader.resume()")
                    result = downloader.resume(url, filename, save_dir, headers)
                    res_t1 = time.time()
                    self.debug_log("PERFORMANCE", "INFO", "Resume operation",
                                   f"Duration: {res_t1 - res_t0:.1f}s | Status: {result.get('status', 'unknown')}")

                    if result.get("status") != "completed":
                        self._cleanup_download(active_id)
                        self.update_button_states()
                        return

                    curr_pkg = info.get("current_package", 0)
                    total_pkgs = len(info.get("packages", []))
                    self.log(f"\u2705 Completed package {curr_pkg}/{total_pkgs}", "success")
                    with self.download_lock:
                        if active_id in self.downloads:
                            self.downloads[active_id]["retry_count"] = 0

                    packages = info.get("packages", [])
                    download_dir = info.get("download_dir")
                    downloaded_count = curr_pkg

                    for i, pkg in enumerate(packages, 1):
                        if i <= curr_pkg:
                            continue

                        pkg_url = pkg.get("URL")
                        if not pkg_url:
                            continue

                        pkg_filename = os.path.basename(pkg_url) or f"package_{i}.pkg"

                        with self.download_lock:
                            if active_id in self.downloads:
                                self.downloads[active_id]["current_package"] = i
                                self.downloads[active_id]["url"] = pkg_url

                        self.debug_log("DOWNLOAD", "INFO", f"Package {i}/{total_pkgs}: {pkg_filename}")
                        self.debug_log("NETWORK", "INFO", f"URL: {pkg_url[:120]}...")

                        pkg_result = downloader.download(pkg_url, pkg_filename, download_dir, headers)

                        if pkg_result["status"] == "completed":
                            downloaded_count += 1
                            self.log(f"\u2705 Completed package {i}/{total_pkgs}", "success")
                            self.root.after(0, self._close_network_dialog)
                            self.debug_log("DOWNLOAD", "SUCCESS", "Download continued successfully")
                            with self.download_lock:
                                if active_id in self.downloads:
                                    self.downloads[active_id]["retry_count"] = 0
                        elif pkg_result["status"] == "paused":
                            self.log(f"\u23f8 Package {i}/{total_pkgs} paused", "warning")
                            with self.download_lock:
                                if active_id in self.downloads:
                                    self.downloads[active_id]["status"] = "paused"
                            self.root.after(0, self.update_button_states)
                            return
                        elif pkg_result["status"] == "cancelled":
                            self.log(f"\u23f9 Package {i}/{total_pkgs} cancelled", "warning")
                            break
                        elif pkg_result["status"] == "failed":
                            err = pkg_result.get("error", "")
                            is_network_error = any(word in err.lower() for word in
                                ["connectionerror", "timeout", "connection", "reset", "refused",
                                 "resolve", "network", "eof", "read timed out"])
                            if is_network_error:
                                self.debug_log("NETWORK", "WARNING", f"Network error during resume continuation: {err[:100]}")
                                self.log(f"\U0001f504 Network issue - retrying package {i}/{total_pkgs}...", "warning")
                                downloader.clear_state(pkg_url)
                                # Poll internet every 5s for up to 30s
                                for _ in range(6):
                                    if self.check_internet():
                                        self.debug_log("NETWORK", "SUCCESS", "Internet restored during resume")
                                        self.root.after(0, self._auto_close_network_dialog)
                                        break
                                    time.sleep(5)
                                else:
                                    self.log(f"\u274c Package {i}/{total_pkgs} failed after resume timeout", "error")
                                    failed_count += 1
                                    continue
                                i -= 1
                                continue
                            else:
                                failed_count += 1
                                self.log(f"\u274c Failed package {i}/{total_pkgs}: {err[:80]}", "error")

                    with self.download_lock:
                        if active_id in self.downloads:
                            if downloaded_count == total_pkgs:
                                self.downloads[active_id]["status"] = "completed"
                            elif downloaded_count > 0:
                                self.downloads[active_id]["status"] = "partial"
                            else:
                                self.downloads[active_id]["status"] = "failed"

                    if downloaded_count == total_pkgs:
                        self.log("\u2705 DOWNLOAD COMPLETED SUCCESSFULLY!", "success")
                    else:
                        self.log(f"\u274c DOWNLOAD PARTIAL: {downloaded_count}/{total_pkgs} packages", "error")

                    self.root.after(0, self._close_network_dialog)
                    self._cleanup_download(active_id)
                    self.update_button_states()

                threading.Thread(target=resume, daemon=True).start()
                self.update_button_states()

    def _on_net_pause_download(self):
        self._network_pause_event.set()
        with self.download_lock:
            did = self._current_dialog_download_id
            if did and did in self.downloads:
                url = self.downloads[did].get("url")
                if url and did in self.idm_downloaders:
                    self.idm_downloaders[did].pause(url)

    def _on_download_retry_now(self):
        self._max_retry_action = "retry_now"
        self._network_pause_event.set()

    def _on_download_max_retry_resume(self):
        self._max_retry_action = "resume"
        self._network_pause_event.set()

    def _on_download_max_retry_cancel(self):
        self._max_retry_action = "cancel"
        self._network_pause_event.set()

    def _on_download_max_retry_keep_waiting(self):
        self._max_retry_action = "keep_waiting"
        self._network_pause_event.set()

    def on_retry_download(self):
        self._close_network_dialog()
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            info = self.downloads.get(active_id, {})
            url = info.get("url")
            if url:
                self.debug_log("DOWNLOAD", "INFO", "Manual retry",
                               f"Clearing state for: {url[:60]}...")
                self.idm_downloaders[active_id].clear_state(url)
            with self.download_lock:
                if active_id in self.downloads:
                    self.downloads[active_id]["retry_count"] = 0
                    self.downloads[active_id]["status"] = "downloading"
            self.log("\U0001f504 Retrying download...", "info")
            self.log("\U0001f4e6 Retrying download from last position", "info")
            self.on_resume_download()

    def on_cancel_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
                self.debug_log("DOWNLOAD", "WARNING", "Cancel requested",
                               f"Download ID: {active_id}")
                self.idm_downloaders[active_id].cancel(url)
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "cancelled"
                self.log("\u274c Cancelled", "warning")
                self._cleanup_download(active_id)
                self.reset_download_ui()
                self.update_button_states()

    def _get_active_download_id(self):
        with self.download_lock:
            for did, info in self.downloads.items():
                if info.get("status") in ["downloading", "paused"]:
                    return did
        return None

    def _cleanup_download(self, download_id):
        with self.download_lock:
            self.idm_downloaders.pop(download_id, None)
            self.downloads.pop(download_id, None)

    def on_copy_console(self):
        if hasattr(self, '_console_raw'):
            self.root.clipboard_clear()
            self.root.clipboard_append(self._console_raw.get(1.0, tk.END))
            self.log("\U0001f4cb Console content copied", "info")

    def on_clear_console(self):
        if hasattr(self, 'console'):
            self.console.clear()
        self.log("Console cleared", "info")
        with self.fetch_lock:
            self.fetch_in_progress = False
            self.gib_wrapper = None

    def on_clean_temp(self):
        self.log("\U0001f9f9 Cleaning temporary files...", "info")
        pycache_count = self.cleaner.clear_pycache()
        pyc_count = self.cleaner.clear_pyc_files()
        self.cleaner.clear_gibmacos_temp()
        self.log(f"\u2713 \u2705 Cleanup complete ({pycache_count + pyc_count} items)", "success")
        messagebox.showinfo("Cleanup Complete", f"Removed {pycache_count + pyc_count} temporary items")

    def on_clean_logs(self):
        if messagebox.askyesno("Delete All Logs", "\u26a0 WARNING: This will delete ALL log files.\n\nContinue?"):
            self.log("\U0001f5d1 Deleting ALL log files...", "warning")
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            count = 0
            current_log = self.logger.get_log_file_path() if hasattr(self, 'logger') else None

            if os.path.exists(logs_dir):
                for f in os.listdir(logs_dir):
                    if f.endswith(".log"):
                        file_path = os.path.join(logs_dir, f)
                        if current_log and os.path.abspath(file_path) == os.path.abspath(current_log):
                            continue
                        try:
                            os.remove(file_path)
                            count += 1
                        except OSError:
                            pass
            self.log(f"\u2713 \u2705 Deleted {count} log file(s)", "success")
            messagebox.showinfo("Logs Deleted", f"Deleted {count} log files")

    def toggle_theme(self):
        self.settings_service.toggle_and_save_theme()

    def on_closing(self):
        active_downloads = any(info.get("status") in ["downloading", "paused"] for info in self.downloads.values())
        if active_downloads:
            if not messagebox.askyesno("Download Active", "Downloads are in progress. Cancel and exit?"):
                return
            with self.download_lock:
                for did, downloader in self.idm_downloaders.items():
                    try:
                        url = self.downloads.get(did, {}).get("url")
                        if url:
                            downloader.cancel(url)
                    except Exception:
                        pass
        self.log("Application shutting down...", "info")
        self.logger.stop()
        self.root.destroy()


if __name__ == "__main__":
    main()
