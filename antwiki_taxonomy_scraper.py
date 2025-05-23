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
    try:
        html = request.urlopen(page_url)
        page_soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL {page_url}: {e}")
        return None
    
    subfamily_tag = page_soup.find(attrs={'class': 'subfamily'})
    if subfamily_tag is None:
        print(f"Warning: 'subfamily' not found in {page_url}")
        return None
    subfamily_link = subfamily_tag.find('a')
    if subfamily_link is None:
        print(f"Warning: subfamily link not found in {page_url}")
        return None
    subfamily = subfamily_link.get('title', None)
    
    tribe_tag = page_soup.find(attrs={'class': 'tribe'})
    tribe = None
    if tribe_tag:
        tribe_link = tribe_tag.find('a')
        if tribe_link:
            tribe = tribe_link.get('title', None)
    
    genus = None
    species_no = None
    try:
        genus_tag = page_soup.find(attrs={'class': 'genus'})
        if genus_tag and genus_tag.i and genus_tag.i.b:
            genus = genus_tag.i.b.text
        else:
            print(f"Warning: genus tag or sub-elements missing in {page_url}")
        
        if genus:
            species_tag = page_soup.find(attrs={'title': f'Category:{genus} species'})
            if species_tag:
                species_no = species_tag.text
            else:
                print(f"Warning: species count tag missing for genus {genus} in {page_url}")

            print(f'Fetching data for genus {genus}...')
            txt = page_soup.get_text()
            if re.search(r'Invalid genus', txt):
                print(f'Warning: genus {genus} may no longer be valid')
    except Exception as e:
        print(f"Error processing genus data in {page_url}: {e}")
    
    synonyms = []
    try:
        synonym_container = page_soup.find(attrs={'style': 'text-align: left'})
        if synonym_container:
            synonyms = [syn.text for syn in synonym_container.find_all('i')]
    except Exception as e:
        print(f"Error fetching synonyms in {page_url}: {e}")
    
    if genus:
        genus_tpl = (genus, species_no if species_no else "")
        return (subfamily, tribe if tribe else "", genus_tpl, synonyms)
    else:
        print(f'No genus name was found in {page_url}. Perhaps this is a subgenus or page format changed?')
        return None

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

# Filter out None results
classifications = [c for c in classifications if c is not None]

[process_classification(classification, taxonomy) for classification in classifications]

with open('species-table.txt', 'w') as tf:
    for subfamily in sorted(taxonomy):
        for tribe in sorted(taxonomy[subfamily]):
            for genus_tpl in sorted(taxonomy[subfamily][tribe]):
                genus_name, species_no = genus_tpl
                tf.write(f'{genus_name}\t{species_no}\n')

with open('species-table-no-tribes.txt', 'w') as tf:
    for subfamily in sorted(taxonomy):
        genera_by_subfamily = []
        for tribe in sorted(taxonomy[subfamily]):
            for genus_tpl in sorted(taxonomy[subfamily][tribe]):
                genus_name, species_no = genus_tpl
                genera_by_subfamily.append(genus_tpl)
        genera_by_subfamily.sort()
        for genus_tpl in genera_by_subfamily:
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
