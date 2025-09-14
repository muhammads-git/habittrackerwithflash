from datetime import date
import MySQLdb


db = MySQLdb.connect(user='muhammad', passwd='Shahzib123!',db='habittracker')
cursor = db.cursor()


cursor.execute('SELECT id, user_id FROM habits')
habits = cursor.fetchall()

# 
for habit_id, user_id in habits:
    cursor.execute("""INSERT INTO habit_logs (user_id,habit_id,log_date,status) 
                   VALUES (%s,%s,CURDATE(),'pending')
                   ON DUPLICATE KEY UPDATE status=status
                    """, (user_id,habit_id))

db.commit()
cursor.close()
db.close()