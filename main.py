"""
Pipeline that converts the data from http://www.schrijverskabinet.nl/ into RDF. 

Built upon an adapted version of RDFAlchemy for Python (3.7). Install with:

```bash
pip install git+https://github.com/LvanWissen/RDFAlchemy.git
```

Questions:
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
from rdflib import Dataset, ConjunctiveGraph, Graph, URIRef, Literal, XSD, Namespace, RDFS, BNode, OWL
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
personCounter = count(1)

nsArtwork = Namespace(
    "https://data.create.humanities.uva.nl/id/schrijverskabinet/artwork/")
artworkCounter = count(1)


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

    version = rdfSingle(schema.version)


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

    # urls = re.findall(r'(http:\/\/www\.schrijverskabinet\.nl\/portret\/.*?)"',
    #                   r.text)

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
    if 'portrait-no-image' in artdepiction or 'Vrouw01' in artdepiction:
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

    name = name.lower().replace(' ', '-')
    name = unidecode(name)

    name = "".join([i for i in name if i in 'abcdefghijklmnopqrstuvwxyz-'])

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
    dataset = ns.term('')

    g = rdfSubject.db = ds.graph(identifier=ns)

    try:
        with open('data/persondata.json') as infile:
            persondata = json.load(infile)
    except:
        persondata = dict()

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
            birthPlace = birthPlace.replace('ca.', '').replace('(?)',
                                                               '').strip()
        except:
            if birth.isdigit():
                birthYear = birth
                birthPlace = None
            else:
                birthPlace, birthYear = None, None
        try:
            deathPlace, deathYear = death.rsplit(' ', 1)
            deathPlace = deathPlace.replace('ca.', '').replace('(?)',
                                                               '').strip()
        except:
            if death.isdigit():
                deathYear = death
                deathPlace = None
            else:
                deathPlace, deathYear = None, None

        #############
        # Resources #
        #############

        subjectOf = []
        puri, persondata = person2uri(data['title'], persondata)
        p = Person(
            puri,
            name=[Literal(data['title'])],
            sameAs=sameAs,
            birthPlace=Place(BNode("".join([
                i for i in birthPlace.lower()
                if i in 'abcdefghijklmnopqrstuvwxyz'
            ])),
                             name=[birthPlace])
            if birthPlace and birthPlace.lower() != 'onbekend' else None,
            birthDate=Literal(birthYear, datatype=XSD.gYear, normalize=False)
            if birthYear else None,
            deathPlace=Place(BNode("".join([
                i for i in deathPlace.lower()
                if i in 'abcdefghijklmnopqrstuvwxyz'
            ])),
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

            if ', verbeterd door ' in name:
                painternames += name.split(', verbeterd door ')
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

            artwork = VisualArtwork(
                nsArtwork.term(str(next(artworkCounter))),
                artist=painters,
                about=p,
                name=[Literal(f"Portret van {data['title']}", lang='nl')],
                depiction=URIRef(data['artdepiction'])
                if data['artdepiction'] else None,
                temporal=Literal(data['date'], lang='nl'),
                publication=publicationEvent)
            subjectOf.append(artwork)

            if data['origin']['url']:
                artwork.sameAs = [URIRef(data['origin']['url'])]

        p.subjectOf = subjectOf
        page.mainEntity = p
        p.mainEntityOfPage = page

    ########
    # Meta #
    ########

    rdfSubject.db = ds

    description = """Schrijverskabinet.nl is ontwikkeld om op een toegankelijke manier de Nederlandse literaire cultuur van de vroegmoderne tijd voor het voetlicht te brengen. De website is ingericht rondom een achttiende-eeuwse verzameling auteursportretten: het Panpoëticon Batavûm. Naast een geschiedenis van deze collectie, presenteert schrijverskabinet.nl een overzicht van de dichters en dichteressen van wie het portret in de verzameling was opgenomen. Veel van de oorspronkelijke Pan-portretten zijn verloren gegaan of (vooralsnog) onvindbaar. In die gevallen is gekozen om de auteurs waar mogelijk te tonen aan de hand van gravures, schilderijen of prenten. In de focus op het Panpoëticon schuilt de beperking van dit project. Deze website presenteert geen overzicht van alle Nederlandse dichters en dichteressen uit de vroegmoderne tijd, maar bevat uitsluitend de auteurs die in het kabinet waren opgenomen.

Naast een overzicht van de dichters en dichteressen die in het Panpoëticon waren te vinden, biedt schrijverskabinet.nl een computervisualisatie van het verloren houten kabinet. Het gaat om een hypothetische reconstructie.

In de sectie ‘Uit de kast’ introduceren diverse specialisten veel van de auteurs. Deze sectie is geen afgesloten geheel, maar kan in de loop van de tijd verder groeien. De korte artikels streven geen uitputtend bio- of bibliografisch doel na. Ze zijn bedoeld om de (veelal vergeten) auteurs opnieuw onder de aandacht te brengen. Achter elke bijdrage wordt verwezen naar een of twee, zo mogelijk recente en online beschikbare, studies over de besproken auteur en/of (een aspect van) zijn of haar werk, die geschikt zijn voor een nadere kennismaking en een indruk geven van de huidige stand van het onderzoek. De meest voor de handliggende secundaire bronnen (literatuurgeschiedenissen, biografische woordenboeken, wikipagina’s) noemen we in principe niet, behalve als andere publicaties (nog) ontbreken. Alleen in het geval van enkele `groten’ (Vondel, Hooft, Huygens) wijken we van onze regel af: gezien de grote hoeveelheid vaak specialistische publicaties over deze auteurs beperken we ons daar tot het noemen van de meest gebruikte bronnenuitgaven. Bij alle auteurs biedt de link naar de dbnl toegang tot meer complete bibliografische informatie.

Schrijverskabinet.nl is in aanbouw. Mocht u ontbrekende portretten weten te vinden of een nog niet besproken auteur willen introduceren in een essay, neem dan contact op met Lieke van Deinsen (lieke.vandeinsen@kuleuven.be)."""

    contributors = "Sarah Adams, Peter Altena, Pieta van Beek, Frans Blom, Roland de Bonth, Lieke van Deinsen, Feike Dietz, Michiel van Duijnen, Martine van Elk, Johanna Ferket, Josephina de Fouw, Nina Geerdink, Arie-Jan Gelderblom, Lia van Gemert, Elly Groenenboom-Draai, Anna de Haas, Ton Harmsen, Kornee van der Haven, Patrick van ‘t Hof, Rick Honings, Dirk Imhof, Jeroen Jansen, Johan Koppenol, Inger Leemans, Ad Leerintveld, Henk Looijesteijn, Geert Mak, Hubert Meeus, Marijke Meijer Drees, Sven Molenaar, Alan Moss, Nelleke Moser, Ivo Nieuwenhuis, Jan Noordegraaf, Joris Oddens, Kasper van Ommen, Timothy De Paepe, Marrigje Paijmans, Karel Porteman, Sophie Reinders, Michiel Roscam Abbing, Gijsbert Rutten, Riet Schenkeveld-van der Dussen, Nicoline van der Sijs, Jasper van der Steen, René van Stipriaan, Ton van Strien, Els Stronks, Marijke Tolsma, Ans Veltman, Ruben E. Verwaal, Arnoud Visser, Jan Waszink"

    download = DataDownload(
        None,
        contentUrl=URIRef(
            "https://raw.githubusercontent.com/LvanWissen/schrijverskabinet-rdf/1.0/data/schrijverskabinet.trig"
        ),
        # name=Literal(),
        url=URIRef(
            "https://github.com/LvanWissen/schrijverskabinet-rdf/tree/1.0/data"
        ),
        encodingFormat="application/trig")

    date = Literal(datetime.datetime.now().strftime('%Y-%m-%d'),
                   datatype=XSD.datetime)

    contributors = contributors.split(', ')

    creators = ["Lieke van Deinsen", "Ton van Strien"]

    dataset = DatasetClass(
        ns.term(''),
        name=[
            Literal("Het Schrijverskabinet - Panpoëticon Batavûm", lang='nl')
        ],
        about=URIRef('http://www.wikidata.org/entity/Q17319132'),
        url=URIRef('http://www.schrijverskabinet.nl/'),
        description=[Literal(description, lang='nl')],
        descriptionSchema=[Literal(description, lang='nl')],
        creator=creators,
        publisher=[
            URIRef("https://leonvanwissen.nl/me"),
            URIRef("http://viaf.org/viaf/281741168")
        ],
        publisherSchema=[
            URIRef("https://leonvanwissen.nl/me"),
            URIRef("http://viaf.org/viaf/281741168")
        ],
        contributor=contributors,
        contributorSchema=contributors,
        source=URIRef('http://www.schrijverskabinet.nl/'),
        isBasedOn=URIRef('http://www.schrijverskabinet.nl/'),
        date=date,
        dateCreated=date,
        distribution=download,
        created=None,
        issued=None,
        modified=None,
        exampleResource=p,
        vocabulary=[
            URIRef("http://schema.org/"),
            URIRef("http://semanticweb.cs.vu.nl/2009/11/sem/"),
            URIRef("http://xmlns.com/foaf/0.1/")
        ],
        triples=sum(1 for i in ds.graph(identifier=ns).subjects()),
        version="1.0",
        licenseprop=URIRef("https://creativecommons.org/licenses/by-sa/4.0/"))

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
