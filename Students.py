from datetime import datetime, timedelta
import json
import os
import subprocess
import copy
import calendar

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

FILE = "Students.json"
META_FILE = "Meta.json"
HISTORY_FILE = "History.json"
TRASH_FILE = "RecycleBin.json"


# ================= NOTIFY =================
def notify(title, content):
    subprocess.run([
        "termux-notification",
        "--title", title,
        "--content", content
    ])


# ================= LOGIN =================
def login():
    try:
        r = subprocess.run(
            ["termux-fingerprint"],
            capture_output=True,
            text=True,
            timeout=15
        )
        return r.returncode == 0 and "AUTH_RESULT" in r.stdout
    except:
        return False


# ================= LOAD =================
def load_students():
    if os.path.exists(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


students = load_students()


def save_students():
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, indent=4, ensure_ascii=False)


# ================= ALERT =================
def check_student_dates():
    today = datetime.now().strftime("%d-%m-%Y")
    for s in students:
        if s.get("date") == today:
            notify("📌 Today Due", f"{s['name']}")


# ================= REMINDER =================
def check_upcoming_reminders():
    today = datetime.now()
    for s in students:
        try:
            due = datetime.strptime(s["date"], "%d-%m-%Y")
            if due - timedelta(days=2) <= today <= due and not s["paid"]:
                notify("⏰ Upcoming Fee", f"{s['name']} - {s['date']}")
        except:
            pass


# ================= TRASH =================
def load_trash():
    if os.path.exists(TRASH_FILE):
        try:
            with open(TRASH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


trash = load_trash()


def save_trash():
    with open(TRASH_FILE, "w", encoding="utf-8") as f:
        json.dump(trash, f, indent=4, ensure_ascii=False)


def move_to_trash(i):
    item = students.pop(i)
    item["deleted_at"] = str(datetime.now())
    trash.append(item)
    save_students()
    save_trash()
    notify("Deleted", "Moved to Recycle Bin")


def restore_from_trash():
    if not trash:
        print("❌ Empty Bin")
        return

    for i, s in enumerate(trash, 1):
        print(i, s["name"])

    try:
        idx = int(input("Restore No: ")) - 1
    except:
        return

    if 0 <= idx < len(trash):
        students.append(trash.pop(idx))
        save_students()
        save_trash()
        notify("Restored", "Recovered")


# ================= SMART DATE =================
def next_month_date(date_str):
    try:
        d = datetime.strptime(date_str, "%d-%m-%Y")
        year = d.year + (d.month // 12)
        month = d.month % 12 + 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(d.day, last_day)
        return datetime(year, month, day).strftime("%d-%m-%Y")
    except:
        return date_str


# ================= MONTH =================
def check_month():
    meta = {}

    if os.path.exists(META_FILE):
        with open(META_FILE, "r") as f:
            meta = json.load(f)

    current_month = datetime.now().strftime("%B-%Y")

    if "month" not in meta:
        meta["month"] = current_month

    if meta["month"] != current_month:

        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)

        history.append({
            "month": meta["month"],
            "data": copy.deepcopy(students),
            "saved_at": str(datetime.now())
        })

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)

        for s in students:
            s["paid"] = False
            s["date"] = next_month_date(s["date"])

        save_students()
        notify("New Month", "Reset + Date Updated")

        meta["month"] = current_month

    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=4)


# ================= SHOW =================
def show():
    check_month()
    check_student_dates()
    check_upcoming_reminders()

    table = Table(title="📚 Students", box=box.ROUNDED)

    table.add_column("No")
    table.add_column("Name")
    table.add_column("Date")
    table.add_column("Fee")
    table.add_column("Status")

    total_fee = 0
    paid_total = 0

    for i, s in enumerate(students, 1):
        status = "✔" if s["paid"] else "✘"

        total_fee += s["fee"]
        if s["paid"]:
            paid_total += s["fee"]

        table.add_row(
            str(i),
            s["name"],
            s["date"],
            f"₹{s['fee']}",
            status
        )

    console.print(table)

    pending = total_fee - paid_total

    print("\n📊 SUMMARY")
    print(f"👥 Total Students: {len(students)}")
    print(f"💰 Grand Total: ₹{total_fee}")
    print(f"✅ Paid: ₹{paid_total}")
    print(f"❌ Pending: ₹{pending}")


# ================= INPUT =================
def get_indexes():
    raw = input("Enter No(s): ")
    idx = []

    for x in raw.split(","):
        if x.strip().isdigit():
            i = int(x) - 1
            if 0 <= i < len(students):
                idx.append(i)

    return idx[:10]


# ================= PAID =================
def toggle_paid():
    show()
    idx = get_indexes()

    c = input("1 Paid / 2 Unpaid: ")

    for i in idx:
        students[i]["paid"] = True if c == "1" else False

    save_students()
    notify("Updated", "Status Changed")


# ================= REARRANGE =================
def rearrange():
    show()

    try:
        a = int(input("From: ")) - 1
        b = int(input("To: ")) - 1
    except:
        return

    if 0 <= a < len(students) and 0 <= b < len(students):
        item = students.pop(a)
        students.insert(b, item)
        save_students()
        notify("Done", "Rearranged")


# ================= EDIT =================
def edit():
    while True:

        print("\n--- EDIT SYSTEM ---")
        print("1 Add Student")
        print("2 Name Edit")
        print("3 Date Edit")
        print("4 Fee Edit")
        print("5 Delete")
        print("6 Restore")
        print("7 Rearrange")
        print("8 Back")

        c = input("Choose: ")

        if c == "8":
            break

        # ===== ADD STUDENT =====
        if c == "1":
            name = input("Name: ").strip()
            date = input("Date (DD-MM-YYYY): ").strip()

            try:
                fee = int(input("Fee: "))
            except:
                continue

            status_input = input("Status (True/t optional): ").strip().lower()

            paid = True if status_input in ["true", "t"] else False

            students.append({
                "name": name,
                "date": date,
                "fee": fee,
                "paid": paid
            })

            save_students()
            notify("Added", f"{name} Added")
            continue

        if c in ["2", "3", "4", "5"]:
            idx = get_indexes()

            for i in sorted(idx, reverse=True):

                if c == "2":
                    students[i]["name"] = input("New Name: ")

                elif c == "3":
                    students[i]["date"] = input("New Date: ")

                elif c == "4":
                    try:
                        students[i]["fee"] = int(input("New Fee: "))
                    except:
                        pass

                elif c == "5":
                    move_to_trash(i)

            save_students()

        elif c == "6":
            restore_from_trash()

        elif c == "7":
            rearrange()


# ================= MENU =================
def menu():
    while True:
        print("\n--- MENU ---")
        print("1 Show")
        print("2 Paid/Unpaid")
        print("3 Edit System")
        print("4 Exit")

        c = input("Choose: ")

        if c == "1":
            show()
        elif c == "2":
            toggle_paid()
        elif c == "3":
            edit()
        elif c == "4":
            break


# ================= START =================
if not login():
    print("Access Denied")
    exit()

menu()
