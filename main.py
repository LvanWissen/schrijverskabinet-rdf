import time
import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

PORTRETURL = "http://www.schrijverskabinet.nl/schrijverskabinet/"


def main():

    DATA = {
        'portrets': {},
        'metadata': {
            'date': datetime.datetime.now().isoformat()
        }
    }

    # fetch all urls to scrape
    urls = fetchUrls(url=PORTRETURL)

    # fetch from individual pages
    for n, url in enumerate(urls):
        print(f"{n}/{len(urls)}\tFetching {url}")
        pageData = fetchPortretPage(url)

        DATA['portrets'][url] = pageData

    # dump file
    with open('data/data.json', 'w', encoding='utf-8') as outfile:
        json.dump(DATA, outfile, indent=4)


def fetchUrls(url):

    r = requests.get(url)

    urls = re.findall(r'(http:\/\/www\.schrijverskabinet\.nl\/portret\/.*?)"',
                      r.text)

    return urls


def fetchPortretPage(url, sleep=1):

    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    data = dict()

    data['title'] = soup.h1.text
    data['subtitle'] = soup.h2.text if soup.h2 else None

    biodiv = soup.find('div', class_='date-of-birth-and-death')
    data['bio'] = biodiv.text.strip() if biodiv else None

    painter = soup.find('div', class_='label',
                        text='Schilder').find_next_sibling("div").text.strip()
    date = soup.find('div', class_='label',
                     text='Datering').find_next_sibling("div").text.strip()

    origin_el = soup.find('div', class_='label',
                          text='Vindplaats').find_next_sibling("div")
    origin = {
        'name': origin_el.text.strip(),
        'url': origin_el.find('a')['href'] if origin_el.find('a') else None
    }

    article_el = soup.find('div', class_='label',
                           text='Artikel').find_next_sibling("div")
    article = {
        'name':
        None if article_el.text.strip() == 'Geen' else article_el.text.strip(),
        'url':
        article_el.find('a')['href'] if article_el.find('a') else None
    }

    dbnl_el = soup.find('div', class_='label',
                        text='DBNL-profiel').find_next_sibling("div")
    dbnl = {
        'name':
        None if dbnl_el.text.strip() == 'Geen' else dbnl_el.text.strip(),
        'url': dbnl_el.find('a')['href'] if dbnl_el.find('a') else None
    }

    quote = soup.find('div', {'id': 'portrait-quote'})
    if quote:
        quote = quote.text.replace(u'\xa0', ' ')

    data['painter'] = painter
    data['date'] = date
    data['origin'] = origin
    data['article'] = article
    data['dbnl'] = dbnl
    data['quote'] = quote

    if sleep:
        time.sleep(sleep)

    return data


if __name__ == "__main__":
    print(main())