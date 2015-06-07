"""
This file is used to audit postal codes. It prints out a list of city names and the associated postal codes with each city
"""
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import codecs

OSMFILE = "cairo_egypt.osm"


def audit_postal_codes(postal_codes, city_name, postcode):
    postal_codes[city_name].add(postcode)

def audit(osmfile):
    osm_file = codecs.open(osmfile, "r")
    postal_codes = defaultdict(set)
    cities = set()
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        city, code = None, None
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if tag.attrib['k'] == "addr:postcode":
                    code = tag.attrib['v'].lower()
                elif tag.attrib['k'] == "addr:city":
                    city = tag.attrib['v'].lower()
            if city and code:
                audit_postal_codes(postal_codes, city, code)

            if city:
                cities.add(city)

    return postal_codes, cities


def test():
    postcodes, city_names = audit(OSMFILE)

    print "\n-------------CITY NAMES------------------\n"
    for name in city_names:
        print name

    print "\n-------------POSTAL CODES-----------------\n"
    for code in postcodes:
        print code, ":"
        for value in postcodes[code]:
            print value


if __name__ == '__main__':
    test()
