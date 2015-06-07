"""
This file is not necessary, i just used to see some info about the dataset
"""

import xml.etree.ElementTree as ET
import pprint
import re


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

tags_by_users = ['node', 'way', 'relation']


def key_type(element, keys):
    if element.tag == "tag":
        k = element.attrib["k"]
        if lower.match(k):
            keys["lower"] += 1
        elif lower_colon.match(k):
            keys["lower_colon"] += 1
        elif problemchars.search(k):
            keys["problemchars"] += 1
        else:
            keys["other"] += 1

    return keys


def get_user(element):
    if element.tag in tags_by_users:
        return element.attrib["uid"]


def count_tags(filename):
    tags = {}
    for event, elem in ET.iterparse(filename):
        if elem.tag in tags:
            tags[elem.tag] += 1
        else:
            tags[elem.tag] = 1

    return tags


def process_tag_types(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)

    return keys


def process_users(filename):
    users = set()
    for _, element in ET.iterparse(filename):
        user = get_user(element)
        if user is not None:
            users.add(user)

    return users


def main():
    filename = 'test.osm'
    users = process_users(filename)
    tags = count_tags(filename)
    tag_types = process_tag_types(filename)

    print "\n Unique users:", len(users)

    print "\n Top level tags:", tags

    print "\n Tag types:", tag_types


if __name__ == "__main__":
    main()


