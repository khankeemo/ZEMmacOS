# main.py
import os
import socket
import sys
import time
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from main_ui import ZEMmacOSUI
from gib_macos_wrapper import GibMacOSWrapper
from logger import get_logger
from idm_downloader import IDMDownloader
from cleaner import Cleaner
from settings import SettingsManager, AppSettingsService
from update import AppUpdater
from live_log import get_live_log

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from WSD_SDKToolkit_ZEMMACOS import LicenseEngine, LicenseStatus
from WSD_SDKToolkit_ZEMMACOS import WelcomeDialog, ActivationDialog, RenewalDialog, DeviceReplaceDialog


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
    root.withdraw()
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

        self.live_log = get_live_log()

        self.debug_log("APP", "SYSTEM", "Application starting...")
        self.debug_log("PERFORMANCE", "INFO", "ZEMmacOS v3.0", f"Python {sys.version}")
        self.log("=" * 60, "info")
        self.log("ZEMmacOS Application Started", "info")
        self.log(f"Log file: {self.logger.get_log_file_path()}", "info")
        self.log("=" * 60, "info")
        self.live_log.write("STARTUP", "INFO", "Application started")
        self.live_log.write("STARTUP", "INFO", "Configuration loaded")
        self.live_log.write("STARTUP", "INFO", "Theme loaded")

        # --- License Integration ---
        self.license_engine = None
        self.license_status = None
        self._license_initialized = False
        self._customer_name = ""
        self._customer_email = ""
        self._customer_mobile = ""
        self._ui_enabled = False
        self._splash = None
        self._lock_overlay = None

        self.root.after(100, self._license_startup)

    # -----------------------------------------------------------------
    # HELPER: log to both file logger and live log
    # -----------------------------------------------------------------
    def log_live(self, category, level, message, detail=None):
        self.live_log.write(category, level, message, detail)
        self.log(f"[{category}] {message}", level.lower() if level != "SUCCESS" else "success")

    # -----------------------------------------------------------------
    # STRICT STARTUP SEQUENCE
    # -----------------------------------------------------------------
    def _license_startup(self):
        self.live_log.write("STARTUP", "INFO", "Splash screen created")
        self._create_splash()
        self.root.after(50, self._init_license_thread)

    def _create_splash(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg="#1d1d1f")
        W, H = 420, 220
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        splash.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        splash.attributes("-topmost", True)
        tk.Label(splash, text="ZEMmacOS", font=("SF Pro Display", 28, "bold"),
                 fg="#ffffff", bg="#1d1d1f").pack(expand=True, pady=(40, 4))
        tk.Label(splash, text="macOS Download Manager", font=("SF Pro Text", 10),
                 fg="#86868b", bg="#1d1d1f").pack()
        self._splash_status = tk.Label(splash, text="Initializing license...",
                                       font=("SF Pro Text", 10),
                                       fg="#6e6e73", bg="#1d1d1f")
        self._splash_status.pack(pady=(24, 0))
        splash.update()
        self._splash = splash

    def _init_license_thread(self):
        config_path = Path(BASE_DIR) / 'WSD_SDKToolkit_ZEMMACOS' / 'config' / 'api-config.json'
        self.log_live("SDK", "INFO", "LicenseEngine initialization")
        self.log_live("UI", "INFO", "UI locked")

        def do():
            live = self.live_log
            try:
                live.write("SDK", "INFO", "Loading api-config.json")
                self.license_engine = LicenseEngine(config_path=config_path)

                live.write("SDK", "INFO", "Hardware detection")
                _ = self.license_engine.get_hardware_id()

                live.write("SDK", "INFO", "Cache check")
                live.write("SDK", "INFO", "Trial check")
                live.write("SDK", "INFO", "License validation")
                self.license_status = self.license_engine.initialize()
                self._license_initialized = True

                # Extract customer data from API response
                self._extract_customer_from_api()

                status = self.license_status
                if status:
                    live.write("SDK", "INFO", f"Final LicenseStatus: {status.status}")
                    if status.valid:
                        msg = status.message or f"Status: {status.status}"
                        live.write("SDK", "SUCCESS", msg)
                    else:
                        live.write("SDK", "WARNING", "No valid license or trial found")
                else:
                    live.write("SDK", "ERROR", "LicenseStatus is None")
            except Exception as e:
                live.write("SDK", "ERROR", f"License initialization failed: {e}")
                eng = None
                try:
                    eng = LicenseEngine(config_path=config_path)
                except Exception:
                    eng = None
                self.license_engine = eng
                self.license_status = LicenseStatus(
                    valid=False, status='error', message=str(e)
                )
            finally:
                self.root.after(0, self._on_license_init_done)
        threading.Thread(target=do, daemon=True).start()

    def _on_license_init_done(self):
        self.log_live("STARTUP", "INFO", "SDK initialization complete")
        if self._splash:
            try:
                self._splash.destroy()
            except Exception:
                pass
            self._splash = None
        self._finalize_startup()

    def _finalize_startup(self):
        self.log_live("STARTUP", "INFO", "Building UI")
        self.build_main_ui()
        self.settings_service.apply_saved_theme()
        self.root.deiconify()
        self.show_dashboard()
        self.log_live("STARTUP", "INFO", "UI built, dashboard shown")
        self._lock_ui()
        self._start_network_monitor()
        self.root.after(500, self._show_startup_toast)
        self.root.after(1000, self._auto_fetch)
        self.root.after(2000, self._check_internet_on_startup)
        self.settings_service.check_first_run_directory()
        self._countdown_running = True
        self.root.after(1000, self._update_validity_countdown)

        self.root.after(300, self._check_license_on_startup)

    def _check_license_on_startup(self):
        status = self.license_status
        if status and status.valid:
            self.log_live("UI", "INFO", "License valid — enabling UI immediately")
            self._unlock_ui()
        elif status and status.status == "trial":
            self.log_live("UI", "INFO", "Trial active — enabling UI")
            self._unlock_ui()
        elif status and status.status == "unlicensed":
            self.log_live("WELCOME", "INFO", "No license found — opening welcome dialog")
            self.root.after(200, self._run_welcome_flow)
        else:
            self.log_live("WELCOME", "INFO", f"No license/trial — opening welcome dialog (status={status.status if status else 'None'})")
            self.root.after(200, self._run_welcome_flow)

    # -----------------------------------------------------------------
    # UI LOCK / UNLOCK
    # -----------------------------------------------------------------
    def _lock_ui(self):
        self._ui_enabled = False
        self._disable_nav()
        self._show_lock_overlay()
        self.log_live("UI", "INFO", "UI locked — waiting for license")

    def _unlock_ui(self):
        self._ui_enabled = True
        self._hide_lock_overlay()
        self._enable_nav()
        self._update_all_license_ui()
        self.log_live("UI", "SUCCESS", "UI unlocked")

    def _disable_nav(self):
        for btn in self._nav_buttons.values():
            try:
                btn.config(state=tk.DISABLED)
            except Exception:
                pass

    def _enable_nav(self):
        for btn in self._nav_buttons.values():
            try:
                btn.config(state=tk.NORMAL)
            except Exception:
                pass

    def _show_lock_overlay(self):
        try:
            if self._lock_overlay and self._lock_overlay.winfo_exists():
                return
            overlay = tk.Frame(
                self.content_area, bg=self.colors.get("content_bg", "#f5f5f7")
            )
            overlay._role = "card"
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            tk.Label(
                overlay,
                text="License verification in progress...",
                font=("SF Pro Display", 18, "bold"),
                fg=self.colors.get("muted", "#86868b"),
                bg=self.colors.get("content_bg", "#f5f5f7"),
            ).place(relx=0.5, rely=0.45, anchor=tk.CENTER)
            self._lock_overlay = overlay
        except Exception:
            pass

    def _hide_lock_overlay(self):
        try:
            if self._lock_overlay and self._lock_overlay.winfo_exists():
                self._lock_overlay.destroy()
        except Exception:
            pass
        self._lock_overlay = None

    # -----------------------------------------------------------------
    # WELCOME FLOW — closes app if dialog cancelled
    # -----------------------------------------------------------------
    def _run_welcome_flow(self):
        self.log_live("WELCOME", "INFO", "Welcome dialog opened")
        d = WelcomeDialog(
            self.license_engine._client,
            product_name='ZEM MAC OS',
            cache=self.license_engine._cache
        )
        result = d.show()
        if result and result.get('onboarding_complete'):
            self.log_live("WELCOME", "SUCCESS", "Welcome dialog completed — trial created")
            self.refresh_license()
            self.root.after(500, self._unlock_ui)
        else:
            self.log_live("WELCOME", "WARNING", "Welcome dialog closed before verification")
            self.log_live("WELCOME", "INFO", "Application shutdown initiated")
            self._shutdown_app()

    # -----------------------------------------------------------------
    # ACTIVATION FLOW — closes app if dialog cancelled
    # -----------------------------------------------------------------
    def open_activation(self, license_key=None):
        if not self.license_engine:
            return
        self.log_live("ACTIVATION", "INFO", "Activation dialog opened")
        d = ActivationDialog(
            self.license_engine._client,
            product_name='ZEM MAC OS',
            cache=self.license_engine._cache
        )
        r = d.show()
        if r and r.get('activated'):
            self.log_live("ACTIVATION", "SUCCESS", "License activation successful")
            self.refresh_license()
            self.root.after(500, self._unlock_ui)
        elif r and r.get('cancelled'):
            self.log_live("ACTIVATION", "WARNING", "Activation cancelled — continuing trial")
        return r

    # -----------------------------------------------------------------
    # APPLICATION SHUTDOWN (for incomplete flows)
    # -----------------------------------------------------------------
    def _shutdown_app(self):
        self.log("License flow incomplete — shutting down", "error")
        if hasattr(self, 'live_log'):
            self.live_log.write("STARTUP", "WARNING", "Application shutdown due to incomplete license flow")
            self.live_log.stop()
        self.logger.stop()
        try:
            self.root.destroy()
        except Exception:
            import sys as _sys
            _sys.exit(1)

    # -----------------------------------------------------------------
    # RENEWAL FLOW
    # -----------------------------------------------------------------
    def open_renewal(self):
        if not self.license_engine:
            return
        self.log_live("RENEWAL", "INFO", "Renewal started")
        k = self.license_engine.get_license_key()
        if not k:
            self.log_live("RENEWAL", "WARNING", "No active license key found")
            self.show_toast("No active license key found.", "warning", 3000)
            return
        d = RenewalDialog(self.license_engine, k, parent=self.root)
        r = d.show()
        if r:
            self.log_live("RENEWAL", "SUCCESS", "Renewal completed")
            self.refresh_license()
        return r

    # -----------------------------------------------------------------
    # DEVICE REPLACEMENT FLOW
    # -----------------------------------------------------------------
    def open_device_replace(self):
        if not self.license_engine:
            return
        self.log_live("DEVICE", "INFO", "Device replacement requested")
        k = self.license_engine.get_license_key()
        if not k:
            self.log_live("DEVICE", "WARNING", "No active license key found")
            self.show_toast("No active license key found.", "warning", 3000)
            return
        d = DeviceReplaceDialog(self.license_engine, k, parent=self.root)
        r = d.show()
        if r:
            self.log_live("DEVICE", "SUCCESS", "Device replacement successful")
            self.refresh_license()
        return r

    # -----------------------------------------------------------------
    # LICENSE REFRESH
    # -----------------------------------------------------------------
    def refresh_license(self):
        if not self.license_engine:
            return
        self.log_live("ACTIVATION", "INFO", "License refresh started")
        def do():
            try:
                new_status = self.license_engine.initialize()
                # Only update if we got valid data
                if new_status is not None:
                    self.license_status = new_status
                    # Extract customer info from API response
                    self._extract_customer_from_api()
                    self.root.after(0, self._update_all_license_ui)
                    self.log_live("ACTIVATION", "SUCCESS", "License refresh completed")
                else:
                    self.log_live("ACTIVATION", "WARNING", "License refresh returned None - keeping previous data")
            except Exception as e:
                self.log_live("ACTIVATION", "ERROR", f"License refresh error: {e}")
        threading.Thread(target=do, daemon=True).start()

    def _extract_customer_info(self, status):
        """Extract customer info from license status and store locally."""
        if status and status.valid:
            self._customer_name = getattr(status, 'customer_name', '') or ''
            self._customer_email = getattr(status, 'customer_email', '') or ''
            # Prefer mobile over phone
            self._customer_mobile = getattr(status, 'customer_mobile', '') or getattr(status, 'customer_phone', '') or ''

    def _extract_customer_from_api(self):
        """Get customer data using public SDK API."""
        if not self.license_engine or not self.license_status:
            return

        try:
            hw_id = self.license_engine.get_hardware_id()

            # If we have a license key, use public validate() method
            if self.license_engine.has_license_key():
                result = self.license_engine.validate(
                    self.license_engine.get_license_key()
                )
                # validate() returns full API response dict
                data = result.get('data', result)
                if data.get('valid') or data.get('customer_name'):
                    self._customer_name = data.get('customer_name', '') or ''
                    self._customer_email = data.get('customer_email', '') or ''
                    self._customer_mobile = data.get('customer_mobile', '') or data.get('customer_phone', '') or ''
                    return

            # For trial: data already fetched during initialize()
            # Trial customer data is in the trial API response but not exposed in LicenseStatus
            # This is a known SDK limitation - backend fix already returns the data
            # If license is not valid but trial is active, we can't access trial customer data via public SDK
            # (requires SDK regeneration to expose trial customer fields in LicenseStatus)

        except Exception as e:
            self.log_live("SDK", "WARNING", f"Could not extract customer from API: {e}")

    def _update_all_license_ui(self):
        self._update_dashboard_license()
        self._update_header_license_badge()
        # Also update settings license panel if open
        if hasattr(self, '_settings_license_widgets') and self._settings_license_widgets:
            self._update_settings_license_panel()

    def _update_validity_countdown(self):
        """Update validity countdown every second."""
        if not getattr(self, '_countdown_running', False):
            return
        self._update_all_license_ui()
        self.root.after(1000, self._update_validity_countdown)

    def open_welcome(self):
        if not self.license_engine:
            return
        self.log_live("WELCOME", "INFO", "Welcome dialog opened (manual)")
        d = WelcomeDialog(
            self.license_engine._client,
            product_name='ZEM MAC OS',
            cache=self.license_engine._cache
        )
        result = d.show()
        if result and result.get('onboarding_complete'):
            self.log_live("WELCOME", "SUCCESS", "Trial created via manual welcome")
            self.refresh_license()
        else:
            self.log_live("WELCOME", "WARNING", "Manual welcome dialog cancelled")
            self.log_live("WELCOME", "INFO", "Application shutdown initiated")
            self._shutdown_app()

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
        if hasattr(self, 'live_log'):
            self.live_log.write("STARTUP", "INFO", "Application shutting down")
            self.live_log.stop()
        self.logger.stop()
        self.root.destroy()


if __name__ == "__main__":
    main()
