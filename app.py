

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pyodbc
from datetime import datetime
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None  

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "DRIVER":   "{ODBC Driver 17 for SQL Server}",
    "SERVER":   "Abd_laptop\\SQLEXPRESS",   
    "DATABASE": "LibrarySystem",
    "Trusted_Connection": "yes"
}

def get_conn():
    conn_str = (
        f"DRIVER={DB_CONFIG['DRIVER']};"
        f"SERVER={DB_CONFIG['SERVER']};"
        f"DATABASE={DB_CONFIG['DATABASE']};"
        f"Trusted_Connection={DB_CONFIG['Trusted_Connection']};"
    )
    return pyodbc.connect(conn_str)

def rows_to_list(cursor):
    """Convert pyodbc rows into a list of dicts (JSON-friendly)."""
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def next_id(table, id_col):
    """Auto-generate next ID by getting MAX + 1 from the table."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT ISNULL(MAX({id_col}), 0) + 1 FROM {table}")
    new_id = cursor.fetchone()[0]
    conn.close()
    return new_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/query/books_with_authors")
def books_with_authors():
    sql = """
        SELECT b.bookID, b.title, b.publisher, b.publicationYear,
               c.categoryName,
               a.firstName + ' ' + a.lastName AS author
        FROM Book b
        JOIN Category c            ON b.categoryID  = c.categoryID
        JOIN Author_of_the_Book ab ON b.bookID       = ab.bookID
        JOIN Authors a             ON ab.authorID    = a.authorID
        ORDER BY b.title
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/checked_out")
def checked_out():
    sql = """
        SELECT t.transactionID,
               u.firstName + ' ' + u.lastName AS borrower,
               u.email,
               b.title,
               bc.copyID,
               bc.shelfLocation,
               CAST(t.checkoutDate AS VARCHAR) AS checkoutDate,
               CAST(t.dueDate      AS VARCHAR) AS dueDate,
               DATEDIFF(DAY, t.dueDate, GETDATE()) AS daysOverdue
        FROM Transactions t
        JOIN Users      u  ON t.userID  = u.userID
        JOIN BookCopies bc ON t.copyID  = bc.copyID
        JOIN Book       b  ON bc.bookID = b.bookID
        WHERE t.returnDate IS NULL
        ORDER BY t.dueDate
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/unpaid_fines")
def unpaid_fines():
    sql = """
        SELECT f.fineID,
               u.firstName + ' ' + u.lastName AS userName,
               u.email, f.amount, f.reason, f.paymentStatus,
               CAST(t.checkoutDate AS VARCHAR) AS checkoutDate
        FROM Fines f
        JOIN Users        u ON f.userID        = u.userID
        JOIN Transactions t ON f.transactionID = t.transactionID
        WHERE f.paymentStatus = 'Pending'
        ORDER BY f.amount DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/available_copies")
def available_copies():
    sql = """
        SELECT b.title, COUNT(bc.copyID) AS availableCopies
        FROM Book b
        JOIN BookCopies bc ON b.bookID = bc.bookID
        WHERE bc.bookingStatus = 'Available'
        GROUP BY b.title
        ORDER BY availableCopies DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/top_borrowers")
def top_borrowers():
    sql = """
        SELECT u.firstName + ' ' + u.lastName AS userName,
               u.userType, COUNT(t.transactionID) AS totalBorrows
        FROM Users u
        LEFT JOIN Transactions t ON u.userID = t.userID
        GROUP BY u.userID, u.firstName, u.lastName, u.userType
        ORDER BY totalBorrows DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/locker_summary")
def locker_summary():
    sql = """
        SELECT bookingStatus, COUNT(*) AS total
        FROM Locker
        GROUP BY bookingStatus
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/pc_usage")
def pc_usage():
    sql = """
        SELECT ul.logID,
               u.firstName + ' ' + u.lastName AS userName,
               ul.pcID,
               CAST(ul.startTime AS VARCHAR) AS startTime,
               CAST(ul.endTime   AS VARCHAR) AS endTime,
               DATEDIFF(MINUTE, ul.startTime, ul.endTime) AS minutesUsed
        FROM PC_usage_log ul
        JOIN Users u ON ul.userID = u.userID
        ORDER BY ul.startTime DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/search_books")
def search_books():
    term = request.args.get("q", "")
    sql = """
        SELECT b.bookID, bc.copyID, b.title, b.publisher,
               b.publicationYear, c.categoryName, bc.bookingStatus,
               bc.shelfLocation
        FROM Book b
        JOIN Category   c  ON b.categoryID = c.categoryID
        JOIN BookCopies bc ON b.bookID     = bc.bookID
        WHERE b.title LIKE ?
        ORDER BY b.title
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql, (f"%{term}%",))
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/all_categories")
def all_categories():
    sql = """
        SELECT c.categoryID, c.categoryName,
               COUNT(b.bookID) AS totalBooks
        FROM Category c
        LEFT JOIN Book b ON c.categoryID = b.categoryID
        GROUP BY c.categoryID, c.categoryName
        ORDER BY c.categoryName
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/all_books")
def all_books():
    sql = """
        SELECT b.bookID, b.title, b.publisher,
               b.publicationYear, c.categoryName,
               COUNT(bc.copyID) AS totalCopies
        FROM Book b
        JOIN Category c ON b.categoryID = c.categoryID
        LEFT JOIN BookCopies bc ON b.bookID = bc.bookID
        GROUP BY b.bookID, b.title, b.publisher,
                 b.publicationYear, c.categoryName
        ORDER BY b.title
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/books_by_category")
def books_by_category():
    category_id = request.args.get("id", "")
    sql = """
        SELECT b.bookID, b.title, b.publisher, b.publicationYear,
            c.categoryName,
            a.firstName + ' ' + a.lastName AS author
        FROM Book b
        JOIN Category c            ON b.categoryID = c.categoryID
        LEFT JOIN Author_of_the_Book ab ON b.bookID = ab.bookID
        LEFT JOIN Authors a         ON ab.authorID  = a.authorID
        WHERE c.categoryID = ?
        ORDER BY b.title
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql, (category_id,))
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/all_users")
def all_users():
    sql = """
        SELECT u.userID,
            u.firstName + ' ' + u.lastName AS fullName,
            u.email, u.userType,
            CAST(u.registrationDate AS VARCHAR) AS registrationDate,
            COUNT(t.transactionID) AS totalBorrows
        FROM Users u
        LEFT JOIN Transactions t ON u.userID = t.userID
        GROUP BY u.userID, u.firstName, u.lastName,
                u.email, u.userType, u.registrationDate
        ORDER BY u.firstName
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/active_locker_reservations")
def active_locker_reservations():
    sql = """
        SELECT lb.bookingID,
            lb.lockerNumber,
            u.firstName + ' ' + u.lastName AS userName,
            u.email,
            CAST(lb.startTime AS VARCHAR) AS startTime,
            CAST(lb.endTime   AS VARCHAR) AS endTime,
            CASE
                WHEN lb.startTime <= GETDATE() AND lb.endTime >= GETDATE()
                THEN 'Active Now'
                WHEN lb.endTime < GETDATE()
                THEN 'Expired'
                ELSE 'Upcoming'
            END AS status
        FROM LockerBooking lb
        JOIN Users u ON lb.userID = u.userID
        ORDER BY lb.startTime DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/query/available_lockers")
def available_lockers():
    sql = """
        SELECT l.bookingStatus, l.lockerNumber
        FROM Locker l
        WHERE l.bookingStatus = 'Available'
        AND l.lockerNumber NOT IN (
            SELECT lockerNumber
            FROM LockerBooking
            WHERE endTime >= GETDATE()
        )
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400



@app.route("/api/insert/user", methods=["POST"])
def insert_user():
    data = request.get_json()
    sql = """
        INSERT INTO Users
            (userID, firstName, lastName, email, userType, registrationDate)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        conn = get_conn()
        conn.execute(sql, (
            data["userID"], data["firstName"], data["lastName"],
            data["email"],  data["userType"],  data["registrationDate"]
        ))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "User added successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/book", methods=["POST"])
def insert_book():
    data = request.get_json()
    sql = """
        INSERT INTO Book
            (bookID, ISBN, title, publisher, publicationYear, description, categoryID)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn = get_conn()
        conn.execute(sql, (
            data["bookID"], data["ISBN"], data["title"],
            data["publisher"], data["publicationYear"],
            data["description"], data["categoryID"]
        ))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Book added successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/copy", methods=["POST"])
def insert_copy():
    data = request.get_json()
    sql = """
        INSERT INTO BookCopies
            (copyID, bookID, barcode, shelfLocation, bookingStatus, purchaseDate)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        conn = get_conn()
        conn.execute(sql, (
            data["copyID"], data["bookID"], data["barcode"],
            data["shelfLocation"], data["bookingStatus"], data["purchaseDate"]
        ))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Copy added successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/transaction", methods=["POST"])
def insert_transaction():
    data = request.get_json()
    sql = """
        INSERT INTO Transactions
            (transactionID, copyID, userID, checkoutDate, dueDate, renewalCount)
        VALUES (?, ?, ?, ?, ?, 0)
    """
    update_sql = "UPDATE BookCopies SET bookingStatus='CheckedOut' WHERE copyID=?"
    try:
        conn = get_conn()
        conn.execute(sql, (
            data["transactionID"], data["copyID"],
            data["userID"], data["checkoutDate"], data["dueDate"]
        ))
        conn.execute(update_sql, (data["copyID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Checkout recorded successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/fine", methods=["POST"])
def insert_fine():
    data = request.get_json()
    sql = """
        INSERT INTO Fines
            (fineID, userID, transactionID, amount, reason, paymentStatus)
        VALUES (?, ?, ?, ?, ?, 'Pending')
    """
    try:
        conn = get_conn()
        conn.execute(sql, (
            data["fineID"], data["userID"], data["transactionID"],
            data["amount"], data["reason"]
        ))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Fine issued successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/reservation", methods=["POST"])
def insert_reservation():
    data = request.get_json()
    new_id = next_id("Reservation", "reserveID")
    sql = """
        INSERT INTO Reservation (reserveID, userID, bookID, copyID)
        VALUES (?, ?, ?, ?)
    """
    update_sql = "UPDATE BookCopies SET bookingStatus='Reserved' WHERE copyID=?"
    try:
        conn = get_conn()
        conn.execute(sql, (new_id, data["userID"], data["bookID"], data["copyID"]))
        conn.execute(update_sql, (data["copyID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True,
                        "message": f"Book reserved successfully. Reserve ID: {new_id}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/locker_booking", methods=["POST"])
def insert_locker_booking():
    data = request.get_json()
    new_id = next_id("LockerBooking", "bookingID")
    sql = """
        INSERT INTO LockerBooking
            (bookingID, lockerNumber, userID, startTime, endTime)
        VALUES (?, ?, ?, ?, ?)
    """
    update_sql = "UPDATE Locker SET bookingStatus='Booked' WHERE lockerNumber=?"
    try:
        start = datetime.strptime(data["startTime"], "%Y-%m-%dT%H:%M")
        end   = datetime.strptime(data["endTime"],   "%Y-%m-%dT%H:%M")
        conn = get_conn()
        conn.execute(sql, (
            new_id, data["lockerNumber"],
            data["userID"], start, end
        ))
        conn.execute(update_sql, (data["lockerNumber"],))
        conn.commit(); conn.close()
        return jsonify({"success": True,
                        "message": f"Locker booked successfully. Booking ID: {new_id}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/pc_session", methods=["POST"])
def insert_pc_session():
    data = request.get_json()
    new_id = next_id("PC_usage_log", "logID")
    sql = """
        INSERT INTO PC_usage_log
            (logID, userID, pcID, startTime, endTime)
        VALUES (?, ?, ?, ?, ?)
    """
    try:
        start = datetime.strptime(data["startTime"], "%Y-%m-%dT%H:%M")
        end   = datetime.strptime(data["endTime"],   "%Y-%m-%dT%H:%M")
        conn = get_conn()
        conn.execute(sql, (
            new_id, data["userID"], data["pcID"],
            start, end
        ))
        conn.commit(); conn.close()
        return jsonify({"success": True,
                        "message": f"PC session recorded. Log ID: {new_id}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/update/return_book", methods=["POST"])
def return_book():
    data = request.get_json()
    sql_trans = """
        UPDATE Transactions SET returnDate = GETDATE()
        WHERE transactionID = ?
    """
    sql_copy = """
        UPDATE BookCopies SET bookingStatus = 'Available'
        WHERE copyID = (SELECT copyID FROM Transactions WHERE transactionID = ?)
    """
    try:
        conn = get_conn()
        conn.execute(sql_trans, (data["transactionID"],))
        conn.execute(sql_copy,  (data["transactionID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Book returned successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/update/pay_fine", methods=["POST"])
def pay_fine():
    data = request.get_json()
    sql = """
        UPDATE Fines SET paymentStatus='Paid', paymentDate=GETDATE()
        WHERE fineID = ?
    """
    try:
        conn = get_conn()
        conn.execute(sql, (data["fineID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Fine marked as paid."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/delete/reservation", methods=["POST"])
def delete_reservation():
    data = request.get_json()
    free_sql = """
        UPDATE BookCopies SET bookingStatus='Available'
        WHERE copyID = (SELECT copyID FROM Reservation WHERE reserveID=?)
    """
    del_sql = "DELETE FROM Reservation WHERE reserveID = ?"
    try:
        conn = get_conn()
        conn.execute(free_sql, (data["reserveID"],))
        conn.execute(del_sql,  (data["reserveID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Reservation cancelled."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/delete/user", methods=["POST"])
def delete_user():
    data = request.get_json()
    sql = "DELETE FROM Users WHERE userID = ?"
    try:
        conn = get_conn()
        conn.execute(sql, (data["userID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "User deleted."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/query/all_reservations")
def all_reservations():
    sql = """
        SELECT r.reserveID,
            u.firstName + ' ' + u.lastName AS userName,
            u.userID,
            b.title AS bookTitle,
            b.bookID,
            r.copyID,
            bc.bookingStatus
        FROM Reservation r
        JOIN Users      u  ON r.userID  = u.userID
        JOIN Book       b  ON r.bookID  = b.bookID
        JOIN BookCopies bc ON r.copyID  = bc.copyID
        ORDER BY r.reserveID
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/all_locker_bookings")
def all_locker_bookings():
    sql = """
        SELECT lb.bookingID,
            lb.lockerNumber,
            u.firstName + ' ' + u.lastName AS userName,
            u.userID,
            CAST(lb.startTime AS VARCHAR) AS startTime,
            CAST(lb.endTime   AS VARCHAR) AS endTime,
            CASE
                WHEN lb.endTime < GETDATE() THEN 'Expired'
                WHEN lb.startTime <= GETDATE() AND lb.endTime >= GETDATE() THEN 'Active Now'
                ELSE 'Upcoming'
            END AS status
        FROM LockerBooking lb
        JOIN Users u ON lb.userID = u.userID
        ORDER BY lb.startTime DESC
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/delete/locker_booking", methods=["POST"])
def delete_locker_booking():
    data = request.get_json()
    free_sql = """
        UPDATE Locker SET bookingStatus='Available'
        WHERE lockerNumber = (SELECT lockerNumber FROM LockerBooking WHERE bookingID=?)
    """
    del_sql = "DELETE FROM LockerBooking WHERE bookingID = ?"
    try:
        conn = get_conn()
        conn.execute(free_sql, (data["bookingID"],))
        conn.execute(del_sql,  (data["bookingID"],))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Locker booking cancelled successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/all_pcs")
def all_pcs():
    sql = """
        SELECT p.pcID,
            s.firstName + ' ' + s.lastName AS assignedStaff,
            s.staffID
        FROM PC p
        JOIN Staff s ON p.staffID = s.staffID
        ORDER BY p.pcID
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/query/available_pcs")
def available_pcs():
    sql = """
        SELECT p.pcID,
            s.firstName + ' ' + s.lastName AS assignedStaff,
            s.staffID
        FROM PC p
        JOIN Staff s ON p.staffID = s.staffID
        WHERE p.pcID NOT IN (
            SELECT pcID FROM PC_usage_log
            WHERE startTime <= GETDATE() AND endTime >= GETDATE()
        )
        ORDER BY p.pcID
    """
    try:
        conn = get_conn(); cursor = conn.cursor()
        cursor.execute(sql)
        result = rows_to_list(cursor)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/insert/pc", methods=["POST"])
def insert_pc():
    data = request.get_json()
    sql = "INSERT INTO PC (pcID, staffID) VALUES (?, ?)"
    try:
        conn = get_conn()
        conn.execute(sql, (data["pcID"], data["staffID"]))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "PC added successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
    
def release_expired_lockers():
    """Runs every minute — sets locker back to Available when booking expires."""
    sql = """
        UPDATE Locker SET bookingStatus = 'Available'
        WHERE lockerNumber IN (
            SELECT lockerNumber FROM LockerBooking
            WHERE endTime < GETDATE()
        )
    """
    try:
        conn = get_conn()
        conn.execute(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Scheduler error: {e}")


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(release_expired_lockers, 'interval', minutes=1)
    scheduler.start()
    app.run(debug=True, port=5000)