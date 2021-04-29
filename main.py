"""
Pipeline that converts the data from http://www.schrijverskabinet.nl/ into RDF. 

Built upon an adapted version of RDFAlchemy for Python (3.7). Install with:

```bash
pip install git+https://github.com/LvanWissen/RDFAlchemy.git
```

Contact:
    Leon van Wissen (l.vanwissen@uva.nl)

"""

import os
import time
import datetime
import json
import re
from itertools import count

from unidecode import unidecode

import requests
from bs4 import BeautifulSoup

import rdflib
from rdflib import Dataset, URIRef, BNode, Literal, Namespace, XSD, RDFS, OWL
from rdfalchemy import rdfSubject, rdfMultiple, rdfSingle

PORTRETURL = "http://www.schrijverskabinet.nl/schrijverskabinet/"

create = Namespace("https://data.create.humanities.uva.nl/")
schema = Namespace("http://schema.org/")
sem = Namespace("http://semanticweb.cs.vu.nl/2009/11/sem/")
bio = Namespace("http://purl.org/vocab/bio/0.1/")
foaf = Namespace("http://xmlns.com/foaf/0.1/")
void = Namespace("http://rdfs.org/ns/void#")
dcterms = Namespace("http://purl.org/dc/terms/")

rdflib.graph.DATASET_DEFAULT_GRAPH_ID = create

ns = Namespace("https://data.create.humanities.uva.nl/id/schrijverskabinet/")

nsPerson = Namespace(
    "https://data.create.humanities.uva.nl/id/schrijverskabinet/person/")

nsArtwork = Namespace(
    "https://data.create.humanities.uva.nl/id/schrijverskabinet/artwork/")


class Entity(rdfSubject):
    rdf_type = URIRef('urn:entity')

    label = rdfMultiple(RDFS.label)
    name = rdfMultiple(schema.name)
    description = rdfMultiple(schema.description)

    mainEntityOfPage = rdfSingle(schema.mainEntityOfPage)
    sameAs = rdfMultiple(OWL.sameAs)

    disambiguatingDescription = rdfSingle(schema.disambiguatingDescription)

    depiction = rdfSingle(foaf.depiction)
    subjectOf = rdfMultiple(schema.subjectOf)
    about = rdfSingle(schema.about)
    url = rdfSingle(schema.url)

    inDataset = rdfSingle(void.inDataset)


class CreativeWork(Entity):
    rdf_type = schema.CreativeWork

    publication = rdfMultiple(schema.publication)
    author = rdfMultiple(schema.author)

    text = rdfSingle(schema.text)

    mainEntity = rdfSingle(schema.mainEntity)


class DatasetClass(Entity):

    # db = ConjunctiveGraph

    rdf_type = void.Dataset, schema.Dataset

    title = rdfMultiple(dcterms.title)
    description = rdfMultiple(dcterms.description)
    descriptionSchema = rdfMultiple(schema.description)
    creator = rdfMultiple(schema.creator)
    publisher = rdfMultiple(dcterms.publisher)
    publisherSchema = rdfMultiple(schema.publisher)
    contributor = rdfMultiple(dcterms.contributor)
    contributorSchema = rdfMultiple(schema.contributor)
    source = rdfSingle(dcterms.source)
    isBasedOn = rdfSingle(schema.isBasedOn)
    date = rdfSingle(dcterms.date)
    dateCreated = rdfSingle(schema.dateCreated)
    created = rdfSingle(dcterms.created)
    issued = rdfSingle(dcterms.issued)
    modified = rdfSingle(dcterms.modified)

    exampleResource = rdfSingle(void.exampleResource)
    vocabulary = rdfMultiple(void.vocabulary)
    triples = rdfSingle(void.triples)

    distribution = rdfSingle(schema.distribution)
    licenseprop = rdfSingle(schema.license)

    alternateName = rdfMultiple(schema.alternateName)
    citation = rdfMultiple(schema.citation)

    keywords = rdfMultiple(schema.keywords)
    spatialCoverage = rdfSingle(schema.spatialCoverage)
    temporalCoverage = rdfSingle(schema.temporalCoverage)

    version = rdfSingle(schema.version)


class DataDownload(CreativeWork):
    rdf_type = schema.DataDownload

    contentUrl = rdfSingle(schema.contentUrl)
    encodingFormat = rdfSingle(schema.encodingFormat)


class ScholarlyArticle(CreativeWork):
    rdf_type = schema.ScholarlyArticle


class VisualArtwork(CreativeWork):
    rdf_type = schema.VisualArtwork

    artist = rdfMultiple(schema.artist)

    dateCreated = rdfSingle(schema.dateCreated)
    dateModified = rdfSingle(schema.dateModified)

    temporal = rdfSingle(schema.temporal)


class PublicationEvent(Entity):
    rdf_type = schema.PublicationEvent

    startDate = rdfSingle(schema.startDate)
    hasEarliestBeginTimeStamp = rdfSingle(sem.hasEarliestBeginTimeStamp)
    hasLatestEndTimeStamp = rdfSingle(sem.hasLatestEndTimeStamp)

    location = rdfSingle(schema.location)

    publishedBy = rdfMultiple(schema.publishedBy)


class Place(Entity):
    rdf_type = schema.Place


class Person(Entity):
    rdf_type = schema.Person

    birthPlace = rdfSingle(schema.birthPlace)
    deathPlace = rdfSingle(schema.deathPlace)

    birthDate = rdfSingle(schema.birthDate)
    deathDate = rdfSingle(schema.deathDate)


def main(loadData: str = None, target: str = 'data/schrijverskabinet.trig'):
    """Main function that starts the scraping and conversion to RDF.

    Args:
        loadData (str, optional): File pointer to a json file with earlier 
        scraped data. If supplied, the data will not be fetched again. 
        Defaults to None.
        target (str, optional): Destination file location. Defaults to 
        'data/schrijverskabinet.trig'.       
    """

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
        pages = fetchUrls(url=PORTRETURL)

        # fetch from individual pages
        for n, (url, img) in enumerate(pages, 1):
            print(f"{n}/{len(pages)}\tFetching {url}")
            pageData = fetchPortretPage(url, img)

            DATA['portrets'][url] = pageData

        # dump file
        with open('data/data.json', 'w', encoding='utf-8') as outfile:
            json.dump(DATA, outfile, indent=4)

    #######
    # RDF #
    #######

    toRDF(DATA, target=target)


def fetchUrls(url: str):
    """Fetches portrait data (info + image) from an overview portrait page.

    Args:
        url (str): The url to download

    Returns:
        list: List of tuples with an url + img src for the portraits on the
        overview page.
    """

    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    portraits = soup.findAll('a', class_='portrait')

    pagedata = []
    for portrait in portraits:
        url = portrait['href']
        el_img = portrait.find('img', recursive=False)

        img = el_img.get('data-lazy-src', el_img['src'])

        pagedata.append((url, img))

    return pagedata


def fetchPortretPage(url: str, img: str, sleep: int = 1):
    """Download data from an individual portrait page.

    Args:
        url (str): URL to the page
        img (str): URL to the image (thumbnail for the page)
        sleep (int, optional): Wait before returning (to not overload the 
        server). Defaults to 1.

    Returns:
        dict: Dictionary with structured data from the portrait page. 
    """

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
        'url':
        origin_el.find('a')['href'].strip() if origin_el.find('a') else None
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
        'url': dbnl_el.find('a')['href'].strip() if dbnl_el.find('a') else None
    }

    quote = soup.find('div', {'id': 'portrait-quote'})
    if quote:
        quote = quote.text.replace(u'\xa0', ' ')
        quote = quote.replace(u'\u00a0', '')
        quote = quote.strip()

    if 'portrait-no-image-overview' in img or 'Vrouw01' in img:
        img = None
    else:
        img = URIRef(img)

    artdepiction = soup.find('img')['src']

    # If there is no poëticon-portrait, don't include the (modern) image
    if img is None:
        artdepiction = None
    elif 'portrait-no-image' in artdepiction or 'Vrouw01' in artdepiction:
        artdepiction = None
    else:
        artdepiction = URIRef(artdepiction)

    data['painter'] = painter
    data['date'] = date
    data['origin'] = origin
    data['article'] = article
    data['dbnl'] = dbnl
    data['quote'] = quote
    data['depiction'] = img
    data['artdepiction'] = artdepiction

    if sleep:
        time.sleep(sleep)

    return data


def normalize_name(name: str):
    """Normalize a name for usage in a URI by replacing spaces with hyphens, 
    lowercasing it, transforming it to ASCII, and by stripping it of non-alpha 
    characters.

    Args:
        name (str): An entity's name

    Returns:
        str: Normalized name that can be used in a URI

    >>> normalize_name("Arnoud van Halen")
    "arnoud-van-halen"
    """

    name = name.lower().replace(' ', '-')
    name = unidecode(name)

    name = "".join([i for i in name if i in 'abcdefghijklmnopqrstuvwxyz-'])

    return name


def person2uri(name: str, data: dict):
    """Convert a reference to a person (str) to an URIRef.
    Function to keep an URI for a reference of person (based on uniqueness of 
    string). The data argument (dict) is used to store the references. 

    Args:
        name (str): A person's name
        data (dict): Dictionary to store the reference for reuse

    Returns:
        tuple: URI or BNode to identify a person and the dictionary
    """

    name = normalize_name(name)

    if name == "onbekend":
        return BNode(), data

    uri = data.get(name, None)
    if uri:
        return URIRef(uri), data
    else:

        data[name] = nsPerson.term(name)
        return data[name], data


def datePortretParser(date: str):
    """Return a PublicationEvent with filled dates for a date string.

    Args:
        date (str): Date reference from the portrait page

    Returns:
        PublicationEvent: PublicationEvent with hasEarliestBeginTimeStamp and
        hasLatestEndTimeStamp properties filled for the publication year.
    """

    date = date.strip()

    if date.isdigit():
        begin = date
        end = date
    elif ' en ' in date:
        dateCreated, dateModified = date.split(' en ')
        dateCreated = dateCreated.strip().replace('(', '').replace(')', '')
        dateModified = dateModified.strip().replace('(', '').replace(')', '')

        # for now only creation

        begin, end = dateCreated.split(' – ')
        begin = begin.strip()
        end = end.strip()

    elif ' – ' in date:
        begin, end = date.split(' – ')
        begin = begin.strip()
        end = end.strip()

    else:
        return []

    return [
        PublicationEvent(None,
                         hasEarliestBeginTimeStamp=Literal(f"{begin}-01-01",
                                                           datatype=XSD.date),
                         hasLatestEndTimeStamp=Literal(f"{end}-12-31",
                                                       datatype=XSD.date))
    ]


def toRDF(d: dict, target: str):
    """Convert the earlier harvested and structured data to RDF.

    Args:
        d (dict): Dictionary with structured portrait information, coming from 
        the loadData() function. 
        target (str): Destination file path.
    """

    ds = Dataset()
    g = rdfSubject.db = ds.graph(identifier=ns)

    try:
        with open('data/persondata.json') as infile:
            persondata = json.load(infile)
    except:
        persondata = dict()

    with open('data/artist2dbnl.json') as infile:
        artist2dbnl = json.load(infile)

    # Links for artists to DBNL. Stored in separate json file.
    for subject, object in artist2dbnl.items():
        if object:
            g.add((URIRef(subject), OWL.sameAs, URIRef(object)))

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
            print("bio:", data['bio'])
            birth, death = "", ""

        try:
            birthPlace, birthYear = birth.rsplit(' ', 1)
            birthPlace = birthPlace.replace('ca.',
                                            '').replace(' na ', '').replace(
                                                '(?)', '').strip()
        except:
            if birth.isdigit():
                birthYear = birth
                birthPlace = None
            else:
                birthPlace, birthYear = None, None
        try:
            deathPlace, deathYear = death.rsplit(' ', 1)
            deathPlace = deathPlace.replace('ca.',
                                            '').replace(' na ', '').replace(
                                                '(?)', '').strip()
        except:
            if death.isdigit():
                deathYear = death
                deathPlace = None
            else:
                deathPlace, deathYear = None, None

        # onbekend
        if birthYear and not birthYear.isdigit():
            birthYear = None
        if deathYear and not deathYear.isdigit():
            deathYear = None

        #############
        # Resources #
        #############

        subjectOf = []
        puri, persondata = person2uri(data['title'], persondata)
        p = Person(
            puri,
            name=[Literal(data['title'])],
            sameAs=sameAs,
            birthPlace=Place(BNode(normalize_name(birthPlace)),
                             name=[birthPlace])
            if birthPlace and birthPlace.lower() != 'onbekend' else None,
            birthDate=Literal(birthYear, datatype=XSD.gYear, normalize=False)
            if birthYear else None,
            deathPlace=Place(BNode(normalize_name(deathPlace)),
                             name=[deathPlace])
            if deathPlace and deathPlace.lower() != 'onbekend' else None,
            deathDate=Literal(deathYear, datatype=XSD.gYear, normalize=False)
            if deathYear else None,
            disambiguatingDescription=data['subtitle'],
            depiction=URIRef(data['depiction']) if data['depiction'] else None,
        )

        page = CreativeWork(URIRef(url), text=data['quote'])

        if data['article']['name']:

            name, author = data['article']['name'].rsplit(' door ', 1)

            authoruri, persondata = person2uri(author, persondata)
            author = Person(authoruri, name=[author])

            article = ScholarlyArticle(URIRef(data['article']['url']),
                                       name=[name.strip()],
                                       author=[author],
                                       about=p)
            subjectOf.append(article)

        if data['painter']:

            painters = []
            painternames = []
            name = data['painter']

            name = name.strip()
            if name.endswith(')'):
                name, _ = name.rsplit(' (', 1)

            # dirty hardcoded fix
            if name == "Tweemaal door Arnoud van Halen en ('in zijnen laatsten leeftijd' door) Jan Maurits Quinkhard":
                name = "Arnoud van Halen en Jan Maurits Quinkhard"

            if name == "Tweemaal door Jan Maurits Quinkhard":
                name = "Jan Maurits Quinkhard"

            if ', verbeterd door ' in name:
                painternames += name.split(', verbeterd door ')
            elif ', vervangen door ' in name:
                painternames.append(name.split(', vervangen door ')[1])
            elif ' en ' in name:
                painternames += name.split(' en ')
            elif ' of ' in name:
                painternames += name.split(' of ')
            else:
                painternames.append(name)

            for paintername in painternames:
                painteruri, persondata = person2uri(paintername, persondata)
                painter = Person(painteruri, name=[paintername])
                painters.append(painter)

            publicationEvent = datePortretParser(data['date'])

            # She has two portraits
            if url == "http://www.schrijverskabinet.nl/portret/anna-maria-van-schurman/":
                artworkURI = nsArtwork.term(
                    normalize_name(data['title']) + '-1')
            elif url == "http://www.schrijverskabinet.nl/portret/anna-maria-van-schurman-2/":
                artworkURI = nsArtwork.term(
                    normalize_name(data['title']) + '-2')
            else:
                artworkURI = nsArtwork.term(normalize_name(data['title']))

            artwork = VisualArtwork(artworkURI,
                                    artist=painters,
                                    about=p,
                                    name=[
                                        Literal(f"Portret van {data['title']}",
                                                lang='nl'),
                                        Literal(f"Portrait of {data['title']}",
                                                lang='en')
                                    ],
                                    depiction=URIRef(data['artdepiction'])
                                    if data['artdepiction'] else None,
                                    temporal=Literal(data['date'], lang='nl'),
                                    publication=publicationEvent)
            subjectOf.append(artwork)

            if data['origin']['name']:
                artwork.description = [
                    Literal(data['origin']['name'], lang='nl')
                ]

            if data['origin']['url']:
                artwork.sameAs = [URIRef(data['origin']['url'])]

        p.subjectOf = subjectOf
        page.mainEntity = p
        p.mainEntityOfPage = page

    ##################################
    # Meta included in separate file #
    ##################################

    ds.bind('owl', OWL)
    ds.bind('dcterms', dcterms)
    ds.bind('create', create)
    ds.bind('schema', schema)
    ds.bind('sem', sem)
    ds.bind('void', void)
    ds.bind('foaf', foaf)

    ds.serialize(target, format='trig')

    with open('data/persondata.json', 'w') as outfile:
        json.dump(persondata, outfile)


if __name__ == "__main__":

    DATA = 'data/data.json'
    TARGET = 'data/schrijverskabinet.trig'

    if os.path.exists(DATA):
        main(loadData=DATA, target=TARGET)
    else:
        main(loadData=None, target=TARGET)
