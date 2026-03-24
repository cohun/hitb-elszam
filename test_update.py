import database
import pandas as pd
import numpy as np
import sqlite3

def run_test():
    conn = database.get_connection()
    cursor = conn.cursor()
    
    # Check if id 72 exists
    cursor.execute('SELECT id, Szla, Resz_fizetett FROM forgalom WHERE id = 72')
    row = cursor.fetchone()
    print(f"Row 72 before update: {row}")
    
    # Try updating with numpy int64
    real_id = np.int64(72)
    new_resz = 1
    cursor.execute('UPDATE forgalom SET Resz_fizetett = ? WHERE id = ?', (new_resz, real_id))
    print(f"Rowcount after numpy update: {cursor.rowcount}")
    conn.commit()
    
    # Check again
    cursor.execute('SELECT id, Szla, Resz_fizetett FROM forgalom WHERE id = 72')
    row = cursor.fetchone()
    print(f"Row 72 after numpy update: {row}")
    
    # Try updating with native int
    real_id_native = int(real_id)
    cursor.execute('UPDATE forgalom SET Resz_fizetett = ? WHERE id = ?', (0, real_id_native))
    print(f"Rowcount after native update: {cursor.rowcount}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_test()
