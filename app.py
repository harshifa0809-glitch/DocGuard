import tkinter as tk

from tkinter import (
    filedialog,
    messagebox
)

from datetime import (
    datetime,
    date
)

from pathlib import Path

import os
import sys
import subprocess

import customtkinter as ctk


# ============================================================
# IMPORTANT:
# UNIQUE MODULE NAMES
# ============================================================

import docguard_database as db
import docguard_security as security
import docguard_vault as vault
import cloud_manager
import docguard_background as background

try:
    from plyer import notification
except ImportError:
    notification = None


# ============================================================
# APPEARANCE
# ============================================================

ctk.set_appearance_mode("light")

ctk.set_default_color_theme("blue")


# ============================================================
# COLORS
# ============================================================

BG = "#F5F7FA"

WHITE = "#FFFFFF"

TEXT = "#172033"

SECONDARY = "#64748B"

BORDER = "#E2E8F0"

PRIMARY = "#00A6A6"
TEAL = PRIMARY

PRIMARY_DARK = "#008B8B"

GREEN = "#16A34A"

ORANGE = "#F59E0B"

RED = "#EF4444"

LIGHT_TEAL = "#E6FFFB"

LIGHT_RED = "#FEE2E2"


# ============================================================
# CATEGORIES
# ============================================================

CATEGORIES = {

    "Identity": ("#06B6D4", "🪪"),

    "Education": ("#8B5CF6", "🎓"),

    "Vehicle": ("#F97316", "🚗"),

    "Insurance": ("#22C55E", "🛡"),

    "Financial": ("#14B8A6", "💳"),

    "Medical": ("#EC4899", "⚕"),

    "Property": ("#6366F1", "🏠"),

    "Other": ("#EAB308", "📄")
}


# ============================================================
# DATE
# ============================================================

def parse_date(value):

    if not value:
        return None

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except Exception:

        return None


def expiry_status(expiry):

    if not expiry:
        return "No expiry date", SECONDARY

    expiry_date = parse_date(expiry)

    if not expiry_date:
        return "Invalid expiry date", RED

    days = (expiry_date - date.today()).days

    if days < 0:
        return f"🔴 EXPIRED • {abs(days)} days ago", RED

    if days == 0:
        return "🔴 EXPIRES TODAY", RED

    if days == 1:
        return "⚠ 1 DAY LEFT", RED

    if days <= 7:
        return f"⚠ {days} DAYS LEFT", RED

    if days <= 60:
        return f"⏰ {days} DAYS LEFT", ORANGE

    return f"✓ {days} DAYS LEFT", GREEN


# ============================================================
# APP
# ============================================================

class DocGuardApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(
            "DocGuard — Personal Document Vault"
        )

        self.geometry(
            "1400x850"
        )

        self.minsize(
            1100,
            700
        )

        self.configure(
            fg_color=BG
        )

        self.category = None

        self.auth_tab = "login"

        db.initialize()

        try:
            background.install_windows_task()
        except Exception as error:
            print("Background notification setup skipped:", error)

        self.show_auth("login")

        self.after(5000, self.check_expiry_notifications)
        self.after(60000, self.refresh_countdown)
        self.after(60000, self.check_session_timeout)

        self.last_activity = datetime.now()
        self.bind_all("<Any-KeyPress>", self.touch_session)
        self.bind_all("<Any-Button>", self.touch_session)
        self.session_timeout_seconds = 15 * 60


    def touch_session(self, event=None):
        self.last_activity = datetime.now()


    def check_session_timeout(self):
        try:
            if vault.is_initialized():
                elapsed = (datetime.now() - self.last_activity).total_seconds()
                if elapsed >= self.session_timeout_seconds:
                    self.lock_vault(auto=True)
                    self.after(60000, self.check_session_timeout)
                    return
        except Exception as error:
            print("Session timeout error:", error)
        self.after(60000, self.check_session_timeout)


    def check_expiry_notifications(self):
        try:
            documents = db.get_documents()
            today_string = date.today().isoformat()
            for document in documents:
                expiry = document["expiry_date"]
                if not expiry:
                    continue
                expiry_date = parse_date(expiry)
                if not expiry_date:
                    continue
                days_left = (expiry_date - date.today()).days
                if 0 <= days_left <= 7 and document["last_notification_date"] != today_string:
                    self.send_expiry_notification(document, days_left)
                    db.mark_notification_sent(document["id"], today_string)
        except Exception as error:
            print("Expiry notification error:", error)
        self.after(60 * 60 * 1000, self.check_expiry_notifications)


    def send_expiry_notification(self, document, days_left):
        name = document["name"]
        if days_left == 0:
            title = "DocGuard — Document Expires Today"
            message = f"{name} expires today. Please renew it immediately."
        elif days_left == 1:
            title = "DocGuard — Document Expires Tomorrow"
            message = f"{name} expires tomorrow. Please renew it."
        else:
            title = "DocGuard — Expiry Reminder"
            message = f"{name} expires in {days_left} days. Please renew it before expiry."
        if notification:
            try:
                notification.notify(title=title, message=message, app_name="DocGuard", timeout=10)
            except Exception as error:
                print("Windows notification error:", error)


    def refresh_countdown(self):
        try:
            if hasattr(self, "documents_frame") and self.winfo_exists():
                self.refresh_documents()
        except Exception as error:
            print("Countdown refresh error:", error)
        self.after(60000, self.refresh_countdown)


    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self):

        for widget in self.winfo_children():

            widget.destroy()


    # ========================================================
    # AUTH SCREEN
    # ========================================================

    def show_auth(
        self,
        tab="login"
    ):

        self.clear()

        self.auth_tab = tab

        self.geometry(
            "1150x720"
        )


        # ----------------------------------------------------
        # MAIN CARD
        # ----------------------------------------------------

        card = ctk.CTkFrame(
            self,
            fg_color=WHITE,
            corner_radius=28,
            border_width=1,
            border_color=BORDER
        )

        card.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=0.88,
            relheight=0.88
        )


        # ====================================================
        # LEFT
        # ====================================================

        left = ctk.CTkFrame(
            card,
            fg_color=PRIMARY,
            corner_radius=24
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=16,
            pady=16
        )


        ctk.CTkLabel(
            left,
            text="🛡",
            font=("Segoe UI Emoji", 65),
            text_color="#123333"
        ).pack(
            pady=(45, 0)
        )


        ctk.CTkLabel(
            left,
            text="DocGuard",
            font=("Segoe UI", 36, "bold"),
            text_color=WHITE
        ).pack()


        ctk.CTkLabel(
            left,
            text="PERSONAL DOCUMENT VAULT",
            font=("Segoe UI", 10, "bold"),
            text_color="#D8FFFF"
        ).pack(
            pady=(2, 28)
        )


        ctk.CTkLabel(
            left,
            text=(
                "Your documents.\n"
                "Your vault.\n"
                "Your control."
            ),
            font=("Segoe UI", 20),
            text_color=WHITE,
            justify="center"
        ).pack(
            pady=5
        )


        features = [

            "🔐  Encrypted Local Storage",

            "📁  Smart Document Categories",

            "⏰  Expiry Reminders",

            "🔎  Instant Document Search",

            "☁  Optional Cloud Backup"
        ]


        for item in features:

            ctk.CTkLabel(
                left,
                text=item,
                font=("Segoe UI", 11),
                text_color="#E8FFFF"
            ).pack(
                anchor="w",
                padx=45,
                pady=5
            )


        ctk.CTkLabel(
            left,
            text="OFFLINE-FIRST • PRIVATE • SECURE",
            font=("Segoe UI", 9, "bold"),
            text_color="#D8FFFF"
        ).pack(
            side="bottom",
            pady=22
        )


        # ====================================================
        # RIGHT
        # ====================================================

        right = ctk.CTkFrame(
            card,
            fg_color=WHITE
        )

        right.pack(
            side="right",
            fill="both",
            expand=True,
            padx=45,
            pady=32
        )


        ctk.CTkLabel(
            right,
            text="Welcome to DocGuard",
            font=("Segoe UI", 28, "bold"),
            text_color=TEXT
        ).pack(
            pady=(8, 3)
        )


        ctk.CTkLabel(
            right,
            text=(
                "Securely store and manage "
                "your important documents."
            ),
            font=("Segoe UI", 12),
            text_color=SECONDARY
        ).pack(
            pady=(0, 18)
        )


        # ====================================================
        # TABS
        # ====================================================

        tabs = ctk.CTkFrame(
            right,
            fg_color="#F1F5F9",
            corner_radius=12
        )

        tabs.pack(
            fill="x",
            pady=(0, 20)
        )


        ctk.CTkButton(
            tabs,
            text="🔐  LOGIN",
            height=42,
            corner_radius=9,
            fg_color=(
                PRIMARY
                if tab == "login"
                else "transparent"
            ),
            hover_color=PRIMARY_DARK,
            text_color=(
                WHITE
                if tab == "login"
                else TEXT
            ),
            font=("Segoe UI", 12, "bold"),
            command=lambda:
            self.show_auth("login")
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=4,
            pady=4
        )


        ctk.CTkButton(
            tabs,
            text="✨  CREATE ACCOUNT",
            height=42,
            corner_radius=9,
            fg_color=(
                PRIMARY
                if tab == "create"
                else "transparent"
            ),
            hover_color=PRIMARY_DARK,
            text_color=(
                WHITE
                if tab == "create"
                else TEXT
            ),
            font=("Segoe UI", 12, "bold"),
            command=lambda:
            self.show_auth("create")
        ).pack(
            side="right",
            fill="x",
            expand=True,
            padx=4,
            pady=4
        )


        if tab == "login":

            self.login_form(right)

        else:

            self.create_form(right)


    # ========================================================
    # LOGIN FORM
    # ========================================================

    def login_form(
        self,
        parent
    ):

        if not security.has_account():

            ctk.CTkLabel(
                parent,
                text=(
                    "No account exists yet. "
                    "Create your account first."
                ),
                font=("Segoe UI", 12),
                text_color=ORANGE
            ).pack(
                pady=(3, 16)
            )

        else:

            ctk.CTkLabel(
                parent,
                text="Login to access your secure vault.",
                font=("Segoe UI", 12),
                text_color=SECONDARY
            ).pack(
                pady=(0, 16)
            )


        # USERNAME

        ctk.CTkLabel(
            parent,
            text="Username",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(3, 4)
        )


        self.username_entry = ctk.CTkEntry(
            parent,
            height=46,
            corner_radius=11,
            placeholder_text="Enter your username"
        )

        self.username_entry.pack(
            fill="x",
            pady=(0, 12)
        )


        # PIN

        ctk.CTkLabel(
            parent,
            text="PIN / Password",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(3, 4)
        )


        row = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        row.pack(
            fill="x"
        )


        self.login_pin_entry = ctk.CTkEntry(
            row,
            height=46,
            corner_radius=11,
            placeholder_text="Enter your PIN",
            show="●"
        )

        self.login_pin_entry.pack(
            side="left",
            fill="x",
            expand=True
        )


        self.login_pin_visible = False


        ctk.CTkButton(
            row,
            text="👁",
            width=50,
            height=40,
            fg_color="transparent",
            hover_color="#F1F5F9",
            text_color=TEXT,
            command=self.toggle_login_pin
        ).pack(
            side="right",
            padx=(5, 0)
        )


        self.remember_var = tk.BooleanVar(
            value=False
        )


        ctk.CTkCheckBox(
            parent,
            text="Remember me on this device",
            variable=self.remember_var,
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(13, 12)
        )


        ctk.CTkButton(
            parent,
            text="🔐  LOGIN TO VAULT",
            height=50,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.login
        ).pack(
            fill="x"
        )


        ctk.CTkButton(
            parent,
            text="Don't have an account?  Create one →",
            height=32,
            fg_color="transparent",
            hover_color="#F1F5F9",
            text_color=PRIMARY_DARK,
            font=("Segoe UI", 11, "bold"),
            command=lambda:
            self.show_auth("create")
        ).pack(
            pady=(12, 4)
        )


        ctk.CTkLabel(
            parent,
            text="🔒 Your documents remain encrypted locally.",
            font=("Segoe UI", 10),
            text_color=SECONDARY
        ).pack()


        self.username_entry.focus()


    # ========================================================
    # CREATE ACCOUNT FORM
    # ========================================================

    def create_form(
        self,
        parent
    ):

        ctk.CTkLabel(
            parent,
            text="Create your secure DocGuard account.",
            font=("Segoe UI", 12),
            text_color=SECONDARY
        ).pack(
            pady=(0, 15)
        )


        # NAME

        ctk.CTkLabel(
            parent,
            text="Full Name",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(2, 4)
        )


        self.name_entry = ctk.CTkEntry(
            parent,
            height=43,
            corner_radius=11,
            placeholder_text="e.g. Danish Shaikh"
        )

        self.name_entry.pack(
            fill="x",
            pady=(0, 9)
        )


        # USERNAME

        ctk.CTkLabel(
            parent,
            text="Username",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(2, 4)
        )


        self.create_username_entry = ctk.CTkEntry(
            parent,
            height=43,
            corner_radius=11,
            placeholder_text="Choose a username"
        )

        self.create_username_entry.pack(
            fill="x",
            pady=(0, 9)
        )


        # PIN

        ctk.CTkLabel(
            parent,
            text="PIN / Password",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(2, 4)
        )


        pin_row = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        pin_row.pack(
            fill="x"
        )


        self.create_pin_entry = ctk.CTkEntry(
            pin_row,
            height=43,
            corner_radius=11,
            placeholder_text="Minimum 4 characters",
            show="●"
        )

        self.create_pin_entry.pack(
            side="left",
            fill="x",
            expand=True
        )


        self.create_pin_visible = False


        ctk.CTkButton(
            pin_row,
            text="👁",
            width=50,
            height=38,
            fg_color="transparent",
            hover_color="#F1F5F9",
            text_color=TEXT,
            command=self.toggle_create_pin
        ).pack(
            side="right",
            padx=(5, 0)
        )


        # CONFIRM

        ctk.CTkLabel(
            parent,
            text="Confirm PIN",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            pady=(9, 4)
        )


        self.confirm_pin_entry = ctk.CTkEntry(
            parent,
            height=43,
            corner_radius=11,
            placeholder_text="Re-enter your PIN",
            show="●"
        )

        self.confirm_pin_entry.pack(
            fill="x",
            pady=(0, 12)
        )


        ctk.CTkButton(
            parent,
            text="✨  CREATE SECURE ACCOUNT",
            height=49,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.create_account
        ).pack(
            fill="x"
        )


        ctk.CTkButton(
            parent,
            text="Already have an account?  Login →",
            height=32,
            fg_color="transparent",
            hover_color="#F1F5F9",
            text_color=PRIMARY_DARK,
            font=("Segoe UI", 11, "bold"),
            command=lambda:
            self.show_auth("login")
        ).pack(
            pady=(9, 3)
        )


        ctk.CTkLabel(
            parent,
            text="🔐 Your PIN is never stored directly.",
            font=("Segoe UI", 10),
            text_color=SECONDARY
        ).pack()


        self.name_entry.focus()


    # ========================================================
    # PIN VISIBILITY
    # ========================================================

    def toggle_login_pin(self):

        self.login_pin_visible = (
            not self.login_pin_visible
        )

        self.login_pin_entry.configure(
            show=(
                ""
                if self.login_pin_visible
                else
                "●"
            )
        )


    def toggle_create_pin(self):

        self.create_pin_visible = (
            not self.create_pin_visible
        )

        value = (
            ""
            if self.create_pin_visible
            else
            "●"
        )

        self.create_pin_entry.configure(
            show=value
        )

        self.confirm_pin_entry.configure(
            show=value
        )


    # ========================================================
    # LOGIN
    # ========================================================

    def login(self):

        username = (
            self.username_entry
            .get()
            .strip()
        )

        pin = (
            self.login_pin_entry
            .get()
            .strip()
        )


        if not security.has_account():

            answer = messagebox.askyesno(
                "No Account Found",
                (
                    "No DocGuard account exists.\n\n"
                    "Create an account now?"
                )
            )

            if answer:

                self.show_auth("create")

            return


        if not username:

            messagebox.showwarning(
                "Username Required",
                "Please enter your username."
            )

            return


        if not pin:

            messagebox.showwarning(
                "PIN Required",
                "Please enter your PIN."
            )

            return


        if not security.authenticate(
            username,
            pin
        ):

            messagebox.showerror(
                "Login Failed",
                "Incorrect username or PIN."
            )

            return


        try:

            vault.initialize_key(
                pin
            )
            db.set_current_user_id(security.get_current_user_id())
            db.claim_orphan_documents(security.get_current_user_id())

            self.last_activity = datetime.now()
            self.show_dashboard()

        except Exception as error:

            messagebox.showerror(
                "Login Error",
                str(error)
            )


    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    def create_account(self):

        name = (
            self.name_entry
            .get()
            .strip()
        )

        username = (
            self.create_username_entry
            .get()
            .strip()
        )

        pin = (
            self.create_pin_entry
            .get()
            .strip()
        )

        confirm = (
            self.confirm_pin_entry
            .get()
            .strip()
        )


        if not name:

            messagebox.showwarning(
                "Name Required",
                "Please enter your full name."
            )

            return


        if not username:

            messagebox.showwarning(
                "Username Required",
                "Please choose a username."
            )

            return


        if len(username) < 3:

            messagebox.showwarning(
                "Username Too Short",
                "Username must contain at least 3 characters."
            )

            return


        if len(pin) < 4:

            messagebox.showwarning(
                "Weak PIN",
                "PIN must contain at least 4 characters."
            )

            return


        if pin != confirm:

            messagebox.showerror(
                "PIN Mismatch",
                "PIN and Confirm PIN do not match."
            )

            return


        try:

            security.create_account(
                name,
                username,
                pin
            )


            vault.initialize_key(
                pin
            )
            db.set_current_user_id(security.get_current_user_id())
            db.claim_orphan_documents(security.get_current_user_id())
            self.last_activity = datetime.now()


            messagebox.showinfo(
                "Account Created",
                (
                    "Account created successfully!\n\n"
                    "Welcome to DocGuard."
                )
            )


            self.show_dashboard()


        except Exception as error:

            messagebox.showerror(
                "Account Creation Failed",
                str(error)
            )


    # ========================================================
    # SIDEBAR
    # ========================================================

    def create_sidebar(self):

        sidebar = ctk.CTkFrame(
            self,
            width=250,
            fg_color=WHITE,
            corner_radius=0,
            border_width=1,
            border_color=BORDER
        )

        sidebar.pack(
            side="left",
            fill="y"
        )


        profile = security.profile()

        name = profile.get(
            "full_name",
            profile.get("name", "User")
        )

        username = profile.get(
            "username",
            ""
        )


        ctk.CTkLabel(
            sidebar,
            text="🛡",
            font=("Segoe UI Emoji", 32),
            text_color=PRIMARY
        ).pack(
            pady=(23, 0)
        )


        ctk.CTkLabel(
            sidebar,
            text="DocGuard",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT
        ).pack()


        ctk.CTkLabel(
            sidebar,
            text=name,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT
        ).pack(
            pady=(4, 0)
        )


        ctk.CTkLabel(
            sidebar,
            text=f"@{username}",
            font=("Segoe UI", 10),
            text_color=SECONDARY
        ).pack(
            pady=(0, 18)
        )


        nav = [

            (
                "⌂   Overview",
                lambda:
                self.show_dashboard()
            ),

            (
                "＋   Add Document",
                self.add_document
            ),

            (
                "⏰   Expiry Center",
                self.show_expiry_center
            ),

            (
                "☁   Backup & Restore",
                self.show_backup_center
            )
        ]


        for text, command in nav:

            ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=42,
                corner_radius=9,
                fg_color="transparent",
                hover_color="#E6FFFB",
                text_color=TEXT,
                font=("Segoe UI", 12),
                command=command
            ).pack(
                fill="x",
                padx=14,
                pady=2
            )


        ctk.CTkLabel(
            sidebar,
            text="CATEGORIES",
            font=("Segoe UI", 10, "bold"),
            text_color=SECONDARY
        ).pack(
            anchor="w",
            padx=24,
            pady=(24, 7)
        )


        for category, (_, icon) in CATEGORIES.items():

            count = db.count_category(
                category
            )

            ctk.CTkButton(
                sidebar,
                text=(
                    f"{icon}   "
                    f"{category}   "
                    f"{count}"
                ),
                anchor="w",
                height=36,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#F1F5F9",
                text_color=TEXT,
                font=("Segoe UI", 11),
                command=lambda c=category:
                self.show_dashboard(c)
            ).pack(
                fill="x",
                padx=14,
                pady=1
            )


        ctk.CTkFrame(
            sidebar,
            fg_color="transparent"
        ).pack(
            fill="both",
            expand=True
        )


        ctk.CTkLabel(
            sidebar,
            text="● BACKGROUND ALERTS ENABLED",
            font=("Segoe UI", 9, "bold"),
            text_color=TEAL
        ).pack(
            pady=(5, 0)
        )


        ctk.CTkLabel(
            sidebar,
            text="● LOCAL ENCRYPTED VAULT",
            font=("Segoe UI", 9, "bold"),
            text_color=GREEN
        ).pack(
            pady=5
        )


        ctk.CTkButton(
            sidebar,
            text="🔒  Lock Vault",
            height=40,
            corner_radius=10,
            fg_color=LIGHT_RED,
            hover_color="#FECACA",
            text_color="#B91C1C",
            command=self.lock_vault
        ).pack(
            fill="x",
            padx=16,
            pady=16
        )


    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(
        self,
        category=None
    ):

        self.clear()

        self.category = category

        self.create_sidebar()


        main = ctk.CTkFrame(
            self,
            fg_color=BG
        )

        main.pack(
            side="right",
            fill="both",
            expand=True
        )


        name = security.get_name()


        title = (
            category
            if category
            else
            f"Good to see you, {name} 👋"
        )


        ctk.CTkLabel(
            main,
            text=title,
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=32,
            pady=(28, 2)
        )


        ctk.CTkLabel(
            main,
            text=(
                "Your documents are protected "
                "and organized in one place."
            ),
            font=("Segoe UI", 12),
            text_color=SECONDARY
        ).pack(
            anchor="w",
            padx=32
        )


        # SEARCH

        search = ctk.CTkFrame(
            main,
            fg_color=WHITE,
            corner_radius=13,
            border_width=1,
            border_color=BORDER
        )

        search.pack(
            fill="x",
            padx=32,
            pady=14
        )


        self.search_entry = ctk.CTkEntry(
            search,
            height=44,
            border_width=0,
            fg_color="transparent",
            placeholder_text="🔍  Search documents..."
        )

        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=8
        )


        self.search_entry.bind(
            "<KeyRelease>",
            lambda event:
            self.refresh_documents()
        )


        ctk.CTkButton(
            search,
            text="+ Add Document",
            width=150,
            height=38,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            command=self.add_document
        ).pack(
            side="right",
            padx=6
        )


        # STATS

        self.stats_frame = ctk.CTkFrame(
            main,
            fg_color="transparent"
        )

        self.stats_frame.pack(
            fill="x",
            padx=28,
            pady=3
        )


        # DOCUMENTS

        self.documents_frame = ctk.CTkScrollableFrame(
            main,
            fg_color="transparent"
        )

        self.documents_frame.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=5
        )


        self.refresh_documents()


    # ========================================================
    # REFRESH
    # ========================================================

    def refresh_documents(self):

        for widget in (
            self.documents_frame
            .winfo_children()
        ):

            widget.destroy()


        all_documents = db.get_documents()

        documents = list(
            all_documents
        )


        if self.category:

            documents = [

                d for d in documents

                if d["category"]
                ==
                self.category
            ]


        query = (
            self.search_entry
            .get()
            .strip()
            .lower()
        )


        if query:

            documents = [

                d for d in documents

                if (
                    query
                    in d["name"].lower()
                )

                or

                (
                    query
                    in d["filename"].lower()
                )

                or

                (
                    query
                    in d["category"].lower()
                )
            ]


        total = len(documents)

        active = 0

        expiring = 0

        expired = 0


        for d in all_documents:

            expiry = d["expiry_date"]


            if not expiry:

                active += 1

                continue


            expiry_date = parse_date(
                expiry
            )


            if not expiry_date:
                continue


            days = (
                expiry_date -
                date.today()
            ).days


            if days < 0:

                expired += 1

            else:

                active += 1

                if days <= 60:

                    expiring += 1


        # STATS

        for widget in (
            self.stats_frame
            .winfo_children()
        ):

            widget.destroy()


        stats = [

            ("TOTAL", total, PRIMARY, "📁"),

            ("ACTIVE", active, GREEN, "✓"),

            ("EXPIRING", expiring, ORANGE, "⏰"),

            ("EXPIRED", expired, RED, "!")
        ]


        for title, value, color, icon in stats:

            card = ctk.CTkFrame(
                self.stats_frame,
                fg_color=WHITE,
                corner_radius=14,
                border_width=1,
                border_color=BORDER
            )

            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=4
            )


            ctk.CTkLabel(
                card,
                text=icon,
                font=("Segoe UI Emoji", 19),
                text_color=color
            ).pack(
                anchor="w",
                padx=16,
                pady=(8, 0)
            )


            ctk.CTkLabel(
                card,
                text=str(value),
                font=("Segoe UI", 23, "bold"),
                text_color=TEXT
            ).pack(
                anchor="w",
                padx=16
            )


            ctk.CTkLabel(
                card,
                text=title,
                font=("Segoe UI", 10, "bold"),
                text_color=SECONDARY
            ).pack(
                anchor="w",
                padx=16,
                pady=(0, 9)
            )


        if not documents:

            empty = ctk.CTkFrame(
                self.documents_frame,
                fg_color=WHITE,
                corner_radius=18,
                border_width=1,
                border_color=BORDER
            )

            empty.pack(
                fill="x",
                padx=10,
                pady=25
            )


            ctk.CTkLabel(
                empty,
                text="📂",
                font=("Segoe UI Emoji", 48)
            ).pack(
                pady=(30, 4)
            )


            ctk.CTkLabel(
                empty,
                text="No documents found",
                font=("Segoe UI", 20, "bold"),
                text_color=TEXT
            ).pack()


            ctk.CTkButton(
                empty,
                text="+ Add your first document",
                fg_color=PRIMARY,
                hover_color=PRIMARY_DARK,
                command=self.add_document
            ).pack(
                pady=18
            )

            return


        for document in documents:

            self.document_card(
                document
            )


    # ========================================================
    # DOCUMENT CARD
    # ========================================================

    def document_card(
        self,
        document
    ):

        color, icon = CATEGORIES.get(
            document["category"],
            (PRIMARY, "📄")
        )


        status, status_color = expiry_status(
            document["expiry_date"]
        )


        card = ctk.CTkFrame(
            self.documents_frame,
            fg_color=WHITE,
            corner_radius=15,
            border_width=1,
            border_color=BORDER
        )

        card.pack(
            fill="x",
            padx=8,
            pady=6
        )


        ctk.CTkFrame(
            card,
            width=6,
            fg_color=color,
            corner_radius=3
        ).pack(
            side="left",
            fill="y",
            padx=(0, 8),
            pady=8
        )


        ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI Emoji", 27)
        ).pack(
            side="left",
            padx=12,
            pady=15
        )


        info = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        info.pack(
            side="left",
            fill="x",
            expand=True,
            pady=12
        )


        ctk.CTkLabel(
            info,
            text=document["name"],
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w"
        )


        ctk.CTkLabel(
            info,
            text=(
                f'{document["category"]} • '
                f'{document["filename"]}'
            ),
            font=("Segoe UI", 11),
            text_color=SECONDARY
        ).pack(
            anchor="w",
            pady=3
        )


        right = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        right.pack(
            side="right",
            padx=15
        )


        ctk.CTkLabel(
            right,
            text=status,
            font=("Segoe UI", 10, "bold"),
            text_color=status_color
        ).pack(
            pady=3
        )


        buttons = ctk.CTkFrame(
            right,
            fg_color="transparent"
        )

        buttons.pack()


        ctk.CTkButton(
            buttons,
            text="Open",
            width=65,
            height=30,
            fg_color=LIGHT_TEAL,
            hover_color="#CCFBF1",
            text_color=PRIMARY_DARK,
            command=lambda d=document:
            self.open_document(d)
        ).pack(
            side="left",
            padx=2
        )


        if document["cloud_file_id"]:

            ctk.CTkButton(
                buttons,
                text="☁",
                width=34,
                height=30,
                fg_color="#E0F2FE",
                hover_color="#BAE6FD",
                text_color="#0369A1",
                command=lambda d=document: self.backup_document(d)
            ).pack(
                side="left",
                padx=2
            )


        ctk.CTkButton(
            buttons,
            text="Delete",
            width=65,
            height=30,
            fg_color=LIGHT_RED,
            hover_color="#FECACA",
            text_color="#B91C1C",
            command=lambda d=document:
            self.delete_document(d)
        ).pack(
            side="left",
            padx=2
        )


    # ========================================================
    # ADD DOCUMENT
    # ========================================================

    def add_document(self):

        window = ctk.CTkToplevel(
            self
        )

        window.title(
            "Add Document — DocGuard"
        )

        window.geometry(
            "620x720"
        )

        window.configure(
            fg_color=BG
        )

        window.transient(self)

        window.grab_set()


        ctk.CTkLabel(
            window,
            text="Add Document",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT
        ).pack(
            pady=(20, 3)
        )


        ctk.CTkLabel(
            window,
            text=(
                "The selected file will be encrypted "
                "before entering the vault."
            ),
            font=("Segoe UI", 12),
            text_color=SECONDARY
        ).pack(
            pady=(0, 10)
        )


        form = ctk.CTkFrame(
            window,
            fg_color=WHITE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER
        )

        form.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=8
        )


        selected = {
            "path": None
        }


        # FILE

        ctk.CTkLabel(
            form,
            text="Document File",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 4)
        )


        file_row = ctk.CTkFrame(
            form,
            fg_color="#F8FAFC",
            corner_radius=10
        )

        file_row.pack(
            fill="x",
            padx=22
        )


        file_label = ctk.CTkLabel(
            file_row,
            text="No file selected",
            text_color=SECONDARY
        )

        file_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10
        )


        def browse():

            path = filedialog.askopenfilename()

            if path:

                selected["path"] = path

                file_label.configure(
                    text=Path(path).name,
                    text_color=TEXT
                )


        ctk.CTkButton(
            file_row,
            text="Browse",
            width=90,
            height=34,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            command=browse
        ).pack(
            side="right",
            padx=5,
            pady=5
        )


        # FIELD

        def make_field(
            label,
            placeholder
        ):

            ctk.CTkLabel(
                form,
                text=label,
                font=("Segoe UI", 11, "bold"),
                text_color=TEXT
            ).pack(
                anchor="w",
                padx=22,
                pady=(12, 3)
            )


            entry = ctk.CTkEntry(
                form,
                height=38,
                corner_radius=9,
                placeholder_text=placeholder
            )

            entry.pack(
                fill="x",
                padx=22
            )

            return entry


        name_entry = make_field(
            "Document Name",
            "e.g. Aadhaar Card"
        )


        # CATEGORY

        ctk.CTkLabel(
            form,
            text="Category",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(12, 3)
        )


        category_menu = ctk.CTkOptionMenu(
            form,
            values=list(
                CATEGORIES.keys()
            ),
            height=38,
            fg_color=PRIMARY,
            button_color=PRIMARY_DARK
        )

        category_menu.pack(
            fill="x",
            padx=22
        )


        issue_entry = make_field(
            "Issue Date",
            "YYYY-MM-DD"
        )


        expiry_entry = make_field(
            "Expiry Date",
            "YYYY-MM-DD (optional)"
        )


        # REMINDER

        ctk.CTkLabel(
            form,
            text="Reminder",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=22,
            pady=(12, 3)
        )


        reminder_menu = ctk.CTkOptionMenu(
            form,
            values=[
                "7 days",
                "15 days",
                "30 days",
                "60 days"
            ],
            height=38,
            fg_color=PRIMARY,
            button_color=PRIMARY_DARK
        )

        reminder_menu.set(
            "30 days"
        )

        reminder_menu.pack(
            fill="x",
            padx=22
        )


        # SAVE

        def save():

            if not selected["path"]:

                messagebox.showwarning(
                    "File Required",
                    "Please select a document."
                )

                return


            name = (
                name_entry
                .get()
                .strip()
            )


            if not name:

                name = Path(
                    selected["path"]
                ).stem


            issue = (
                issue_entry
                .get()
                .strip()
                or None
            )


            expiry = (
                expiry_entry
                .get()
                .strip()
                or None
            )


            if issue and not parse_date(issue):

                messagebox.showerror(
                    "Invalid Date",
                    "Issue date must be YYYY-MM-DD."
                )

                return


            if expiry and not parse_date(expiry):

                messagebox.showerror(
                    "Invalid Date",
                    "Expiry date must be YYYY-MM-DD."
                )

                return


            reminder_days = int(
                reminder_menu
                .get()
                .split()[0]
            )


            try:

                stored_path = vault.store_file(
                    selected["path"]
                )


                document_id = db.add_document(

                    name=name,

                    category=category_menu.get(),

                    filename=Path(
                        selected["path"]
                    ).name,

                    stored_path=stored_path,

                    issue_date=issue,

                    expiry_date=expiry,

                    reminder_days=reminder_days
                )


                if cloud_manager.is_available():

                    try:

                        cloud_id = (
                            cloud_manager.upload_file(
                                stored_path,
                                Path(
                                    selected["path"]
                                ).name
                            )
                        )

                        db.set_cloud_file_id(
                            document_id,
                            cloud_id
                        )

                    except Exception as error:

                        print(
                            "Cloud backup skipped:",
                            error
                        )


                window.destroy()

                self.refresh_documents()

                messagebox.showinfo(
                    "Document Saved",
                    (
                        "Document encrypted and "
                        "stored successfully."
                    )
                )


            except Exception as error:

                messagebox.showerror(
                    "Save Failed",
                    str(error)
                )


        ctk.CTkButton(
            window,
            text="🔐  Encrypt & Store Document",
            height=48,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            font=("Segoe UI", 14, "bold"),
            command=save
        ).pack(
            fill="x",
            padx=25,
            pady=15
        )


    # ========================================================
    # OPEN
    # ========================================================

    def open_document(
        self,
        document
    ):

        try:

            temp_file = vault.restore_to_temp(
                document["stored_path"],
                document["filename"]
            )


            if sys.platform.startswith("win"):

                os.startfile(
                    temp_file
                )

            elif sys.platform == "darwin":

                subprocess.run(
                    [
                        "open",
                        temp_file
                    ]
                )

            else:

                subprocess.run(
                    [
                        "xdg-open",
                        temp_file
                    ]
                )


        except Exception as error:

            messagebox.showerror(
                "Open Failed",
                str(error)
            )


    # ========================================================
    # DELETE
    # ========================================================

    def delete_document(
        self,
        document
    ):

        answer = messagebox.askyesno(
            "Delete Document",
            (
                f'Delete "{document["name"]}" permanently?'
            )
        )


        if not answer:
            return


        try:

            vault.delete_file(
                document["stored_path"]
            )

            db.delete_document(
                document["id"]
            )

            self.refresh_documents()


        except Exception as error:

            messagebox.showerror(
                "Delete Failed",
                str(error)
            )


    def backup_document(self, document):
        if not cloud_manager.is_available():
            messagebox.showwarning(
                "Cloud Backup Not Configured",
                "Add credentials.json and install Google Drive packages first."
            )
            return
        try:
            cloud_id = cloud_manager.upload_file(
                document["stored_path"],
                document["filename"]
            )
            if cloud_id:
                db.set_cloud_file_id(document["id"], cloud_id)
                messagebox.showinfo("Backup Complete", "Encrypted document backed up to Google Drive.")
            else:
                messagebox.showerror("Backup Failed", "Google Drive did not return a file ID.")
        except Exception as error:
            messagebox.showerror("Backup Failed", str(error))


    def restore_document(self, document):
        if not document["cloud_file_id"]:
            messagebox.showwarning("No Cloud Backup", "This document has no cloud backup.")
            return
        try:
            if vault.file_exists(document["stored_path"]):
                messagebox.showinfo("Already Restored", "The encrypted document already exists in the local vault.")
                return
            if not cloud_manager.is_available():
                messagebox.showwarning("Cloud Backup Not Configured", "Google Drive credentials are not available.")
                return
            if cloud_manager.download_file(document["cloud_file_id"], document["stored_path"]):
                messagebox.showinfo("Restore Complete", "Encrypted document restored to the local vault.")
                self.refresh_documents()
            else:
                messagebox.showerror("Restore Failed", "Could not download the encrypted backup.")
        except Exception as error:
            messagebox.showerror("Restore Failed", str(error))


    def show_backup_center(self):
        self.clear()
        self.category = None
        self.create_sidebar()

        main = ctk.CTkFrame(self, fg_color=BG)
        main.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            main, text="Backup & Restore",
            font=("Segoe UI", 28, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=35, pady=(30, 4))

        ctk.CTkLabel(
            main,
            text="Manage encrypted Google Drive backups without exposing plaintext files.",
            font=("Segoe UI", 13), text_color=SECONDARY
        ).pack(anchor="w", padx=35)

        scroll = ctk.CTkScrollableFrame(main, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=25, pady=20)

        documents = db.get_documents()
        if not documents:
            ctk.CTkLabel(scroll, text="No documents available.", font=("Segoe UI", 18, "bold"), text_color=SECONDARY).pack(pady=100)
            return

        for document in documents:
            card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=15, border_width=1, border_color=BORDER)
            card.pack(fill="x", padx=10, pady=6)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=18, pady=15)
            ctk.CTkLabel(info, text=document["name"], font=("Segoe UI", 15, "bold"), text_color=TEXT).pack(anchor="w")
            cloud_status = "☁ Backed up" if document["cloud_file_id"] else "Local only"
            ctk.CTkLabel(info, text=f'{document["category"]} • {cloud_status}', font=("Segoe UI", 11), text_color=SECONDARY).pack(anchor="w", pady=3)

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=15)
            ctk.CTkButton(actions, text="Backup", width=80, height=32, fg_color=PRIMARY, hover_color=PRIMARY_DARK, command=lambda d=document: self.backup_document(d)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Restore", width=80, height=32, fg_color="#E0F2FE", hover_color="#BAE6FD", text_color="#0369A1", command=lambda d=document: self.restore_document(d)).pack(side="left", padx=3)


    # ========================================================
    # EXPIRY CENTER
    # ========================================================

    def show_expiry_center(self):

        self.clear()

        self.category = None

        self.create_sidebar()


        main = ctk.CTkFrame(
            self,
            fg_color=BG
        )

        main.pack(
            side="right",
            fill="both",
            expand=True
        )


        ctk.CTkLabel(
            main,
            text="Expiry Center",
            font=("Segoe UI", 28, "bold"),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=35,
            pady=(30, 4)
        )


        ctk.CTkLabel(
            main,
            text=(
                "Documents expiring within "
                "the next 60 days."
            ),
            font=("Segoe UI", 13),
            text_color=SECONDARY
        ).pack(
            anchor="w",
            padx=35
        )


        scroll = ctk.CTkScrollableFrame(
            main,
            fg_color="transparent"
        )

        scroll.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=20
        )


        documents = []


        for document in db.get_documents():

            expiry = parse_date(
                document["expiry_date"]
            )


            if expiry:

                days = (
                    expiry -
                    date.today()
                ).days


                if days <= 60:

                    documents.append(
                        (
                            days,
                            document
                        )
                    )


        documents.sort(
            key=lambda x: x[0]
        )


        if not documents:

            ctk.CTkLabel(
                scroll,
                text=(
                    "✓\n\n"
                    "No documents require attention."
                ),
                font=("Segoe UI", 22, "bold"),
                text_color=GREEN
            ).pack(
                pady=100
            )

            return


        for days, document in documents:

            card = ctk.CTkFrame(
                scroll,
                fg_color=WHITE,
                corner_radius=15,
                border_width=1,
                border_color=BORDER
            )

            card.pack(
                fill="x",
                padx=10,
                pady=6
            )


            ctk.CTkLabel(
                card,
                text="⏰",
                font=("Segoe UI Emoji", 27)
            ).pack(
                side="left",
                padx=20,
                pady=18
            )


            info = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )

            info.pack(
                side="left",
                fill="x",
                expand=True,
                pady=15
            )


            ctk.CTkLabel(
                info,
                text=document["name"],
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT
            ).pack(
                anchor="w"
            )


            ctk.CTkLabel(
                info,
                text=(
                    f'{document["category"]} • '
                    f'Expiry: {document["expiry_date"]}'
                ),
                font=("Segoe UI", 11),
                text_color=SECONDARY
            ).pack(
                anchor="w",
                pady=3
            )


            if days < 0:

                label = "EXPIRED"

                color = RED

            elif days == 0:

                label = "EXPIRES TODAY"

                color = RED

            else:

                label = f"{days} DAYS LEFT"

                color = ORANGE


            ctk.CTkLabel(
                card,
                text=label,
                font=("Segoe UI", 11, "bold"),
                text_color=color
            ).pack(
                side="right",
                padx=25
            )


    # ========================================================
    # LOCK
    # ========================================================

    def lock_vault(self, auto=False):

        vault.clear_key()
        db.clear_current_user_id()
        security.logout()

        if auto:
            messagebox.showinfo(
                "Vault Locked",
                "DocGuard was locked automatically after 15 minutes of inactivity."
            )

        self.show_auth("login")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    db.initialize()

    app = DocGuardApp()

    app.mainloop()
