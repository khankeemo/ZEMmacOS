# main.py
import os
import socket
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox

import threading as _threading

from main_ui import ZEMmacOSUI
from gib_macos_wrapper import GibMacOSWrapper
from logger import get_logger
from idm_downloader import IDMDownloader
from cleaner import Cleaner
from settings import SettingsManager, AppSettingsService
from update import AppUpdater
from SDK_ZEM_MAC_OS_prod_zemmacos import LicenseEngine, WelcomeDialog
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


NETWORK_ERROR_KEYWORDS = [
    "connectionerror", "timeout", "connection", "reset", "refused",
    "resolve", "network", "eof", "read timed out",
    "chunkedencodingerror", "remotedisconnected",
    "connectionabortederror", "connectionreseterror",
]


def _is_network_error_str(err_str):
    low = err_str.lower()
    return any(k in low for k in NETWORK_ERROR_KEYWORDS)


class ZEMmacOSApp(ZEMmacOSUI):
    def __init__(self, root, settings=None):
        super().__init__(root)

        self.settings = settings or SettingsManager()
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
        )

        self._network_monitor_running = False
        self._network_monitor_stop = threading.Event()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.settings_service.apply_saved_theme()
        self.settings_service.check_first_run_directory()

        self.debug_log("APP", "SYSTEM", "Application starting...")
        self.debug_log("PERFORMANCE", "INFO", "ZEMmacOS v3.0", f"Python {sys.version}")
        self.log("=" * 60, "info")
        self.log("ZEMmacOS Application Started", "info")
        self.log(f"Log file: {self.logger.get_log_file_path()}", "info")
        self.log("=" * 60, "info")

        self.show_dashboard()

        self.root.after(500, self._show_startup_toast)
        self.root.after(1000, self._auto_fetch)
        self.root.after(2000, self._check_internet_on_startup)
        self.root.after(3000, self._start_license_system)
        self._start_network_monitor()

    # -----------------------------------------------------------------
    # LICENSE SYSTEM — SDK initialization + welcome flow
    # -----------------------------------------------------------------
    def _start_license_system(self):
        _threading.Thread(target=self._init_license_worker, daemon=True).start()

    def _init_license_worker(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base, 'SDK_ZEM_MAC_OS_prod_zemmacos', 'config', 'api-config.json')
            engine = LicenseEngine(config_path=config_path)
            status = engine.initialize()
            self.root.after(0, lambda: self._on_license_init(engine, status))
        except Exception as e:
            self.log(f"License init: {e}", "warning")
            self.root.after(0, lambda: self.log("License system unavailable - app runs unlicensed", "warning"))

    def _on_license_init(self, engine, status):
        self.license_engine = engine
        self.set_license_engine(engine)
        self.debug_log("LICENSE", "INFO", f"SDK status: {status.status}")
        if status.status in ('active', 'trial'):
            msg = f"License: {status.status.upper()} — {status.days_remaining}d remaining"
            if status.plan:
                msg += f" ({status.plan})"
            self.log(msg, "success")
            return
        self.log("No active license — starting onboarding", "info")
        self.root.after(1000, self._show_welcome_dialog)

    def _show_welcome_dialog(self):
        try:
            engine = getattr(self, 'license_engine', None)
            if not engine:
                return
            client = engine._client
            cache = engine._cache
            dialog = WelcomeDialog(client, product_name='ZEMmacOS', cache=cache)
            if dialog.is_onboarding_complete():
                self.log("Onboarding already completed (cached)", "info")
                return
            result = dialog.show()
            if result.get('onboarding_complete'):
                self.log("Onboarding complete — trial started", "success")
                self.license_engine.initialize()
                self.set_license_engine(self.license_engine)
                self.refresh_license_widgets()
            elif result.get('skipped'):
                self.log("Onboarding skipped", "info")
        except Exception as e:
            self.log(f"Welcome dialog: {e}", "warning")

    # -----------------------------------------------------------------
    # NETWORK MONITOR — runs continuously in background
    # -----------------------------------------------------------------
    def _start_network_monitor(self):
        if self._network_monitor_running:
            return
        self._network_monitor_running = True
        self._network_monitor_stop.clear()
        self._net_dialog_open = False

        def monitor():
            while not self._network_monitor_stop.is_set():
                online = self.check_internet()
                has_active_download = False
                with self.download_lock:
                    for info in self.downloads.values():
                        if info.get("status") in ("downloading", "retrying", "network_error"):
                            has_active_download = True
                            break

                if not online and has_active_download and not self._net_dialog_open:
                    self._net_dialog_open = True
                    self.debug_log("NETWORK", "WARNING", "Internet lost - opening dialog")
                    self.root.after(0, lambda: self._show_network_dialog(1, self._on_net_pause_download))
                elif not online and not has_active_download and self._net_dialog_open:
                    self._net_dialog_open = False
                    self.root.after(0, self._close_network_dialog)
                elif online and self._net_dialog_open:
                    self._net_dialog_open = False
                    self.root.after(0, self._auto_close_network_dialog)

                for _ in range(5):
                    if self._network_monitor_stop.is_set():
                        return
                    time.sleep(1)

        threading.Thread(target=monitor, daemon=True).start()

    def _stop_network_monitor(self):
        self._network_monitor_stop.set()

    # -----------------------------------------------------------------
    # INTERNET CHECK
    # -----------------------------------------------------------------
    def check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def _show_startup_toast(self):
        self.show_toast("ZEMmacOS started successfully", "success", 2500)

    def _check_internet_on_startup(self):
        if not self.check_internet():
            self.debug_log("NETWORK", "WARNING", "No internet on startup - showing dialog")
            self.root.after(0, lambda: self._show_network_dialog(0, self._on_net_pause_download))
            self._wait_for_internet_startup()

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

    # -----------------------------------------------------------------
    # FETCH CATALOGUE
    # -----------------------------------------------------------------
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
            self.debug_log("CATALOGUE", "INFO", "Catalogue fetch thread started")

            while True:
                try:
                    catalog = self.settings.get("catalog", "publicrelease")
                    self.debug_log("CATALOGUE", "INFO", f"Fetching catalogue: {catalog}")
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
                    self.log("CATALOGUE FETCH COMPLETED - Found {} versions".format(len(products)), "success")
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

                    if retry_count > max_retries:
                        self.debug_log("NETWORK", "ERROR", "All 10 retries exhausted for fetch")
                        self.log("Catalogue fetch failed after 10 retries.", "error")
                        self.root.after(0, self._close_network_dialog)
                        break

                    self.log(f"Fetch retry {retry_count}/{max_retries} in 30s...", "warning")
                    self.root.after(0, lambda rc=retry_count: self._show_network_dialog(
                        rc, self._on_net_pause_fetch
                    ))

                    for remaining in range(30, 0, -1):
                        with self.fetch_lock:
                            if not self.fetch_in_progress:
                                return
                        self.root.after(0, lambda s=remaining: self._update_dialog_countdown(s))
                        time.sleep(1)
                        if self.check_internet():
                            self.debug_log("NETWORK", "SUCCESS", "Internet restored")
                            self.root.after(0, self._auto_close_network_dialog)
                            break

            self.root.after(0, lambda: self.set_fetch_state(False))
            with self.fetch_lock:
                self.fetch_in_progress = False

        threading.Thread(target=fetch, daemon=True).start()

    def _on_net_pause_fetch(self):
        self.log("Pausing catalogue fetch...", "warning")
        with self.fetch_lock:
            self.fetch_in_progress = False
        self.root.after(0, lambda: self.set_fetch_state(False))
        self.root.after(0, self._close_network_dialog)

    def _update_version_list(self, products):
        if hasattr(self, 'version_listbox'):
            self.version_listbox.delete(0, tk.END)
            for product in products:
                self.version_listbox.insert(tk.END, product)
        if hasattr(self, 'index_entry'):
            self.index_entry.delete(0, tk.END)
            self.root.after(50, self.index_entry.focus_set)

    def _wait_for_internet_startup(self):
        def waiter():
            for _ in range(10):
                self.debug_log("NETWORK", "INFO", "Waiting for internet...")
                for _ in range(30):
                    time.sleep(1)
                    if self.check_internet():
                        self.debug_log("NETWORK", "SUCCESS", "Internet restored on startup")
                        self.root.after(0, self._auto_close_network_dialog)
                        return
            self.debug_log("NETWORK", "WARNING", "Startup retries exhausted - continuing offline")
            self.root.after(0, self._close_network_dialog)

        threading.Thread(target=waiter, daemon=True).start()

    # -----------------------------------------------------------------
    # UPDATE CHECK
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # DOWNLOAD START
    # -----------------------------------------------------------------
    def on_download_clicked(self):
        index_str = self.index_entry.get().strip() if hasattr(self, 'index_entry') else ""

        if not index_str or not index_str.isdigit():
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
            self.root.after(50, self.index_entry.focus_set)

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
        self.root.after(0, lambda: self.show_toast(f"Downloading: {product.get('title')} {product.get('version')}", "info", 3000))
        self.log("=" * 60, "info")
        self.log("DOWNLOADING: {} {}".format(product.get('title'), product.get('version')), "info")
        self.log("Total packages: {}".format(len(packages)), "info")
        self.log("Save to: {}".format(download_dir), "output")
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

        self._run_package_loop(download_id)

    # -----------------------------------------------------------------
    # PACKAGE LOOP
    # -----------------------------------------------------------------
    _package_loop_running = set()

    def _run_package_loop(self, download_id):
        with self.download_lock:
            if download_id in self._package_loop_running:
                return
            self._package_loop_running.add(download_id)

        def loop():
            try:
                with self.download_lock:
                    info = self.downloads.get(download_id, {})
                    if not info:
                        return
                    packages = info.get("packages", [])
                    download_dir = info.get("download_dir")
                    idm_downloader = info.get("idm_downloader")

                if not packages or not download_dir or not idm_downloader:
                    return

                os.makedirs(download_dir, exist_ok=True)

                all_completed = True
                any_failed = False

                i = info.get("current_package", 0) + 1
                total_pkgs = len(packages)

                while i <= total_pkgs:
                    with self.download_lock:
                        if self.downloads.get(download_id, {}).get("status") == "cancelled":
                            break

                    pkg = packages[i - 1]
                    url = pkg.get("URL")
                    if not url:
                        self.log(f"Package {i}/{total_pkgs} has no URL - skipping", "warning")
                        i += 1
                        continue

                    filename = os.path.basename(url)
                    if not filename:
                        filename = f"package_{i}.pkg"

                    with self.download_lock:
                        if download_id in self.downloads:
                            self.downloads[download_id]["current_package"] = i - 1
                            self.downloads[download_id]["url"] = url

                    self.debug_log("DOWNLOAD", "INFO", f"Package {i}/{total_pkgs}: {filename}")

                    retry_count_for_pkg = 0
                    max_retries = 9
                    headers = {"User-Agent": "Mozilla/5.0 ZEMmacOS Downloader"}

                    while retry_count_for_pkg <= max_retries:
                        with self.download_lock:
                            if self.downloads.get(download_id, {}).get("status") == "cancelled":
                                break

                        result = idm_downloader.download(url, filename, download_dir, headers=headers)

                        if result["status"] == "completed":
                            self.log(f"Completed package {i}/{total_pkgs}", "success")
                            self.root.after(0, self._close_network_dialog)
                            with self.download_lock:
                                if download_id in self.downloads:
                                    self.downloads[download_id]["retry_count"] = 0
                            break

                        elif result["status"] == "paused":
                            self.log(f"Package {i}/{total_pkgs} paused", "warning")
                            with self.download_lock:
                                if download_id in self.downloads:
                                    self.downloads[download_id]["status"] = "paused"
                            self.root.after(0, self.update_button_states)
                            return

                        elif result["status"] == "cancelled":
                            self.log(f"Package {i}/{total_pkgs} cancelled", "warning")
                            return

                        elif result["status"] == "network_error":
                            retry_count_for_pkg += 1
                            with self.download_lock:
                                if download_id in self.downloads:
                                    self.downloads[download_id]["retry_count"] = retry_count_for_pkg
                                    self.downloads[download_id]["connection_lost"] = True

                            self.debug_log("NETWORK", "WARNING", "Internet disconnected",
                                           f"Download attempt {retry_count_for_pkg}/{max_retries}")

                            if retry_count_for_pkg == 1:
                                self.root.after(0, lambda: self._show_network_dialog(
                                    retry_count_for_pkg, self._on_net_pause_download
                                ))

                            if retry_count_for_pkg <= max_retries:
                                self.log(f"Network issue - retry {retry_count_for_pkg}/{max_retries} in 30s...", "warning")
                                self.root.after(0, lambda rc=retry_count_for_pkg, fn=filename:
                                    self.update_download_progress(0, 0, 0, 0, 0, fn, "retrying"))
                                self.root.after(0, lambda rc=retry_count_for_pkg:
                                    self._update_network_dialog(rc))

                                waited = 0
                                while waited < 30:
                                    time.sleep(1)
                                    waited += 1
                                    with self.download_lock:
                                        s = self.downloads.get(download_id, {}).get("status")
                                        if s == "paused":
                                            self.log("Paused during retry wait", "warning")
                                            return
                                        if s == "cancelled":
                                            return
                                    self.root.after(0, lambda s=30 - waited: self._update_dialog_countdown(s))
                                    if self.check_internet():
                                        self.debug_log("NETWORK", "SUCCESS", "Internet restored")
                                        self.root.after(0, self._auto_close_network_dialog)
                                        break
                                else:
                                    continue

                                self.log(f"Retrying package {i}/{total_pkgs}...", "info")
                                continue
                            else:
                                self.debug_log("NETWORK", "ERROR", f"All {max_retries} retries exhausted")
                                self.log("Internet connection lost. Download paused.", "error")
                                self.root.after(0, lambda f=filename: self.update_download_progress(
                                    0, 0, 0, 0, 0, f, "paused"))
                                with self.download_lock:
                                    if download_id in self.downloads:
                                        self.downloads[download_id]["retry_count"] = 0
                                        self.downloads[download_id]["status"] = "paused"
                                self._start_auto_resume_watcher(download_id, url, filename, download_dir)
                                self.root.after(0, self.update_button_states)
                                return

                        elif result["status"] == "already_running":
                            retry_count_for_pkg += 1
                            if retry_count_for_pkg <= max_retries:
                                self.log(f"Retrying after stale state ({retry_count_for_pkg}/{max_retries})...", "warning")
                                time.sleep(1)
                                continue
                            else:
                                self.log("Max retries reached for stale state", "error")
                                any_failed = True
                                i += 1
                                break

                        elif result["status"] == "failed":
                            err = result.get("error", "")
                            is_net = _is_network_error_str(err)
                            if is_net:
                                continue
                            else:
                                self.log(f"Failed package {i}/{total_pkgs}: {err[:80]}", "error")
                                any_failed = True
                                i += 1
                                break

                    with self.download_lock:
                        if self.downloads.get(download_id, {}).get("status") == "cancelled":
                            break

                    i += 1

                total_pkgs = len(packages)
                with self.download_lock:
                    if download_id in self.downloads:
                        if self.downloads[download_id].get("status") != "cancelled":
                            if not any_failed:
                                self.downloads[download_id]["status"] = "completed"
                            elif all_completed:
                                self.downloads[download_id]["status"] = "partial"
                            else:
                                self.downloads[download_id]["status"] = "failed"

                if not any_failed:
                    self.log("DOWNLOAD COMPLETED SUCCESSFULLY!", "success")
                else:
                    self.log("DOWNLOAD FAILED OR PARTIAL", "error")

                self.root.after(0, self._close_network_dialog)
                self._cleanup_download(download_id)
                self.update_button_states()
                if hasattr(self, 'index_entry'):
                    self.root.after(100, self.index_entry.focus_set)

            except Exception as e:
                self.log(f"Download error: {str(e)}", "error")
                self.root.after(0, lambda: self.show_toast(f"Download failed: {str(e)[:50]}", "error", 4000))
                self._cleanup_download(download_id)
                self.update_button_states()
                if hasattr(self, 'index_entry'):
                    self.root.after(100, self.index_entry.focus_set)
            finally:
                with self.download_lock:
                    self._package_loop_running.discard(download_id)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        with self.download_lock:
            self.download_threads = [t for t in self.download_threads if t.is_alive()]
            self.download_threads.append(thread)

    def _start_auto_resume_watcher(self, download_id, url, filename, download_dir):
        def watcher():
            while True:
                for _ in range(12):
                    time.sleep(5)
                    if self.check_internet():
                        break
                else:
                    continue
                self.debug_log("NETWORK", "SUCCESS", "Internet restored - auto resuming download")
                self.root.after(0, self._auto_close_network_dialog)
                with self.download_lock:
                    if download_id in self.downloads:
                        self.downloads[download_id]["retry_count"] = 0
                        self.downloads[download_id]["status"] = "downloading"
                self.root.after(0, self.on_resume_download)
                return

        threading.Thread(target=watcher, daemon=True).start()

    # -----------------------------------------------------------------
    # IDM CALLBACK
    # -----------------------------------------------------------------
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
                        if old_status == "paused":
                            return
                        if status == "completed":
                            self.downloads[download_id]["status"] = "completed"
                            if old_status != "completed":
                                self.root.after(0, lambda: self.show_toast(f"Download completed: {filename}", "success", 4000))
                        elif status == "downloading" and old_status != "paused":
                            self.downloads[download_id]["status"] = "downloading"

                self.root.after(0, lambda: self._safe_update_progress(
                    download_id, percentage, downloaded, total, speed, eta, filename, status
                ))

                if percentage > 0 and int(percentage) % 25 == 0 and not hasattr(self, f"_logged_{int(percentage)}_{download_id}"):
                    self.debug_log("DOWNLOAD", "INFO", f"Progress: {percentage:.0f}% | Speed: {speed/1024/1024:.1f} MB/s",
                                   f"Downloaded: {downloaded}/{total} bytes | ETA: {eta:.0f}s")
                    setattr(self, f"_logged_{int(percentage)}_{download_id}", True)

                if hasattr(self, 'console') and percentage > 0:
                    bar_length = 25
                    filled = int(bar_length * percentage / 100)
                    bar = chr(9608) * filled + chr(9617) * (bar_length - filled)
                    speed_str = f"{speed/1024/1024:.1f} MB/s" if speed > 0 else "0 B/s"
                    eta_str = f"{int(eta//60)}:{int(eta%60):02d}" if eta > 0 else "--:--"
                    self._direct_console_update(f"[{bar}] {percentage:.1f}% | {speed_str} | ETA: {eta_str}", "progress")

                self.update_button_states()

            elif data.get("type") == "log":
                self.log(data.get("message", ""), data.get("level", "info"))

    def _safe_update_progress(self, download_id, percentage, downloaded, total, speed, eta, filename, status):
        with self.download_lock:
            if download_id in self.downloads:
                if self.downloads[download_id].get("status") == "paused":
                    return
        self.update_download_progress(percentage, downloaded, total, speed, eta, filename, status)

    def _direct_console_update(self, message, level="progress"):
        if hasattr(self, 'console') and self.console.is_valid():
            try:
                self.console.update_progress_line(message)
            except Exception:
                self.console.append(message, level)

    # -----------------------------------------------------------------
    # BUTTON STATES
    # -----------------------------------------------------------------
    def update_button_states(self):
        active_id = self._get_active_download_id()
        states = {"dl_pause_btn": tk.DISABLED, "dl_resume_btn": tk.DISABLED,
                  "dl_cancel_btn": tk.DISABLED}

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

    # -----------------------------------------------------------------
    # PAUSE / RESUME / CANCEL
    # -----------------------------------------------------------------
    def on_pause_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
                self.debug_log("DOWNLOAD", "WARNING", "Pause requested", f"Download ID: {active_id}")
                self.idm_downloaders[active_id].pause(url)
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "paused"
                self.log("Paused", "warning")
                self.update_button_states()

    def on_resume_download(self):
        active_id = self._get_active_download_id()
        if not active_id or active_id not in self.idm_downloaders:
            return
        info = self.downloads.get(active_id, {})
        if not info:
            return
        with self.download_lock:
            if info.get("status") != "paused":
                return
            if active_id in self.downloads:
                self.downloads[active_id]["status"] = "downloading"
        self.log("Resuming download...", "info")
        with self.download_lock:
            self.download_threads = [t for t in self.download_threads if t.is_alive()]
        self._run_package_loop(active_id)

    def _on_net_pause_download(self):
        self.on_pause_download()

    def on_cancel_download(self):
        active_id = self._get_active_download_id()
        if active_id and active_id in self.idm_downloaders:
            url = self.downloads[active_id].get("url")
            if url:
                self.debug_log("DOWNLOAD", "WARNING", "Cancel requested", f"Download ID: {active_id}")
                self.idm_downloaders[active_id].cancel(url)
                with self.download_lock:
                    if active_id in self.downloads:
                        self.downloads[active_id]["status"] = "cancelled"
                self.log("Cancelled", "warning")
                self._cleanup_download(active_id)
                self.reset_download_ui()
                self.update_button_states()

    def _get_active_download_id(self):
        with self.download_lock:
            for did, d_info in self.downloads.items():
                if d_info.get("status") in ["downloading", "paused"]:
                    return did
        return None

    def _cleanup_download(self, download_id):
        with self.download_lock:
            self.idm_downloaders.pop(download_id, None)
            self.downloads.pop(download_id, None)
            self.download_threads = [t for t in self.download_threads if t.is_alive()]

    # -----------------------------------------------------------------
    # CONSOLE
    # -----------------------------------------------------------------
    def on_copy_console(self):
        if hasattr(self, '_console_raw'):
            self.root.clipboard_clear()
            self.root.clipboard_append(self._console_raw.get(1.0, tk.END))
            self.log("Console content copied", "info")

    def on_clear_console(self):
        if hasattr(self, 'console'):
            self.console.clear()
        self.log("Console cleared", "info")
        with self.fetch_lock:
            self.fetch_in_progress = False
            self.gib_wrapper = None

    def on_clean_temp(self):
        self.log("Cleaning temporary files...", "info")
        pycache_count = self.cleaner.clear_pycache()
        pyc_count = self.cleaner.clear_pyc_files()
        self.cleaner.clear_gibmacos_temp()
        self.log(f"Cleanup complete ({pycache_count + pyc_count} items)", "success")
        messagebox.showinfo("Cleanup Complete", f"Removed {pycache_count + pyc_count} temporary items")

    def on_clean_logs(self):
        if messagebox.askyesno("Delete All Logs", "WARNING: This will delete ALL log files.\n\nContinue?"):
            self.log("Deleting ALL log files...", "warning")
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
            self.log(f"Deleted {count} log file(s)", "success")
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
        self._stop_network_monitor()
        self.log("Application shutting down...", "info")
        self.logger.stop()
        self.root.destroy()


if __name__ == "__main__":
    main()
