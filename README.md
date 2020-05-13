# Schrijverskabinet RDF

| License     |                                                                                                                                                 |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Source code | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)                                     |
| Data        | [![License: CC BY-SA 40](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/40/) |

## Introduction
The Panpoëticon Batavûm is a collection of small portraits of Dutch poets (and writers in general). The collection was set up at the beginning of the eighteenth century by the painter Arnoud Halen (1673-1732). As a collection the Panpoëticon is no longer intact, but fortunately researchers at Radboud University have made a beautiful digital reconstruction, which can be seen at http://www.schrijverskabinet.nl/.

By modelling the data from the Schrijverskabinet as RDF, we can connect the entities that are included in the Schrijverskabinet to other relevant datasets that for instance include more detailed biographical information, such as [ECARTICO](http://www.vondel.humanities.uva.nl/ecartico/), [ONSTAGE](http://www.vondel.humanities.uva.nl/onstage/), and Wikidata. Also, a link to the Linked Open Data from the [Koninklijke Bibliotheek](http://data.bibliotheken.nl/) allows us to retrieve primary and secondary works for an author included in the Panpoëticon. We then can start asking questions such as 'To what extent were the authors of popular pieces in the Amsterdam Theatre included in the Panpoeticon?' and 'What was the geographical distribution of the poets included in the Panpoeticon?'. 

The data was first converted to be used in an Amsterdam Time Machine / UvA CREATE datasprint. More information is available here: https://uvacreate.gitlab.io/datasprint-ecartico-2020/

## Data

The data was extracted from http://www.schrijverskabinet.nl/, which can be cited as:
* Deinsen, L. van and T. van Strien (eds.), Het schrijverskabinet. Panpoëticon Batavûm, 2016,
<http://www.schrijverskabinet.nl/>.

```bibtex
@misc{vandeinsen_vanstrien2016, 
    title={Het schrijverskabinet. Panpoëticon Batavûm},
    howpublished={http://www.schrijverskabinet.nl/}, 
    author={Deinsen, Lieke van and Strien, Ton van},
    editor={Strien, Ton van},
    year={2016}
}
```

## Conversion to RDF

After scraping, the data is stored in a [JSON file](https://github.com/LvanWissen/schrijverskabinet-rdf/blob/master/data/data.json) and further processed into RDF. The conversion is done using a [script](https://github.com/LvanWissen/schrijverskabinet-rdf/blob/master/main.py) that follows the schema.org approach in modelling entities and relations. The data is returned as application/trig (see the [releases](https://github.com/LvanWissen/schrijverskabinet-rdf/releases) page for the latest stable/citable version).

## Cite

Please cite both the original website (above) and this repository if you are (re)using the data or refering to the publication.

** Zenodo **

