import requests

pid = "01003008"

url = "https://unionnc.devnetwedge.com/"

response = requests.get(url)

print("Status:", response.status_code)
print(response.text[:3000])