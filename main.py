import requests
from bs4 import BeautifulSoup
import csv

# URL de la page produit
product_page_url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

# Requête HTTP
response = requests.get(product_page_url)
soup = BeautifulSoup(response.text,'html.parser')

# Extraction des informations nécessaires
title = soup.find("h1").string

table = soup.find("table", class_="table table-striped")
universal_product_code = table.find_all("td")[0].string
price_including_tax = table.find_all("td")[3].string.strip("Â")
price_excluding_tax = table.find_all("td")[2].string.strip("Â")

number_available = soup.find("p", class_="instock availability").text.strip()

unordered_list = soup.find("ul", class_="breadcrumb")
category = unordered_list.find_all("li")[-2].text.strip()

# Sauvegarde des données dans un fichier CSV
filename = "book_data.csv"
headers = ["Page url", "UPC", "Title", "Price Including Tax", "Price Excluding Tax", "Availability", "Category"]

with open(filename, "w") as file:
    writer = csv.writer(file)
    writer.writerow(headers)
    writer.writerow([product_page_url, universal_product_code, title, price_including_tax, price_excluding_tax,
                     number_available, category])

print(f"Données extraites et sauvegardées dans {filename}")
