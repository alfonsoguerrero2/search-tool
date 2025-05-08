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
                res = crawl(absolute_url, visited, depth - 1, inverted_index, url_to_id, id_to_url)
                if res is not None:
                   inverted_index, url_to_id, id_to_url = res

    return inverted_index, url_to_id, id_to_url


def build(url):
    visited = set()  # global set to prevent revisiting
    inverted_index = defaultdict(lambda: defaultdict(lambda: {"count": 0, "positions": []}))
# e.g. {"life": {0: {"count": 3, "positions": [5, 12, 29]}}}
   
    url_to_id = {}
    id_to_url = {}
    inverted_index, url_to_id, id_to_url = crawl(url, visited, 10, inverted_index, url_to_id, id_to_url)
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

def has_exact_phrase_match(word_positions):
    # Start with positions of the first word
    for start_pos in word_positions[0]:
        match = True
        current_pos = start_pos
        for i in range(1, len(word_positions)):
            next_pos = current_pos + 1
            if next_pos not in word_positions[i]:
                match = False
                break
            current_pos = next_pos
        if match:
            return True  # Found exact phrase match
    return False  # No match found


#Pages with exact phrase matches should be printed at the top (i.e. rated higher than any others)
#followed by pages with non-exact phrase matches but with all words present(with those having a higher frequency appearing before others)
#finally pages with fewer than all words appearing at the bottom of the list
def ranking(list_of_words,url_to_id, id_to_url, inverted_index):
    ids_of_words = []
    valid_words = []

    # 1. Collect all sets of page IDs for each word
    for word in list_of_words:
        if word in inverted_index:
            word_ids = set(inverted_index[word].keys())
            ids_of_words.append(word_ids)
            valid_words.append(word)
        else:
            if len(word) < 3:
                print(f"'{word}' skipped because it is too short.") 
            else: 
                print(f"'{word}'was not found in index. Skipped.")

    num_words = len(valid_words)
    url_id_count = defaultdict(int)

    # 2. Count how many times each URL ID appears across all word sets
    for word_ids in ids_of_words:
        for url_id in word_ids:
            url_id_count[url_id] += 1  # +1 for each word this page contains

    # 3. Group pages by how many words they matched
    grouped_by_matches = defaultdict(list)
    for url_id, count in url_id_count.items():
        grouped_by_matches[count].append(url_id)

    # 4. Build the final result, from "matched all" down to "matched only one"
    # returns a dict that containes all the labels exact pages, and from top matched to least mattched, and the count od each 
    result = {
    "exact matches": []
    }
    for i in range(num_words, 0, -1): 
        label = f"{i}/{num_words} words matched"
         # from n to 1
        if label not in result:
            result[label] = []

        for url_id in grouped_by_matches[i]:
            # all the words matched
            page = []
            count = 0
            if i == num_words:
                # check for a phrase exact match
                word_positions = []
                for word in valid_words:
                    word_positions.append(inverted_index[word][url_id]["positions"])
                    count = count + inverted_index[word][url_id]["count"]
                
                if has_exact_phrase_match(word_positions):
                    page.append(url_id)
                    page.append(0)
                    result["exact matches"].append(page)
                    continue
                else:
                    page.append(url_id)
                    page.append(count)
                    result[label].append(page)
            else:
                for word in valid_words:
                    if url_id in inverted_index[word]:
                        count = count + inverted_index[word][url_id]["count"]
                page.append(url_id)
                page.append(count)
                result[label].append(page)

    return result

def output_results(result, url_to_id, id_to_url):
    # Print the results in a readable format
    for label, pages in result.items():
        
        if not pages:
            if label != "exact matches" and label.startswith("1/") or label.startswith("2/"):
                continue
            print(f"\n{label}:\nNo matches.")
            continue
        print(f"\n{label}:")
        sorted_pages = sorted(pages, key=lambda x: x[1], reverse=True)
        for page in sorted_pages:
            url_id = page[0]
            count = page[1]
            if url_id in id_to_url and label != "exact matches":
                print(f"URL: {id_to_url[url_id]}, Frequency: {count}")
            elif url_id in id_to_url and label == "exact matches":
                print(f"Exact match URL: {id_to_url[url_id]} ")
            else:
                print(f"URL ID {url_id} not found in mapping.")

    return


import pprint
# Entry Point
if __name__ == "__main__":
    BASE_URL = "https://quotes.toscrape.com/"
    print("\n search Command Line Tool")
    inverted_index = None
    url_to_id, id_to_url = None, None
    while True:
        prompt =  "> "
        command = input(prompt).strip().split()

        if len(command) == 0:
            print("No command entered. Please try again.")
            continue
        

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

        elif command[0] == "load" and len(command) == 1:
            inverted_index = load_inverted_index()
            url_to_id, id_to_url = load_mappings()
            print("Inverted index loaded!")
            print("Mappings loaded!")
            continue

        elif command[0] == "print" and len(command) == 2:
            if inverted_index is not None and url_to_id is not None:
                word = command[1]
                if word in inverted_index:
                    print(f"Inverted index for '{word}':")
                    pprint.pprint(dict(inverted_index[word]))
                else:
                    print(f"'{word}' not found in the inverted index.")
            else: 
                print("Inverted index or mappings not loaded.")
        



        elif command[0] == "find":
            if inverted_index is not None and url_to_id is not None:
                if len(command) < 1:
                    print("Please provide a phrase or words to search for.")  
                else:    
                    if inverted_index is not None and url_to_id is not None and id_to_url is not None:
                        list_of_words = command[1:]
                        results = ranking(list_of_words,url_to_id, id_to_url, inverted_index)
                        if all(len(pages) == 0 for pages in results.values()):
                            print("No results found.")
                            
                        else:
                            output_results(results, url_to_id, id_to_url)
            else:
                print("Inverted index or mappings not loaded. Please build or load them first.")


  
        elif command[0] == "exit":
            print("Exiting...")
            break
        
        else:
            print("Invalid command. Please try again.")