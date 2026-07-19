"""About Widget for ZEM MAC OS - Sidebar footer and Settings → About dialog"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Any, Dict, Optional


class AboutWidget:
    """Sidebar footer widget showing 'Powered by Websmith Digital™'"""

    def __init__(self, parent, engine):
        self.parent = parent
        self.engine = engine
        self.frame = tk.Frame(parent)
        self._build()

    def _build(self) -> tk.Frame:
        branding = self.engine.config.get('branding', {})
        colors = branding.get('colors', {})
        labels = branding.get('labels', {})

        bg = colors.get('bg_page', '#f8f9fa')
        text_muted = colors.get('text_muted', '#888888')
        text_secondary = colors.get('text_secondary', '#555555')
        border = colors.get('border', '#dbe3ef')

        self.frame.configure(bg=bg)
        self.frame.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 8))

        sep = tk.Frame(self.frame, bg=border, height=1)
        sep.pack(fill=tk.X, pady=(0, 6))

        footer_frame = tk.Frame(self.frame, bg=bg)
        footer_frame.pack(fill=tk.X)

        company = branding.get('company_name', 'Websmith Digital™')
        tk.Label(
            footer_frame,
            text=f"Powered by {company}",
            font=("Segoe UI", 8, "bold"),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.W)

        tk.Label(
            footer_frame,
            text=labels.get('about_subtitle', 'Enterprise License Platform'),
            font=("Segoe UI", 7),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.W)

        location = branding.get('location', 'Kolkata, India')
        tk.Label(
            footer_frame,
            text=location,
            font=("Segoe UI", 7),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.W, pady=(0, 2))

        return self.frame


class AboutDialog:
    """Settings → About dialog with dynamic product/runtime/license info"""

    def __init__(self, parent, engine):
        self.parent = parent
        self.engine = engine
        self.config = engine.config
        self.branding = self.config.get('branding', {})
        self.colors = self.branding.get('colors', {})
        self.labels = self.branding.get('labels', {})
        self._root: Optional[tk.Toplevel] = None

    def show(self):
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._root = tk.Toplevel(self.parent)
        self._root.title(self.labels.get('about_title', 'About'))
        self._root.geometry('420x520')
        self._root.resizable(False, False)
        self._root.configure(bg=self.colors.get('bg_page', '#f8f9fa'))
        self._root.transient(self.parent)
        self._root.grab_set()
        self._root.protocol('WM_DELETE_WINDOW', self._on_close)

        self._build_ui()
        self._center_window()
        self._root.wait_window()

    def _center_window(self):
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f'{w}x{h}+{x}+{y}')

    def _on_close(self):
        if self._root:
            self._root.destroy()
            self._root = None

    def _build_ui(self):
        root = self._root
        bg = self.colors.get('bg_page', '#f8f9fa')
        card_bg = self.colors.get('bg_card', '#ffffff')
        text_primary = self.colors.get('text_primary', '#333333')
        text_secondary = self.colors.get('text_secondary', '#555555')
        text_muted = self.colors.get('text_muted', '#888888')
        border = self.colors.get('border', '#dbe3ef')
        primary = self.colors.get('primary', '#1e40af')

        main_frame = tk.Frame(root, bg=bg, padx=24, pady=24)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with logo/brand
        header = tk.Frame(main_frame, bg=bg)
        header.pack(fill=tk.X, pady=(0, 20))

        company = self.branding.get('company_name', 'Websmith Digital™')
        tk.Label(
            header,
            text=company,
            font=("Segoe UI", 18, "bold"),
            bg=bg,
            fg=primary
        ).pack()

        tk.Label(
            header,
            text=self.labels.get('about_subtitle', 'Enterprise License & Activation Platform'),
            font=("Segoe UI", 10),
            bg=bg,
            fg=text_secondary
        ).pack(pady=(4, 0))

        # Product info card
        card = tk.Frame(main_frame, bg=card_bg, bd=1, relief=tk.SOLID,
                        highlightbackground=border, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 16))

        inner = tk.Frame(card, bg=card_bg, padx=20, pady=16)
        inner.pack(fill=tk.BOTH)

        tk.Label(
            inner,
            text=self.labels.get('about_product_info', 'Product Information'),
            font=("Segoe UI", 11, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W, pady=(0, 12))

        self._add_info_row(inner, self.labels.get('product_label', 'Product'),
                          self._get_product_name())
        self._add_info_row(inner, self.labels.get('version_label', 'Version'),
                          self._get_product_version())
        self._add_info_row(inner, self.labels.get('sdk_version_label', 'SDK Version'),
                          self._get_sdk_version())
        self._add_info_row(inner, self.labels.get('runtime_label', 'Runtime'),
                          self._get_runtime())
        self._add_info_row(inner, self.labels.get('status_label', 'License Status'),
                          self._get_license_status())
        self._add_info_row(inner, self.labels.get('plan_label', 'Current Plan'),
                          self._get_current_plan())
        self._add_info_row(inner, self.labels.get('build_date_label', 'Build Date'),
                          self._get_build_date())

        # Description card
        desc_card = tk.Frame(main_frame, bg=card_bg, bd=1, relief=tk.SOLID,
                              highlightbackground=border, highlightthickness=1)
        desc_card.pack(fill=tk.X, pady=(0, 16))

        desc_inner = tk.Frame(desc_card, bg=card_bg, padx=20, pady=16)
        desc_inner.pack(fill=tk.BOTH)

        desc_text = (
            f"This product is powered by {company},\n"
            f"Kolkata, India.\n\n"
            f"Licensing, activation, customer onboarding,\n"
            f"device security, and SDK services are\n"
            f"provided by {company}."
        )
        tk.Label(
            desc_inner,
            text=desc_text,
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_secondary,
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        # Architecture card
        arch_card = tk.Frame(main_frame, bg=card_bg, bd=1, relief=tk.SOLID,
                              highlightbackground=border, highlightthickness=1)
        arch_card.pack(fill=tk.X, pady=(0, 16))

        arch_inner = tk.Frame(arch_card, bg=card_bg, padx=20, pady=16)
        arch_inner.pack(fill=tk.BOTH)

        tk.Label(
            arch_inner,
            text=self.labels.get('about_architecture', 'Platform Architecture & Development'),
            font=("Segoe UI", 11, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W, pady=(0, 8))

        dev_name = self.branding.get('developer_name', 'Mohammad Kalam Khan')
        dev_title = self.branding.get('developer_title', 'Senior Developer')
        arch_text = f"{dev_name}\n{dev_title}"
        tk.Label(
            arch_inner,
            text=arch_text,
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_secondary,
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        # Copyright footer
        year = datetime.now().year
        copyright_text = f"© {year} {company}. All rights reserved."
        tk.Label(
            main_frame,
            text=copyright_text,
            font=("Segoe UI", 8),
            bg=bg,
            fg=text_muted
        ).pack(pady=(8, 0))

    def _add_info_row(self, parent, label: str, value: str):
        row = tk.Frame(parent, bg=parent.cget('bg'))
        row.pack(fill=tk.X, pady=2)
        text_primary = self.colors.get('text_primary', '#333333')
        text_secondary = self.colors.get('text_secondary', '#555555')
        tk.Label(
            row,
            text=f"{label}:",
            font=("Segoe UI", 9, "bold"),
            bg=row.cget('bg'),
            fg=text_primary,
            width=18,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        tk.Label(
            row,
            text=value,
            font=("Segoe UI", 9),
            bg=row.cget('bg'),
            fg=text_secondary,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _get_product_name(self) -> str:
        return self.config.get('product', {}).get('name', self.labels.get('unknown', 'Unknown'))

    def _get_product_version(self) -> str:
        return self.config.get('product', {}).get('version', self.labels.get('unknown', 'Unknown'))

    def _get_sdk_version(self) -> str:
        kit_version = self.config.get('kit_version')
        if kit_version:
            return kit_version
        manifest = self.config.get('manifest', {})
        return manifest.get('kit_version', self.labels.get('unknown', 'Unknown'))

    def _get_runtime(self) -> str:
        return self.config.get('runtime', 'Python')

    def _get_license_status(self) -> str:
        status = self.engine.get_status()
        if not status:
            status = self.engine.initialize()
        if status and status.valid:
            label = self.labels.get('trial_active_text', 'Trial Active') if status.trial_active else self.labels.get('licensed_text', 'Licensed')
            return f"{label} ({status.days_left} days remaining)"
        return self.labels.get('unlicensed_status', 'Unlicensed')

    def _get_current_plan(self) -> str:
        status = self.engine.get_status()
        if status and status.plan:
            return status.plan
        return self.labels.get('plan_na', 'N/A')

    def _get_build_date(self) -> str:
        manifest = self.config.get('manifest', {})
        generated = manifest.get('generated_at')
        if generated:
            try:
                dt = datetime.fromisoformat(generated.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
        return datetime.now().strftime('%Y-%m-%d')
