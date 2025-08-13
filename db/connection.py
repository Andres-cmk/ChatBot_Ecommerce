import sqlite3

class DatabaseStock:

    def __init__(self):
        self.path = 'C:\\Users\\ramir\\Desktop\\ChatBot\\db\\makers_tech_db.sqlite3' # url to database
        self.conn = None

    def get_connection(self):
        return sqlite3.connect(self.path)

    def get_by_query(self, query: str = ""):
        self.conn = self.get_connection()
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(e)
            return []
        finally:
            self.conn.close()
    
    def update_db(self, name_product: str):

        self.conn = self.get_connection()
        try:
            cur = self.conn.cursor()
            cur.execute("UPDATE productos SET stock = stock - 1 WHERE nombre = ? AND stock > 0;", (name_product,))
            return True
        
        except sqlite3.Error as e:
            print(e)
            return False
        finally:
            self.conn.commit()
            self.conn.close()
    


