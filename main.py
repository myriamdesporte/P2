import requests
from bs4 import BeautifulSoup
import csv

def create_soup_object(url):
    """Crée un objet BeautifulSoup à partir d'une URL"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

def get_category_urls(limit = None):
    """Récupère les URLS de toutes les catégories sur la page d'accueil"""
    home_url = "http://books.toscrape.com/index.html"
    soup = create_soup_object(home_url)

    category_urls = []

    for url in soup.select("div.side_categories ul li a"):
        category_urls.append("http://books.toscrape.com/" + url["href"])

    return category_urls[1:limit] if limit else category_urls[1:]

    # À adapter en fonction des catégories souhaitées

def get_books_urls_from_category(category_url, books_urls = None):
    """Fonction récursive qui récupère les URLS de tous les livres d'une catégorie"""

    if books_urls is None:
        books_urls = []
    soup = create_soup_object(category_url)

    # Extraction du titre de la catégorie
    category_name = soup.find("h1").string

    # Extraction des URLs des livres de la page actuelle
    for url in soup.select("h3 a"):
        books_urls.append(url["href"].replace("../../..", "http://books.toscrape.com/catalogue"))

    # Si bouton next, on appelle la fonction récursivement
    next_page = soup.select_one("li.next a")

    if next_page:
        next_page_url = category_url.rsplit("/", 1)[0] + "/" + next_page["href"]
        return get_books_urls_from_category(next_page_url, books_urls)

    return category_name, books_urls

def scrape_book(book_url):
    """Extrait les données d'un livre à partir de l'URL produit"""
    soup = create_soup_object(book_url)

    # Extraction des informations nécessaires
    title = soup.find("h1").string

    table = soup.find("table", class_="table table-striped")
    universal_product_code = table.find_all("td")[0].string
    price_including_tax = table.find_all("td")[3].string.strip("Â")
    price_excluding_tax = table.find_all("td")[2].string.strip("Â")

    number_available = soup.find("p", class_="instock availability").text.strip()

    breadcrumb = soup.find("ul", class_="breadcrumb")
    category = breadcrumb.find_all("li")[-2].text.strip()

    return [book_url, universal_product_code, title, price_including_tax,
            price_excluding_tax, number_available, category]

def save_book_data_in_csv_file(filename, data):
    """Sauvegarde les données d'un livre dans un fichier csv"""
    headers = ["Page url", "UPC", "Title", "Price Including Tax", "Price Excluding Tax", "Availability", "Category"]

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)

    print(f"Données de {len(data)} livre(s) extraite(s) et sauvegardée(s) dans {filename}")

category_urls_list = get_category_urls(limit=3)

for category_url in category_urls_list:
    category_name, category_books_urls = get_books_urls_from_category(category_url)
    data = [scrape_book(url) for url in category_books_urls]
    save_book_data_in_csv_file(f"{category_name}.csv", data)