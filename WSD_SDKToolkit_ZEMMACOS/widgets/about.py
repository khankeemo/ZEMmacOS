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

    def _build(self):
        branding = self.engine.config.get('branding', {})
        colors = branding.get('colors', {})
        labels = branding.get('labels', {})

        bg = colors.get('bg_page', '#f8f9fa')
        text_muted = colors.get('text_muted', '#888888')
        border = colors.get('border', '#dbe3ef')

        self.frame.configure(bg=bg)
        self.frame.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 6))

        sep = tk.Frame(self.frame, bg=border, height=1)
        sep.pack(fill=tk.X, pady=(0, 4))

        footer_frame = tk.Frame(self.frame, bg=bg)
        footer_frame.pack(fill=tk.X)

        company = branding.get('company_name', 'Websmith Digital™')
        tk.Label(
            footer_frame,
            text=f"Powered by {company}",
            font=("Segoe UI", 7, "bold"),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.CENTER)

        tk.Label(
            footer_frame,
            text=labels.get('about_subtitle', 'Universal License Platform'),
            font=("Segoe UI", 6),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.CENTER)

        location = branding.get('location', 'Kolkata, West Bengal, India')
        tk.Label(
            footer_frame,
            text=location,
            font=("Segoe UI", 6),
            bg=bg,
            fg=text_muted
        ).pack(anchor=tk.CENTER, pady=(0, 2))

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
        self._root.geometry('540x620')
        self._root.minsize(480, 560)
        self._root.resizable(True, True)
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

    def _make_card(self, parent):
        card_bg = self.colors.get('bg_card', '#ffffff')
        border_color = self.colors.get('border', '#dbe3ef')
        card = tk.Frame(
            parent,
            bg=card_bg,
            bd=1,
            relief=tk.SOLID,
            highlightbackground=border_color,
            highlightthickness=1
        )
        return card

    def _build_ui(self):
        root = self._root
        bg = self.colors.get('bg_page', '#f8f9fa')
        card_bg = self.colors.get('bg_card', '#ffffff')
        text_primary = self.colors.get('text_primary', '#333333')
        text_secondary = self.colors.get('text_secondary', '#555555')
        text_muted = self.colors.get('text_muted', '#888888')
        primary = self.colors.get('primary', '#1e40af')

        canvas = tk.Canvas(root, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=bg)
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width - 4)
        canvas.bind('<Configure>', _on_canvas_configure)

        content = tk.Frame(scroll_frame, bg=bg, padx=28, pady=28)
        content.pack(fill=tk.BOTH, expand=True)

        company = self.branding.get('company_name', 'Websmith Digital™')

        # ── HEADER CARD ──
        header_card = self._make_card(content)
        header_card.pack(fill=tk.X, pady=(0, 20))

        header_inner = tk.Frame(header_card, bg=card_bg, padx=24, pady=20)
        header_inner.pack(fill=tk.BOTH)

        tk.Label(
            header_inner,
            text=company,
            font=("Segoe UI", 20, "bold"),
            bg=card_bg,
            fg=primary
        ).pack(anchor=tk.CENTER)

        tk.Label(
            header_inner,
            text=self.labels.get('about_subtitle',
                                 'Universal License Platform'),
            font=("Segoe UI", 11),
            bg=card_bg,
            fg=text_secondary
        ).pack(anchor=tk.CENTER, pady=(4, 0))

        location = self.branding.get('location',
                                     'Kolkata, West Bengal, India')
        tk.Label(
            header_inner,
            text=location,
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_muted
        ).pack(anchor=tk.CENTER, pady=(4, 0))

        # ── PRODUCT INFORMATION CARD (Two-column) ──
        product_card = self._make_card(content)
        product_card.pack(fill=tk.X, pady=(0, 16))

        product_inner = tk.Frame(product_card, bg=card_bg, padx=24, pady=18)
        product_inner.pack(fill=tk.BOTH)

        tk.Label(
            product_inner,
            text=self.labels.get('about_product_info',
                                 'Product Information'),
            font=("Segoe UI", 12, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W, pady=(0, 14))

        info_data = [
            (self.labels.get('product_label', 'Product'),
             self._get_product_name(),
             self.labels.get('sdk_version_label', 'SDK Version'),
             self._get_sdk_version()),
            (self.labels.get('version_label', 'Version'),
             self._get_product_version(),
             self.labels.get('runtime_label', 'Runtime'),
             self._get_runtime()),
            (self.labels.get('status_label', 'License Status'),
             self._get_license_status(),
             self.labels.get('plan_label', 'Current Plan'),
             self._get_current_plan()),
            (self.labels.get('build_date_label', 'Build Date'),
             self._get_build_date(),
             '', ''),
        ]

        for row_idx, (lbl_l, val_l, lbl_r, val_r) in enumerate(info_data):
            row_frame = tk.Frame(product_inner, bg=card_bg)
            row_frame.pack(fill=tk.X, pady=(0, 6))
            row_frame.columnconfigure(0, weight=1, uniform='col')
            row_frame.columnconfigure(1, weight=1, uniform='col')

            # Left column
            left_frame = tk.Frame(row_frame, bg=card_bg)
            left_frame.grid(row=0, column=0, sticky='nw', padx=(0, 8))
            tk.Label(
                left_frame,
                text=lbl_l,
                font=("Segoe UI", 8, "bold"),
                bg=card_bg,
                fg=text_primary
            ).pack(anchor=tk.W, pady=(0, 1))
            val_widget_l = tk.Label(
                left_frame,
                text=val_l,
                font=("Segoe UI", 10),
                bg=card_bg,
                fg=text_secondary,
                anchor=tk.W,
                wraplength=200
            )
            val_widget_l.pack(anchor=tk.W)

            # Right column
            if lbl_r and val_r:
                right_frame = tk.Frame(row_frame, bg=card_bg)
                right_frame.grid(row=0, column=1, sticky='nw')
                tk.Label(
                    right_frame,
                    text=lbl_r,
                    font=("Segoe UI", 8, "bold"),
                    bg=card_bg,
                    fg=text_primary
                ).pack(anchor=tk.W, pady=(0, 1))
                val_widget_r = tk.Label(
                    right_frame,
                    text=val_r,
                    font=("Segoe UI", 10),
                    bg=card_bg,
                    fg=text_secondary,
                    anchor=tk.W,
                    wraplength=200
                )
                val_widget_r.pack(anchor=tk.W)

        # ── PLATFORM CARD ──
        platform_card = self._make_card(content)
        platform_card.pack(fill=tk.X, pady=(0, 16))

        platform_inner = tk.Frame(platform_card, bg=card_bg, padx=24, pady=18)
        platform_inner.pack(fill=tk.BOTH)

        tk.Label(
            platform_inner,
            text=company,
            font=("Segoe UI", 12, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W, pady=(0, 6))

        tk.Label(
            platform_inner,
            text="Enterprise License & Activation Platform",
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_secondary
        ).pack(anchor=tk.W, pady=(0, 10))

        platform_desc = (
            "Licensing, activation, onboarding,\n"
            "device security, hardware binding,\n"
            f"and SDK services are powered by\n"
            f"{company}."
        )
        tk.Label(
            platform_inner,
            text=platform_desc,
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_secondary,
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        # ── ARCHITECTURE CARD ──
        arch_card = self._make_card(content)
        arch_card.pack(fill=tk.X, pady=(0, 16))

        arch_inner = tk.Frame(arch_card, bg=card_bg, padx=24, pady=18)
        arch_inner.pack(fill=tk.BOTH)

        tk.Label(
            arch_inner,
            text=self.labels.get('about_architecture',
                                 'Platform Architecture & Development'),
            font=("Segoe UI", 12, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W, pady=(0, 10))

        dev_name = self.branding.get('developer_name',
                                     'Mohammad Kalam Khan')
        dev_title = self.branding.get('developer_title',
                                      'Senior Developer')

        tk.Label(
            arch_inner,
            text=dev_name,
            font=("Segoe UI", 10, "bold"),
            bg=card_bg,
            fg=text_primary
        ).pack(anchor=tk.W)

        tk.Label(
            arch_inner,
            text=dev_title,
            font=("Segoe UI", 9),
            bg=card_bg,
            fg=text_secondary
        ).pack(anchor=tk.W, pady=(0, 6))

        year = datetime.now().year
        tk.Label(
            arch_inner,
            text=f"\u00a9 {year} Websmith Digital",
            font=("Segoe UI", 8),
            bg=card_bg,
            fg=text_muted
        ).pack(anchor=tk.W)

    def _get_product_name(self) -> str:
        return self.config.get('product', {}).get('name', self.labels.get('unknown', 'Unknown'))

    def _get_product_version(self) -> str:
        return self.config.get('product', {}).get('version', self.labels.get('unknown', 'Unknown'))

    def _get_sdk_version(self) -> str:
        try:
            from .. import __version__
            if __version__:
                return __version__
        except ImportError:
            pass
        product = self.config.get('product', {})
        ver = product.get('version')
        if ver and ver != '${kit_version}':
            return ver
        manifest = self.config.get('manifest', {})
        mkv = manifest.get('kit_version')
        if mkv:
            return mkv
        return '1.0.0'

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
