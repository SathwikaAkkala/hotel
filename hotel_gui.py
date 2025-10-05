import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
import sqlite3
import csv

# ------------------ Backend Import ------------------
from hotel import (
    create_booking,
    cancel_booking,
    list_bookings,
    export_bookings_csv,
    export_bookings_txt,
    export_bookings_pdf,
    init_db
)

init_db()

# ------------------ GUI App ------------------
class HotelBookingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏨 Hotel Booking System")
        self.root.geometry("850x600")
        self.root.resizable(False, False)

        # Heading
        title = tk.Label(root, text="Hotel Booking Management System", font=("Helvetica", 18, "bold"))
        title.pack(pady=10)

        # Notebook Tabs
        tabs = ttk.Notebook(root)
        self.tab_book = ttk.Frame(tabs)
        self.tab_list = ttk.Frame(tabs)
        self.tab_report = ttk.Frame(tabs)
        tabs.add(self.tab_book, text="Create Booking")
        tabs.add(self.tab_list, text="View / Cancel Bookings")
        tabs.add(self.tab_report, text="Export Reports")
        tabs.pack(expand=True, fill="both")

        # ------------------ Create Booking Tab ------------------
        self.build_booking_tab()
        self.build_list_tab()
        self.build_report_tab()

    # Booking Tab
    def build_booking_tab(self):
        f = self.tab_book

        tk.Label(f, text="Guest Name:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        tk.Label(f, text="Room Type:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        tk.Label(f, text="Check-in (YYYY-MM-DD):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        tk.Label(f, text="Check-out (YYYY-MM-DD):").grid(row=3, column=0, padx=10, pady=10, sticky="e")

        self.name_var = tk.StringVar()
        self.type_var = tk.StringVar()
        self.ci_var = tk.StringVar()
        self.co_var = tk.StringVar()

        tk.Entry(f, textvariable=self.name_var, width=30).grid(row=0, column=1)
        ttk.Combobox(f, textvariable=self.type_var, values=["Single", "Double", "Deluxe"], width=27).grid(row=1, column=1)
        tk.Entry(f, textvariable=self.ci_var, width=30).grid(row=2, column=1)
        tk.Entry(f, textvariable=self.co_var, width=30).grid(row=3, column=1)

        tk.Button(f, text="Create Booking", command=self.create_booking, bg="#4CAF50", fg="white", width=20).grid(row=4, column=0, columnspan=2, pady=20)

    def create_booking(self):
        guest = self.name_var.get()
        rtype = self.type_var.get()
        ci = self.ci_var.get()
        co = self.co_var.get()
        try:
            bid, room = create_booking(guest, rtype, ci, co)
            messagebox.showinfo("Success", f"Booking Created!\nID: {bid}\nRoom: {room['room_number']}")
            self.load_bookings()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------ List Bookings Tab ------------------
    def build_list_tab(self):
        f = self.tab_list

        self.tree = ttk.Treeview(f, columns=("id", "guest", "room", "checkin", "checkout", "status"), show="headings")
        self.tree.heading("id", text="Booking ID")
        self.tree.heading("guest", text="Guest Name")
        self.tree.heading("room", text="Room")
        self.tree.heading("checkin", text="Check-in")
        self.tree.heading("checkout", text="Check-out")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("guest", width=120)
        self.tree.column("room", width=100)
        self.tree.column("checkin", width=100)
        self.tree.column("checkout", width=100)
        self.tree.column("status", width=80)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Button(f, text="Refresh", command=self.load_bookings).pack(side="left", padx=20, pady=10)
        tk.Button(f, text="Cancel Booking", command=self.cancel_booking).pack(side="left", padx=20, pady=10)

        self.load_bookings()

    def load_bookings(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for b in list_bookings():
            self.tree.insert("", "end", values=(b["id"], b["guest_name"], f"{b['room_type']} {b['room_number']}",
                                                b["check_in"], b["check_out"], b["status"]))

    def cancel_booking(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a booking to cancel.")
            return
        bid = self.tree.item(selected[0])["values"][0]
        try:
            cancel_booking(int(bid))
            messagebox.showinfo("Success", f"Booking {bid} cancelled.")
            self.load_bookings()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------ Report Tab ------------------
    def build_report_tab(self):
        f = self.tab_report
        tk.Label(f, text="Export Format:").pack(pady=10)
        tk.Button(f, text="Export CSV", command=lambda: self.export_report("csv"), width=20).pack(pady=5)
        tk.Button(f, text="Export TXT", command=lambda: self.export_report("txt"), width=20).pack(pady=5)
        tk.Button(f, text="Export PDF", command=lambda: self.export_report("pdf"), width=20).pack(pady=5)

    def export_report(self, fmt):
        try:
            if fmt == "csv":
                path = export_bookings_csv()
            elif fmt == "txt":
                path = export_bookings_txt()
            elif fmt == "pdf":
                path = export_bookings_pdf()
            else:
                raise ValueError("Invalid format")
            messagebox.showinfo("Success", f"Report exported:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ------------------ Run App ------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = HotelBookingApp(root)
    root.mainloop()
