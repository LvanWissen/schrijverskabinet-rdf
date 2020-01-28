import time
import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

from rdflib import Graph, URIRef, Literal, XSD, Namespace, RDFS, BNode, OWL
from rdfalchemy import rdfSubject, rdfMultiple, rdfSingle

PORTRETURL = "http://www.schrijverskabinet.nl/schrijverskabinet/"

schema = Namespace("https://schema.org/")
bio = Namespace("http://purl.org/vocab/bio/0.1/")
foaf = Namespace("http://xmlns.com/foaf/0.1/")

ns = Namespace(
    "https://data.create.humanities.uva.nl/id/datasets/schrijverskabinet/")


class Entity(rdfSubject):
    rdf_type = URIRef('urn:entity')

    label = rdfMultiple(RDFS.label)
    name = rdfMultiple(schema.name)

    mainEntityOfPage = rdfSingle(schema.mainEntityOfPage)
    sameAs = rdfMultiple(OWL.sameAs)

    disambiguatingDescription = rdfSingle(schema.disambiguatingDescription)

    depiction = rdfSingle(foaf.depiction)


class CreativeWork(Entity):
    rdf_type = schema.CreativeWork

    publication = rdfMultiple(schema.publication)
    author = rdfMultiple(schema.author)

    mainEntity = rdfSingle(schema.mainEntity)
    about = rdfSingle(schema.about)


class ScholarlyArticle(CreativeWork):
    rdf_type = schema.ScholarlyArticle


class VisualArtwork(CreativeWork):
    rdf_type = schema.VisualArtwork

    artist = rdfSingle(schema.artist)


class PublicationEvent(Entity):
    rdf_type = schema.PublicationEvent

    startDate = rdfSingle(schema.startDate)
    location = rdfSingle(schema.location)

    publishedBy = rdfMultiple(schema.publishedBy)


class Place(Entity):
    rdf_type = schema.Place


class Marriage(Entity):
    rdf_type = bio.Marriage

    date = rdfSingle(bio.date)
    partner = rdfMultiple(bio.partner)
    place = rdfSingle(bio.place)

    subjectOf = rdfMultiple(schema.subjectOf)


class Person(Entity):
    rdf_type = schema.Person

    birthPlace = rdfSingle(schema.birthPlace)
    deathPlace = rdfSingle(schema.deathPlace)

    birthDate = rdfSingle(schema.birthDate)
    deathDate = rdfSingle(schema.deathDate)


def main(loadData=None):

    if loadData:
        with open(loadData, 'r', encoding='utf-8') as infile:
            DATA = json.load(infile)
    else:
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

    #######
    # RDF #
    #######

    toRDF(DATA)


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
        quote = quote.replace(u'\u00a0', '')
        quote = quote.strip()

    depiction = soup.find('img')['src']
    if 'portrait-no-image' in depiction:
        depiction = None
    else:
        depiction = URIRef(depiction)

    data['painter'] = painter
    data['date'] = date
    data['origin'] = origin
    data['article'] = article
    data['dbnl'] = dbnl
    data['quote'] = quote
    data['depiction'] = depiction

    if sleep:
        time.sleep(sleep)

    return data


def toRDF(d):

    g = rdfSubject.db = Graph(identifier=ns)

    for url in d['portrets']:
        data = d['portrets'][url]

        sameAs = []

        if data['dbnl']['url'] and 'http' in data['dbnl']['url']:
            _, dataBib = data['dbnl']['url'].split('?id=')
            dataBib = URIRef("http://data.bibliotheken.nl/id/dbnla/" + dataBib)
            sameAs.append(dataBib)

        try:
            birth, death = data['bio'].replace('-', ' –').split(' – ')
        except:
            print(data['bio'])

        try:
            birthPlace, birthYear = birth.rsplit(' ', 1)
        except:
            print(birth)
            birthPlace, birthYear = None, None
        try:
            deathPlace, deathYear = death.rsplit(' ', 1)
        except:
            print(death)
            deathPlace, deathYear = None, None

        p = Person(
            None,
            name=[Literal(data['title'])],
            sameAs=sameAs,
            birthPlace=Place(BNode("".join(
                [i for i in birthPlace if i in 'abcdefghijklmnopqrstuvwxyz'])),
                             name=[birthPlace]) if birthPlace else None,
            birthDate=Literal(birthYear, datatype=XSD.gYear, normalize=False)
            if birthYear else None,
            deathPlace=Place(BNode("".join(
                [i for i in deathPlace if i in 'abcdefghijklmnopqrstuvwxyz'])),
                             name=[deathPlace]) if deathPlace else None,
            deathDate=Literal(deathYear, datatype=XSD.gYear, normalize=False)
            if deathYear else None,
            disambiguatingDescription=data['subtitle'],
            depiction=data['depiction'])
        page = CreativeWork(URIRef(url))

        if data['article']['name']:

            name, author = data['article']['name'].rsplit(' door ', 1)

            author = Person(BNode("".join(
                [i for i in author if i in 'abcdefghijklmnopqrstuvwxyz'])),
                            name=[author])

            article = ScholarlyArticle(URIRef(data['article']['url']),
                                       name=[name],
                                       author=[author],
                                       about=p)

        if data['painter']:
            painter = Person(BNode("".join([
                i for i in data['painter'] if i in 'abcdefghijklmnopqrstuvwxyz'
            ])),
                             name=[data['painter']])

            artwork = VisualArtwork(None, artist=painter, about=p)

        page.mainEntity = p
        p.mainEntityOfPage = page

    g.bind('schema', schema)
    g.serialize('data/data.trig', format='trig')


if __name__ == "__main__":
    main(loadData='data/data.json')