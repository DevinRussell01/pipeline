import requests
from bs4 import BeautifulSoup

pid = "00101101"
url = f"https://polaris3g.mecklenburgcountync.gov/pid/{pid}"

response = requests.get(url)
print("Status:", response.status_code)
print(response.text[:1000])