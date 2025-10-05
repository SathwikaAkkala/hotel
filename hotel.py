import sqlite3
from pathlib import Path
from datetime import datetime
import csv

# ------------------ Database Setup ------------------
DB_PATH = Path(__file__).parent / "data" / "hotel.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_type TEXT NOT NULL,
    room_number TEXT NOT NULL UNIQUE,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    guest_name TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    cancelled_at TEXT,
    FOREIGN KEY(room_id) REFERENCES rooms(id)
);
'''

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM rooms')
        if cur.fetchone()[0] == 0:
            rooms = [
                ('Single', 'S101', 1500.0),
                ('Single', 'S102', 1500.0),
                ('Double', 'D201', 2500.0),
                ('Double', 'D202', 2500.0),
                ('Deluxe', 'L301', 4500.0)
            ]
            cur.executemany('INSERT INTO rooms (room_type, room_number, price) VALUES (?,?,?)', rooms)
init_db()

# ------------------ Models / Booking Logic ------------------
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def available_rooms(room_type, check_in, check_out):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            '''SELECT * FROM rooms WHERE room_type = ? AND id NOT IN (
                SELECT room_id FROM bookings
                WHERE status='active' AND NOT (check_out <= ? OR check_in >= ?)
            )''',
            (room_type, check_in, check_out)
        )
        return [dict(r) for r in cur.fetchall()]

def create_booking(guest_name, room_type, check_in, check_out):
    ci = parse_date(check_in)
    co = parse_date(check_out)
    if co <= ci:
        raise ValueError("check_out must be after check_in")
    avail = available_rooms(room_type, check_in, check_out)
    if not avail:
        raise ValueError(f"No available rooms of type {room_type} for given dates")
    room = avail[0]
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO bookings (room_id, guest_name, check_in, check_out, status, created_at)
               VALUES (?,?,?,?, 'active', ?)''',
            (room['id'], guest_name, check_in, check_out, now)
        )
        booking_id = cur.lastrowid
    return booking_id, room

def cancel_booking(booking_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT status FROM bookings WHERE id=?', (booking_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Booking not found")
        if row['status'] == 'cancelled':
            raise ValueError("Booking already cancelled")
        now = datetime.utcnow().isoformat()
        cur.execute('UPDATE bookings SET status=?, cancelled_at=? WHERE id=?', ('cancelled', now, booking_id))
    return True

def list_bookings(status=None):
    with get_conn() as conn:
        cur = conn.cursor()
        if status:
            cur.execute('''SELECT b.*, r.room_type, r.room_number, r.price
                           FROM bookings b JOIN rooms r ON r.id = b.room_id
                           WHERE b.status=?
                           ORDER BY b.created_at DESC''', (status,))
        else:
            cur.execute('''SELECT b.*, r.room_type, r.room_number, r.price
                           FROM bookings b JOIN rooms r ON r.id = b.room_id
                           ORDER BY b.created_at DESC''')
        return [dict(r) for r in cur.fetchall()]

# ------------------ Reports ------------------
def export_bookings_csv(path="bookings_report.csv", status=None):
    rows = list_bookings(status=status)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["booking_id","guest_name","room_type","room_number","price",
                         "check_in","check_out","status","created_at","cancelled_at"])
        for r in rows:
            writer.writerow([r["id"], r["guest_name"], r["room_type"], r["room_number"], r["price"],
                             r["check_in"], r["check_out"], r["status"], r["created_at"], r.get("cancelled_at") or ""])
    return str(path)

def export_bookings_txt(path="bookings_report.txt", status=None):
    rows = list_bookings(status=status)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("Bookings Report\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
        for r in rows:
            cancelled = r.get("cancelled_at") or ""
            f.write(f"ID: {r['id']} | Guest: {r['guest_name']} | Room: {r['room_type']}/{r['room_number']} | "
                    f"{r['check_in']} -> {r['check_out']} | Status: {r['status']} | Cancelled At: {cancelled}\n")
    return str(path)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    def export_bookings_pdf(path="bookings_report.pdf", status=None):
        rows = list_bookings(status=status)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(path), pagesize=letter)
        width, height = letter
        y = height - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Bookings Report")
        y -= 24
        c.setFont("Helvetica", 10)
        for r in rows:
            cancelled = r.get("cancelled_at") or ""
            line = f"{r['id']}: {r['guest_name']} | {r['room_type']}/{r['room_number']} | {r['check_in']} -> {r['check_out']} | Status: {r['status']} | Cancelled At: {cancelled}"
            c.drawString(40, y, line)
            y -= 14
            if y < 40:
                c.showPage()
                y = height - 40
        c.save()
        return str(path)
except ImportError:
    def export_bookings_pdf(*args, **kwargs):
        raise RuntimeError("reportlab not installed. Install it to enable PDF export.")

# ------------------ Console Menu ------------------
def main_menu():
    while True:
        print("\n=== Hotel Booking System ===")
        print("1. Create Booking")
        print("2. Cancel Booking")
        print("3. List All Bookings")
        print("4. Export Report (CSV/TXT/PDF)")
        print("5. Exit")
        choice = input("Enter choice: ").strip()

        if choice == "1":
            guest = input("Guest name: ")
            room_type = input("Room type (Single/Double/Deluxe): ")
            check_in = input("Check-in date (YYYY-MM-DD): ")
            check_out = input("Check-out date (YYYY-MM-DD): ")
            try:
                booking_id, room = create_booking(guest, room_type, check_in, check_out)
                print(f"✅ Booking created! ID={booking_id}, Room={room['room_number']}")
            except Exception as e:
                print("❌ Error:", e)

        elif choice == "2":
            bid = input("Enter booking ID to cancel: ")
            try:
                cancel_booking(int(bid))
                print("✅ Booking cancelled.")
            except Exception as e:
                print("❌ Error:", e)

        elif choice == "3":
            bookings = list_bookings()
            for b in bookings:
                print(f"ID={b['id']} | Guest={b['guest_name']} | Room={b['room_type']}/{b['room_number']} | "
                    f"{b['check_in']} -> {b['check_out']} | Status={b['status']}")

        elif choice == "4":
            print("1. CSV\n2. TXT\n3. PDF")
            opt = input("Choose format: ").strip()
            if opt == "1":
                print("Report saved:", export_bookings_csv())
            elif opt == "2":
                print("Report saved:", export_bookings_txt())
            elif opt == "3":
                try:
                    print("Report saved:", export_bookings_pdf())
                except Exception as e:
                    print("❌ Error:", e)

        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main_menu()

