import sqlite3

db_name = "jobs"
connection = sqlite3.connect(db_name)

cursor = connection.cursor()

#cursor.execute("""
#    CREATE TABLE Jobs(
#        id INTEGER PRIMARY KEY,
#        title TEXT,
#        link TEXT,
#        source TEXT, 
#        country TEXT,
#        cities TEXT
#    );         
#""")

cursor.execute("Select * from jobs")
row = cursor.fetchall()
for row in row:
    print(row)

#connection.commit()
#print(f"Table made in database: {db_name}")

connection.close()
