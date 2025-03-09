import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import os
from PIL import Image
from io import BytesIO


# --- EXTRACTION ---

def create_soup_object(url):
    """Crée un objet BeautifulSoup à partir d'une URL"""
    response = requests.get(url)

    # Forcer l'encodage en UTF-8
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def get_category_urls(limit=None):
    """Récupère les URLS de toutes les catégories (ou une partie)
    sur la page d'accueil"""
    home_url = "http://books.toscrape.com/index.html"
    soup = create_soup_object(home_url)

    category_urls = []

    for url in soup.select("div.side_categories ul li a"):
        category_urls.append("http://books.toscrape.com/" + url["href"])

    return category_urls[1:limit] if limit else category_urls[1:]


def get_books_urls_from_category(category_url, books_urls=None):
    """Fonction récursive récupérant les URLS des livres d'une catégorie"""

    if books_urls is None:
        books_urls = []
    soup = create_soup_object(category_url)

    # Extraction du titre de la catégorie
    category_name = soup.find("h1").string

    # Extraction des URLs des livres de la page actuelle
    for url in soup.select("h3 a"):
        books_urls.append(
            url["href"].replace(
                "../../..", "http://books.toscrape.com/catalogue"
            )
        )

    # Si bouton next, on appelle la fonction récursivement
    next_page = soup.select_one("li.next a")

    if next_page:
        next_page_url = (
                category_url.rsplit("/", 1)[0] + "/" + next_page["href"]
        )
        return get_books_urls_from_category(next_page_url, books_urls)

    return category_name, books_urls


def scrape_book_data(book_url):
    """Extrait les données d'un livre à partir de l'URL produit"""
    soup = create_soup_object(book_url)

    # Extraction des informations nécessaires
    product_page_url = book_url

    def get_table_value(label):
        value = ((soup.find('th', string=label)
                 .find_next('td'))
                 .text.strip())
        return value

    universal_product_code = get_table_value("UPC")

    title = soup.find("h1").text.strip()
    print(title)

    price_including_tax = get_table_value("Price (incl. tax)")

    price_excluding_tax = get_table_value("Price (excl. tax)")

    number_available = get_table_value("Availability")

    description = soup.find('div', id='product_description')
    if description:
        product_description = description.find_next('p').text
    else:
        product_description = "Aucune description disponible"

    category = (
        soup.find('ul', class_='breadcrumb')
        .find_all('li')[2]
        .text.strip()
    )

    rating_tag = soup.find('p', class_='star-rating')
    rating_level = rating_tag['class'][1] if rating_tag else None
    review_rating = transform_rating_to_stars(rating_level)

    image_relative_url = (
        soup.find("div", class_="item active")
        .find("img")["src"]
    )
    image_url = urljoin("http://books.toscrape.com/", image_relative_url)

    return {
        "product_page_url": product_page_url,
        "universal_product_code (upc)": universal_product_code,
        "title": title,
        "price_including_tax": price_including_tax,
        "price_excluding_tax": price_excluding_tax,
        "number_available": number_available,
        "product_description": product_description,
        "category": category,
        "review_rating": review_rating,
        "image_url": image_url
    }


# --- TRANSFORMATION ---

def clean_text(text):
    """Supprime le caractère problématique dans un nom de fichier"""
    text = text.replace('/', '-')
    return text


def transform_rating_to_stars(rating_level):
    """Convertit une notation en texte ('One', 'Two', etc.) en étoiles."""
    star_map = {
        "One": "★☆☆☆☆",
        "Two": "★★☆☆☆",
        "Three": "★★★☆☆",
        "Four": "★★★★☆",
        "Five": "★★★★★"
    }
    return star_map.get(rating_level, 'No rating')


def download_and_process_image(
        image_url, save_path, max_size=(300, 300), quality=85
):
    """Télécharge, redimensionne et compresse l'image d'un livre"""
    response = requests.get(image_url)

    # Ouvrir l'image avec Pillow
    image = Image.open(BytesIO(response.content))

    # Redimensionner l'image
    image.thumbnail(max_size)

    # Sauvegarde l'image avec compression
    image.save(save_path, "JPEG", quality=quality)


# --- SAUVEGARDE ---

def create_folder(path):
    """Crée un dossier s'il n'existe pas déjà."""
    os.makedirs(path, exist_ok=True)
    return path


def save_book_data_in_csv_file(data):
    """Enregistre les données d'un livre dans un fichier csv.

    - Vérifie si le fichier existe et s'il contient déjà le livre.
    - Ajoute les en-têtes si le fichier est créé pour la première fois.
    """

    csv_files_folder = create_folder("Books data/CSV files")
    filename = os.path.join(csv_files_folder, f"{data["category"]}.csv")
    file_exists = os.path.isfile(filename)
    new_row = list(data.values())

    # Vérifie si le livre est déjà enregistré
    if file_exists:
        with open(filename, "r", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            for row in reader:
                if row == new_row:
                    return  # Évite l'ajout d'un doublon

    # Ouvre le fichier en. mode ajout et écrit les données
    with open(filename, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        # Ajoute les en-têtes si le fichier est créé pour la première fois
        if not file_exists:
            writer.writerow(list(data.keys()))

        # Écrit les données du livre dans le fichier
        writer.writerow(list(new_row))


def save_image(data, category_folder):
    """Télécharge et sauvegarde l'image d'un livre"""
    image_filename = f"{clean_text(data["title"])}.jpg"
    image_path = os.path.join(category_folder, image_filename)
    download_and_process_image(data["image_url"], image_path)


# --- MAIN ---

def main():
    # Création du dossier "Images"
    images_folder = create_folder("Books data/Images")

    # Extraction des urls des catégories
    category_urls_list = get_category_urls(limit=2)

    # Pour chaque catégorie, extraction des urls des livres
    for category_url in category_urls_list:
        category_name, category_books_urls = (
            get_books_urls_from_category(category_url)
        )

        # Création du dossier image de la catégorie
        category_images_folder = create_folder(
            os.path.join(images_folder, category_name)
        )

        # Extraction des données, transformation et sauvegarde
        for book_url in category_books_urls:
            book_data = scrape_book_data(book_url)
            save_book_data_in_csv_file(book_data)
            save_image(
                book_data,
                category_images_folder
            )


main()
