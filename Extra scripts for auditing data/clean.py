#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import pprint
import re
import codecs
import json

"""
This is the main cleaning process file.
"""

"""
The transformed data should have a shape like the following:

{
"id": "2406124091",
"type: "node",
"visible":"true",
"created": {
          "version":"2",
          "changeset":"17206049",
          "timestamp":"2013-08-03T16:43:42Z",
          "user":"linuxUser16",
          "uid":"1219059"
        },
"pos": [41.9757030, -87.6921867],
"address": {
          "housenumber": "5157",
          "postcode": "60625",
          "street": "North Lincoln Ave"
        },
"amenity": "restaurant",
"cuisine": "mexican",
"name": "La Cabana De Don Luis",
"phone": "1 (773)-271-5176"
}


Plan:
- Process only ways and nodes
- audit and clean all city names
- audit postal codes, ignore any postal code that is not in the gold list (gold list is acquired from these links:
[http://en.wikipedia.org/wiki/List_of_postal_codes_in_Egypt, http://www.codemasr.com/, http://www.egypt-cairo.com/egypt_postal_code.html,
http://find-postalcode.com/%D9%85%D8%B5%D8%B1]
- all attributes of "node" and "way" should be turned into regular key/value pairs, except:
    - attributes in the CREATED array should be added under a key "created"
    - attributes for latitude and longitude should be added to a "pos" array,
      for use in geospacial indexing. Make sure the values inside "pos" array are floats
      and not strings. 
- if second level tag "k" value contains problematic characters, it should be ignored
- if second level tag "k" value starts with "addr:", it should be added to a dictionary "address"
- if second level tag "k" value does not start with "addr:", but contains ":", you can process it
  same as any other tag.
- if second level tag "k" starts with ("name:ar" or "name:en", ... etc.) should be added under a sub dictionary "alt_names"
  for alternative names, either arabic (ar) or german (de) or russian (ru)
- if there is a second ":" that separates the type/direction of a street,
  the tag should be ignored, for example:

<tag k="addr:housenumber" v="5158"/>
<tag k="addr:street" v="North Lincoln Avenue"/>
<tag k="addr:street:name" v="Lincoln"/>
<tag k="addr:street:prefix" v="North"/>
<tag k="addr:street:type" v="Avenue"/>
<tag k="amenity" v="pharmacy"/>

  should be turned into:

{...
"address": {
    "housenumber": 5158,
    "street": "North Lincoln Avenue"
}
"amenity": "pharmacy",
...
}

- for "way" specifically:

  <nd ref="305896090"/>
  <nd ref="1719825889"/>

should be turned into
"node_refs": ["305896090", "1719825889"]
"""

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
names_re = re.compile(r'name:(ar|en|de|ru)')

CREATED = ["version", "changeset", "timestamp", "user", "uid"]
OSMFILE = 'cairo_egypt.osm'

name_mapping = {
    "name:ar": "arabic",
    "name:en": "english",
    "name:ru": "russian",
    "name:de": "german"
}

#a list of expected city names
EXPECTED = ['Cairo', 'New Cairo', 'Giza', 'Orabi City']

#A map from an arabic city name to the corresponding english name
updated_city_names = {
    u"مدينة 6 أكتوبر - الجيزة": "6th Of October City",
    u"العباسية القاهرة": "Al - Abbasia",
    "6th of October": "6th Of October City",
    u"قليوب المحطة": "Qaliob",
    u"هرم": "Al - Haram",
    u"القاهرة": "Cairo",
    "cairo": "Cairo",
    "Cairo Governorate": "Cairo",
    "Al Manteqah Al Oula CAIRO": "Cairo",
    "Maadi, Cairo": "Maadi",
    u"مدينة 6 أكتوبر - القاهرة - مصر": "6th Of October City",
    "6 october": "6th Of October City",
    u"مدينة 6 أكتوبر": "6th Of October City",
    "new cairo": "New Cairo",
    u"مدينة 6 أكتوبر الحى المتميز داخل جامعة مصر للعلوم والتكنولوجيا": "6th Of October City",
    u"قويسنا": "Quweisna",
    "Gizeh": "Giza",
    u"حى النسايم": "Al - Nasaim District",
    u"الجيزة": "Giza",
    u"مدينة العبور": "Al - Obour City",
    u"مدينة نصر القاهرة": "Nasr City",
    "giza": "Giza",
    u"مدينة الشروق": "Al - Shrouk City",
    "orabi city": "Orabi City"
}


#Gold list of postal codes
postal_codes = {
    "Cairo": [i for i in xrange(11311, 11689)],
    "Al - Abbasia": [11381],
    "6th Of October City": [12573,
                            12563,
                            12564,
                            12566,
                            12568,
                            12575,
                            12582,
                            12585,
                            12586],
    "Giza": [12655,
             12511,
             12521,
             12611,
             12652,
             12651,
             12516,
             12654,
             12513,
             12514,
             12515],
    "Al - Haram": [12557, 12555, 12944, 12518, 12561, 12556, 12111]
}

def update_city_name(city_name):
    if city_name not in EXPECTED:
        return updated_city_names[city_name]
    return city_name


def shape_element(element):
    node = {}

    if element.tag == "node" or element.tag == "way":

        # lon, lat
        pos = [0.0, 0.0]

        # created and address sub dictionaries
        created = {}
        address = {}

        name = {}
        node["type"] = element.tag

        #holds a better city name (converted from arabic to english)
        better_name = ""

        #clean attributes
        for attrib in element.attrib:
            value = element.attrib[attrib]

            if attrib in CREATED:
                created[attrib] = value
            elif attrib == "lon":
                pos[1] = float(value)
            elif attrib == "lat":
                pos[0] = float(value)
            else:
                node[attrib] = value

        #clean tags
        for tag in element.iter('tag'):
            key = tag.attrib['k']
            value = tag.attrib['v']
            colons = key.count(':')
            colon_index = key.find(':')

            #a key of "wikipedia" probably contains some garbage values
            if key == "wikipedia":
                continue

            elif key.startswith("alt_name:"):
                continue

            elif key.startswith("name:"):
                if names_re.match(key):
                    m = names_re.match(key).group()
                    name[name_mapping[m]] = value

            elif problemchars.search(key):
                continue

            elif colons == 1 and key.startswith("addr:"):
                addr_key = key[colon_index+1:]

                #update city name if necessary

                if addr_key == "city":
                    better_name = update_city_name(value)
                    address[addr_key] = better_name

                elif addr_key == "postcode":

                    #all of egypt postal codes are 5 digit numbers
                    if len(value) == 5:
                        if better_name != "":
                            if int(value) in postal_codes[better_name]:
                                address[addr_key] = value
                #there's one faulty entry of addr:housenumber "<tag k="addr:housenumber" v="02.35699066 - 02.35710008"/>"
                if key == "addr:housenumber" and value.find('.') != -1:
                    continue

            #other key value pairs
            elif colons <= 1:
                node[key] = value

        #special cleaning for refs if the tag is way
        if element.tag == "way":
            refs = []
            for tag in element.iter('nd'):
                refs.append(tag.attrib["ref"])
            node["node_refs"] = refs

        node["created"] = created
        if address != {}:
            node["address"] = address
        node["pos"] = pos

        if name != {}:
            node["other_names"] = name
        return node
    else:
        return None


def process_map(file_in, pretty=False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el)+"\n")
    return data


def test():
    # NOTE: if you are running this code on your computer, with a larger dataset, 
    # call the process_map procedure with pretty=False. The pretty=True option adds 
    # additional spaces to the output, making it significantly larger.
    process_map(OSMFILE)
    #pprint.pprint(data)


if __name__ == "__main__":
    test()