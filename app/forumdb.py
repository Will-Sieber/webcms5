import sqlite3

class Forum:
    @staticmethod
    def get_messages(thread_id):
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM messages WHERE thread_id = ?", (thread_id,))
        rows = cur.fetchall()
        con.close()
        return rows

    @staticmethod
    def add_message(thread_id, author, content):
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("INSERT INTO messages (thread_id, author, content) VALUES (?, ?, ?)", (thread_id, author, content))
        con.commit()
        con.close()

    @staticmethod
    def create_table():
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS threads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT
                    )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id INTEGER,
                        author TEXT,
                        content TEXT,
                        FOREIGN KEY(thread_id) REFERENCES threads(id)
                    )""")
        con.close()

    @staticmethod
    def add_thread(name, author, message):
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("INSERT INTO threads (name) VALUES (?)", (name,))
        thread_id = cur.lastrowid
        cur.execute("INSERT INTO messages (thread_id, author, content) VALUES (?, ?, ?)", (thread_id, author, message))
        con.commit()
        con.close()

    @staticmethod
    def get_all_threads():
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM threads")
        rows = cur.fetchall()
        con.close()
        return rows
    
    @staticmethod
    def get_thread_title(thread_id):
        con = sqlite3.connect("forum.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM threads WHERE ID = ?", (thread_id,))
        row = cur.fetchone()
        con.close()
        return row
    
