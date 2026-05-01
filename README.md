📚 University Library System

A full-stack Library Management System designed to manage books, users, transactions, and library resources efficiently. This project includes database design, backend APIs, and a simple web interface.

🚀 Features
📖 Manage books and multiple copies
👤 User registration and management
🔄 Book borrowing and returning
🔖 Book reservations
💰 Fine management system
🔒 Locker booking system
🖥️ PC usage tracking
📊 Advanced queries and reports
🗂️ Database Design

The system is built using a well-structured relational database:

ERD (Entity Relationship Diagram) for conceptual design
Relational Schema for implementation
Fully normalized tables with:
Primary Keys
Foreign Keys
Constraints (CHECK, UNIQUE, etc.)
Main Entities:
Users
Staff
Books
BookCopies
Authors
Transactions
Reservations
Fines
Lockers
PC Usage Logs
⚙️ Technologies Used
Database: SQL Server
Backend: Python (Flask) Flask
Frontend: HTML, CSS, JavaScript
Database اتصال: pyodbc
📁 Project Structure
/project
│── app.py            # Backend (Flask API)
│── DDL.sql           # Database schema (tables)
│── DML.sql           # Sample data
│── index.html        # Frontend UI
│── ERD.png           # ER Diagram
│── schema.png        # Relational schema
🔌 API Features

The backend provides REST APIs for:

Queries:
Books with authors
Checked-out books
Unpaid fines
Available copies
Top borrowers
Locker and PC usage reports
Operations:
Add users, books, copies
Checkout / return books
Reserve books & lockers
Pay fines
Track PC sessions
▶️ How to Run
Setup Database
Run DDL.sql to create tables
Run DML.sql to insert sample data
Run Backend
pip install flask flask-cors pyodbc
python app.py
Open Frontend
Open index.html in your browser
💡 Key Concepts Applied
Database normalization
ER modeling
One-to-Many & Many-to-Many relationships
Data integrity constraints
REST API design
📌 Notes
The system uses auto-generated IDs for some operations
Book availability is dynamically updated during transactions
Constraints ensure valid data (e.g., booking status, user types)
📬 Future Improvements
Authentication & login system
Role-based access (Admin / User)
Better UI/UX
Deployment (cloud hosting)
👨‍💻 Author

Developed as a university database project.