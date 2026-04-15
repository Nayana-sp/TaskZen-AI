import requests

url_base = "http://127.0.0.1:8000/api"

print("1. Registering/Logging in...")
auth_data = {"username": "test@test.com", "password": "password"}
res = requests.post(f"{url_base}/auth/login", data=auth_data)
if res.status_code != 200:
    res = requests.post(f"{url_base}/auth/register", json={"name": "test", "email": "test@test.com", "password": "password"})
    res = requests.post(f"{url_base}/auth/login", data=auth_data)

token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("2. Sending voice prompt...")
res = requests.post(f"{url_base}/voice/process", headers=headers, json={"transcript": "I have a exam tomorrow."})
print("Result Output:", res.status_code)
print(res.text)
