#! /usr/bin/env python3
# antwiki_taxonomy_scraper.py by Marek Borowiec
# created 27 April 2018
# this script downloads higher ant taxonomy
# given a list of genera URLs on www.AntWiki.org

from collections import defaultdict
import multiprocessing as mp
from datetime import date
from sys import argv
import re
from urllib import request

from bs4 import BeautifulSoup

# the input file should have one URL per line
script, genera_url = argv

# Day, textual month, year
today = date.today()
todays_date = today.strftime('%d %b %Y')

def tree():
    return defaultdict(tree)

def get_classification(page_url):
    """Find names of subfamily, tribe and genus on genus page."""
    # Seems like these are contained within classes
    # subfamily and tribe under <a title>
    # and genus is found under genus class under <i><b>
    html = request.urlopen(page_url)
    page_soup = BeautifulSoup(html, 'html.parser')
    subfamily = page_soup.find(attrs = {'class': 'subfamily'}).find('a')['title']
    try:
        tribe = page_soup.find(attrs = {'class': 'tribe'}).find('a')['title']
    except (AttributeError, TypeError) as e:
        tribe = None
    try:
        genus = page_soup.find(attrs = {'class': 'genus'}).i.b.text
        species_no = page_soup.find(attrs = {'title': f'Category:{genus} species'}).text
        print(f'Fetching data for genus {genus}...')
        txt = page_soup.get_text()
        if re.search(r'Invalid genus', txt):
            print(f'Warning: genus {genus} may no longer be valid')
    except (AttributeError, TypeError) as e:
        print(f'Error: genus not found for URL {page_url} {e}')
        genus = None
    try:
        # this will also include valid subgenera
        synonyms = page_soup.find(attrs = {'style': 'text-align: left'}).find_all('i')
        parsed_syns = [synonym_tag.text for synonym_tag in synonyms]
    except (AttributeError, TypeError) as e:
        parsed_syns = ''
    if genus:
        genus_tpl = (genus, species_no)
        if tribe:
            return (subfamily, tribe, genus_tpl, parsed_syns)
        else:
            tribe = ''
            return (subfamily, tribe, genus_tpl, parsed_syns)
    else:
        print(f'No genus name was found in {page_url}. Perhaps this is a subgenus?')

def add_classification(taxonomy, clas):
    """Add classification to existing taxonomy tree"""
    subfamily, tribe, genus_tpl, syns = clas
    print(f'Adding classification data for {genus_tpl[0]}')
    taxonomy[subfamily][tribe][genus_tpl]['@'.join(syns)]

def process_classification(classification, taxonomy):
    add_classification(taxonomy, classification) 

taxonomy = tree()

# open input file with a list of URLs
with open(genera_url) as f:
    urls = f.read().splitlines()

# use multiprocessing to get HTML from the URLs
pool = mp.Pool(2) 
classifications = pool.map(get_classification, urls)

[process_classification(classification, taxonomy) for classification in classifications]

with open('species-table.txt', 'w') as tf:
    for subfamily in sorted(taxonomy):
        for tribe in sorted(taxonomy[subfamily]):
            for genus_tpl in sorted(taxonomy[subfamily][tribe]):
                genus_name, species_no = genus_tpl
                tf.write(f'{genus_name}\t{species_no}\n')

# write appropriately formatted results to a file
with open('classification.md', 'w') as file:
    wiki = 'http://www.antwiki.org/wiki/'
    file.write(f'Information from antwiki.org obtained on {todays_date}\n\n\n')
    for subfamily in sorted(taxonomy):
        pad = '&nbsp;'
        file.write(f'**Subfamily** [**{subfamily}**]({wiki}{subfamily})<br/>\n')
        for tribe in sorted(taxonomy[subfamily]):
            if tribe:
                file.write(f'{pad * 6} **Tribe** [**{tribe}**]({wiki}{tribe})<br/>\n')
            for genus_tpl in sorted(taxonomy[subfamily][tribe]):
                genus_name, species_no = genus_tpl
                file.write(f'{pad * 12} Genus [*{genus_name}*]({wiki}{genus_name}) {species_no}<br/>\n')
                for synonyms in taxonomy[subfamily][tribe][genus_tpl]:
                    if synonyms:
                        syn_list = sorted(synonyms.split('@'))
                        for syn in syn_list:
                            file.write(f'{pad * 20} = [{syn}]({wiki}{syn})<br/>\n')
