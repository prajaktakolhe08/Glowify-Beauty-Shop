import mysql.connector

if __name__ == "__main__":
    con = mysql.connector.connect(host ="localhost",username="root",password="mypassword")
    print(con)
    cursor = con.cursor()
    sql = "Create database mydatabase"
    cursor.execute(sql)
    con.close()