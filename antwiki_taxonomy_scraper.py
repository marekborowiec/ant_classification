#! /usr/bin/env python3
# antwiki_taxonomy_scraper.py by Marek Borowiec
# created 27 April 2018
# this script downloads higher ant taxonomy
# given a list of genera URLs on www.AntWiki.org

from collections import defaultdict
import multiprocessing as mp
from sys import argv
import re
from urllib import request

from bs4 import BeautifulSoup

# the input file should have one URL per line
script, genera_url = argv

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
    except AttributeError:
        tribe = None
    try:
        genus = page_soup.find(attrs = {'class': 'genus'}).i.b.text
        print(f'Fetching data for genus {genus}...')
    except AttributeError:
        genus = None
    try:
        # this will also include valid subgenera
        synonyms = page_soup.find(attrs = {'style': 'text-align: left'}).find_all('i')
        parsed_syns = [synonym_tag.text for synonym_tag in synonyms]
    except AttributeError:
        parsed_syns = ''
    if genus:
        if tribe:
            return (subfamily, tribe, genus, parsed_syns)
        else:
            tribe = ''
            return (subfamily, tribe, genus, parsed_syns)
    else:
        print(f'No genus name was found in {page_url}. Perhaps this is a subgenus?')

def add_classification(taxonomy, clas):
    """Add classification to existing taxonomy tree"""
    subfamily, tribe, genus, syns = clas
    print(f'Adding classification data for {genus}')
    taxonomy[subfamily][tribe][genus]['@'.join(syns)]

def process_classification(classification, taxonomy):
    add_classification(taxonomy, classification) 

taxonomy = tree()

# open input file with a list of URLs
with open(genera_url) as f:
    urls = f.read().splitlines()

# use multiprocessing to get HTML from the URLs
pool = mp.Pool(24) 
classifications = pool.map(get_classification, urls)

[process_classification(classification, taxonomy) for classification in classifications]

# write appropriately formatted results to a file
with open('classification.md', 'w') as file:
    wiki = 'http://www.antwiki.org/wiki/'
    for subfamily in sorted(taxonomy):
        pad = '&nbsp;'
        file.write(f'**Subfamily** [**{subfamily}**]({wiki}{subfamily})<br/>\n')
        for tribe in sorted(taxonomy[subfamily]):
            if tribe:
                file.write(f'{pad * 6} **Tribe** [**{tribe}**]({wiki}{tribe})<br/>\n')
            for genus in sorted(taxonomy[subfamily][tribe]):
                file.write(f'{pad * 12} Genus [*{genus}*]({wiki}{genus})<br/>\n')
                for synonyms in taxonomy[subfamily][tribe][genus]:
                    if synonyms:
                        syn_list = sorted(synonyms.split('@'))
                        for syn in syn_list:
                            file.write(f'{pad * 20} = [{syn}]({wiki}{syn})<br/>\n')