import gzip, glob
from lxml import etree
from collections import namedtuple

# Namedtuple to represent tokens.
Token = namedtuple('Token', ['token', 'POS', 'lemma', 'depid', 'dephead', 'deprel'])

def cowfiles(path='./'):
    "Wrapper for the glob module."
    return glob.glob(path+'*.xml.gz')

def split_element_text(element):
    """Helper function to make things readable. etree.tostring() returns byte representations,
    but you cannot use .split() on them. For that, you need to decode to utf-8.
    This function does just that, and returns the text as a list of lines."""
    return etree.tostring(element).decode('utf-8').split('\n')

def sentence_data_generator(element):
    "Generator that takes a sentence element and yields tokens."
    for line in split_element_text(element):
        if not line.startswith('<') and not line == '':
            data = line.split('\t')
            # Ugly hack because there are some elements with messed up data:
            if len(data) == 6:
                yield Token(*data)

def get_sentence_data(element):
    "Takes a sentence element and returns a list of tokens."
    return list(sentence_data_generator(element))

def get_full_sentence_data(element):
    structure = []
    tokens    = []
    for line in split_element_text(element):
        if line.startswith('<s') or line.startswith('</s'):
            continue
        elif line.startswith('</'):
            structure.append(line[2:-1] + '_close')
        elif line.startswith('<'):
            structure.append(line[1:-1] + '_open')
        elif not line == '':
            data = line.split('\t')
            # Ugly hack because there are some elements with messed up data:
            if len(data) == 6:
                structure.append(data[3])
                tokens.append(Token(*data))
    return (structure, tokens)

def clear_references(element):
    """
    Lower memory by clearing references to elements we won't need
    anymore. See also the answer at: http://stackoverflow.com/a/12161078/2899924
    """
    element.clear()
    for ancestor in element.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]

def sentence_generator(filename, gzipped=True, structure=False):
    """Returns metadata, optionally the sentence structure, and the sentence itself.
    Each sentence is represented as a list of Token objects. Tokens are named tuples,
    with the following values: ['token', 'POS', 'lemma', 'depid', 'dephead', 'deprel']
    
    Arguments
    ---------
    filename:  filename
    gzipped:   assumes the file is gzipped. Change to False for unpacked files
    structure: assumes we don't need information about sentence structure.
               change to True to get this info.
    """
    source = gzip.GzipFile(filename) if gzipped else filename
    parser = etree.iterparse(source, html=True, events=('start','end',), tag='s')
    # get_full_sentence_data() returns the structure and a list of tokens
    # get_sentence_data() returns a list of tokens
    data_func = get_full_sentence_data if structure else get_sentence_data
    for event, element in parser:
        if event == 'start':
            # element.attrib() returns a dictionary with metadata for the sentence.
            yield (element.attrib, data_func(element))
            opening_element = element
        elif event == 'end':
            clear_references(opening_element)
            clear_references(element)
    # Aggressively keep memory load down
    del parser


def separate(list_of_tokens):
    return list(zip(*list_of_tokens))

def sentences_for_dir(path='./', gzipped=True, structure=False):
    """Sentence generator for an entire corpus directory.
    
    Arguments
    ---------
    path    :  path to the COW files
    gzipped :  assumes the file is gzipped. Change to False for unpacked files
    structure: assumes we don't need information about sentence structure.
               change to True to get this info.
    """
    for filename in cowfiles(path):
        for metadata, data in sentence_generator(filename, gzipped, structure):
            yield metadata, data
