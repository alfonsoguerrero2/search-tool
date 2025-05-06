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

    for word in words:
        inverted_index[word][url_id] += 1
    
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
    inverted_index = defaultdict(lambda: defaultdict(int))
    url_to_id = {}
    id_to_url = {}
    inverted_index, url_to_id, id_to_url = crawl(url, visited, 10, inverted_index, url_to_id, id_to_url, DELAY)
    return inverted_index, id_to_url
    #terms = list(set(tokens1 + tokens2))

def save_inverted_index_only(inverted_index, filename="inverted_index.json"):
    # Convert nested defaultdicts to regular dicts
    serializable_index = {word: dict(postings) for word, postings in inverted_index.items()}
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable_index, f, indent=2)
    
    print(f"Inverted index (only) saved to {filename}")


import pprint


# Entry Point
# -------------------------------
if __name__ == "__main__":
    BASE_URL = "https://quotes.toscrape.com/"
    print("\n Student API Command Line Tool")
    inverted_index = None
    id_to_url = None
    while True:
        prompt =  "> "
        command = input(prompt).strip().split()

        if len(command) == 0:
            continue  # ignore empty inputs
        

        if command[0] == "build" and len(command) == 1:
            inverted_index, id_to_url = build(BASE_URL)
            print("Inverted index built!")
            pprint.pprint(dict(inverted_index))
            save_inverted_index_only(inverted_index)
        elif command[0] == "load" and len(command) == 2:
            continue

    