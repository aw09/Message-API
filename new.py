from app import db
import os, requests

# print(os.getcwd())
os.remove('./db.sqlite3')
db.create_all()
r = requests.post("http://localhost:2000/user", json={"username":"agung"})
print(r.status_code, r.reason)
r = requests.post("http://localhost:2000/user", json={"username":"andi"})
print(r.status_code, r.reason)
r = requests.post("http://localhost:2000/user", json={"username":"akbar"})
print(r.status_code, r.reason)


