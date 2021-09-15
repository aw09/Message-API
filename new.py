import requests

# db.create_all()
r = requests.post("http://34.101.133.218:2000/user", json={"username":"agung", "password":"1234"})
print(r.status_code, r.reason)
r = requests.post("http://34.101.133.218:2000/user", json={"username":"andi", "password":"1234"})
print(r.status_code, r.reason)
r = requests.post("http://34.101.133.218:2000/user", json={"username":"akbar", "password":"1234"})
print(r.status_code, r.reason)

