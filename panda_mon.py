import pandas as pd
import sqlite3

c = sqlite3.connect("runinfo/monitoring.db")
df = pd.read_sql_query("SELECT * FROM task", c)
c.close()

print(df['task_time_returned'])
