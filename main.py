# main.py
import os
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
        )

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.settings_service.apply_saved_theme()
        self.settings_service.check_first_run_directory()

        self.log("=" * 60, "info")
        self.log("ZEMmacOS Application Started", "info")
        self.log(f"Log file: {self.logger.get_log_file_path()}", "info")
        self.log("=" * 60, "info")

        self.root.after(500, self._show_startup_toast)
        self.root.after(1000, self._auto_fetch)

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
            try:
                catalog = self.settings.get("catalog", "publicrelease")
                self.gib_wrapper = GibMacOSWrapper(callback=self.log)
                success = self.gib_wrapper.initialize(catalog=catalog, maxos=30)

                if not success:
                    self.log("Failed to fetch catalogue. Check your internet connection.", "error")
                    return

                products = self.gib_wrapper.get_product_display_list()
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

            except Exception as e:
                self.log(f"Failed to fetch catalogue: {str(e)}", "error")
            finally:
                with self.fetch_lock:
                    self.fetch_in_progress = False

        threading.Thread(target=fetch, daemon=True).start()

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
                "idm_downloader": idm_downloader
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

                    self.log(f"\U0001f4e6 Downloading package {i}/{len(packages)}: {filename}", "info")

                    headers = {"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"}
                    result = idm_downloader.download(url, filename, download_dir, headers=headers)

                    if result["status"] == "completed":
                        downloaded_count += 1
                        self.log(f"\u2705 Completed package {i}/{len(packages)}", "success")
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
                    else:
                        failed_count += 1
                        self.log(f"\u274c Failed package {i}/{len(packages)}", "error")

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

                self.log("=" * 60, "info")
                if downloaded_count == total_packages:
                    self.log("\u2705 DOWNLOAD COMPLETED SUCCESSFULLY!", "success")
                else:
                    self.log("\u274c DOWNLOAD FAILED OR PARTIAL", "error")
                self.log("=" * 60, "info")

                self._cleanup_download(download_id)
                self.update_button_states()

            except Exception as e:
                self.log(f"\u274c Download error: {str(e)}", "error")
                self.root.after(0, lambda: self.show_toast(f"Download failed: {str(e)[:50]}", "error", 4000))
                self._cleanup_download(download_id)
                self.update_button_states()

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
        states = {"dl_pause_btn": tk.DISABLED, "dl_resume_btn": tk.DISABLED, "dl_cancel_btn": tk.DISABLED}

        if active_id and active_id in self.downloads:
            status = self.downloads[active_id].get("status", "")
            if status == "downloading":
                states["dl_pause_btn"] = tk.NORMAL
                states["dl_cancel_btn"] = tk.NORMAL
            elif status == "paused":
                states["dl_resume_btn"] = tk.NORMAL
                states["dl_cancel_btn"] = tk.NORMAL

        for btn, state in states.items():
            if hasattr(self, btn):
                getattr(self, btn).config(state=state)

    def on_pause_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
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
                self.log("\u25b6 Resuming", "info")
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "downloading"

                def resume():
                    headers = {"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"}
                    downloader = self.idm_downloaders.get(active_id)
                    if downloader:
                        result = downloader.resume(url, filename, save_dir, headers)
                        if result.get("status") == "completed":
                            with self.download_lock:
                                if active_id in self.downloads:
                                    self.downloads[active_id]["status"] = "completed"
                            self.log("\u2705 Download completed!", "success")
                        self._cleanup_download(active_id)
                        self.update_button_states()

                threading.Thread(target=resume, daemon=True).start()
                self.update_button_states()

    def on_cancel_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
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
