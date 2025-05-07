import requests
from bs4 import BeautifulSoup 
import re # use for tokenise()
import time
from collections import defaultdict
from urllib.parse import urlparse, urljoin
import json


def tokenize(text):
    # Lowercase, remove punctuation, split into words
    words = re.findall(r'\b\w+\b', text.lower())
    return words
        
def crawl(url, visited, depth, inverted_index, url_to_id, id_to_url, DELAY=6):
    if depth == 0 or url in visited:
        return inverted_index, url_to_id, id_to_url
    visited.add(url)

    if url not in url_to_id:
        new_id = len(url_to_id)
        url_to_id[url] = new_id
        id_to_url[new_id] = url
    url_id = url_to_id[url]

    print(f"Visiting: {url}")

    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return inverted_index, url_to_id, id_to_url
    
    time.sleep(DELAY)  # Politeness delay
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get all visible text
    text = soup.get_text(separator=' ', strip=True)
    words = tokenize(text)
    links = soup.find_all('a')
    base_domain = urlparse(url).netloc

    for position, word in enumerate(words):
        if len(word) > 2: 
            inverted_index[word][url_id]["count"] += 1
            inverted_index[word][url_id]["positions"].append(position)
        
    
    for link in links:
        href = link.get('href')
        if href:
            absolute_url = urljoin(url, href)  # Convert relative to absolute
            if urlparse(absolute_url).netloc == base_domain:
                res = crawl(absolute_url, visited, depth - 1, inverted_index, url_to_id, id_to_url, DELAY)
                if res is not None:
                   inverted_index, url_to_id, id_to_url = res

    return inverted_index, url_to_id, id_to_url


def build(url):
    visited = set()  # global set to prevent revisiting
    DELAY = 6 
    inverted_index = defaultdict(lambda: defaultdict(lambda: {"count": 0, "positions": []}))
# e.g. {"life": {0: {"count": 3, "positions": [5, 12, 29]}}}
   
    url_to_id = {}
    id_to_url = {}
    inverted_index, url_to_id, id_to_url = crawl(url, visited, 10, inverted_index, url_to_id, id_to_url, DELAY)
    return inverted_index, url_to_id, id_to_url
    #terms = list(set(tokens1 + tokens2))

def save_inverted_index_only(inverted_index, filename="inverted_index.json"):
    # Convert nested defaultdicts to regular dicts
    serializable_index = {word: dict(postings) for word, postings in inverted_index.items()}
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable_index, f, indent=2)
    
    print(f"Inverted index (only) saved to {filename}")


def load_inverted_index(filename="inverted_index.json"):
    with open(filename, "r", encoding="utf-8") as f:
        inverted_index = json.load(f)
        return inverted_index
    # Convert back to defaultdict for easier manipulation


def save_url_to_id_mapping(url_to_id, filename="url_to_id.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(url_to_id, f, indent=2)
    print(f"URL to ID mapping saved to {filename}")

def save_id_to_url_mapping(id_to_url, filename="id_to_url.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(id_to_url, f, indent=2)
    print(f"ID to URL mapping saved to {filename}")

def load_mappings(filename1="url_to_id.json", filename2="id_to_url.json"):
    with open(filename1, "r", encoding="utf-8") as f:
        url_to_id = json.load(f)
    with open(filename2, "r", encoding="utf-8") as f:
        id_to_url = json.load(f)
    return url_to_id, id_to_url
    


import pprint
# Entry Point
# -------------------------------
if __name__ == "__main__":
    BASE_URL = "https://quotes.toscrape.com/"
    print("\n Student API Command Line Tool")
    inverted_index = None
    while True:
        prompt =  "> "
        command = input(prompt).strip().split()

        if len(command) == 0:
            continue  # ignore empty inputs
        

        if command[0] == "build" and len(command) == 1:
            inverted_index, url_to_id, id_to_url = build(BASE_URL)
            print("Inverted index built!")
            pprint.pprint(dict(inverted_index))

            save_inverted_index_only(inverted_index)
            print("URL to ID mapping:")
            pprint.pprint(url_to_id)
            save_url_to_id_mapping(url_to_id)


            print("ID to URL mapping:")
            pprint.pprint(id_to_url)
            save_id_to_url_mapping(id_to_url)
        elif command[0] == "load" and len(command) == 2:
            inverted_index = load_inverted_index()
            url_to_id, id_to_url = load_mappings()
            print("Mappings loaded!")
            continue

    