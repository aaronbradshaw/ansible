# (c) 2013, Jan-Piet Mens <jpmens(at)gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: csvfile
    author: Jan-Piet Mens (@jpmens) <jpmens(at)gmail.com>
    version_added: "1.5"
    short_description: read data from a TSV or CSV file
    description:
      - The csvfile lookup reads the contents of a file in CSV (comma-separated value) format.
        The lookup looks for the row where the first column matches keyname, and returns the value in the second column, unless a different column is specified.
    options:
      col:
        description:  column to return (0 index).
        default: "1"
      default:
        description: what to return if the value is not found in the file.
        default: ''
      delimiter:
        description: field separator in the file, for a tab you can specify "TAB" or "t".
        default: TAB
      file:
        description: name of the CSV/TSV file to open.
        default: ansible.csv
      encoding:
        description: Encoding (character set) of the used CSV file.
        default: utf-8
        version_added: "2.1"
    notes:
      - The default is for TSV files (tab delimeted) not CSV (comma delimted) ... yes the name is misleading.
"""

EXAMPLES = """
- name:  Match 'Li' on the first column, return the second column (0 based index)
  debug: msg="The atomic number of Lithium is {{ lookup('csvfile', 'Li file=elements.csv delimiter=,') }}"

- name: msg="Match 'Li' on the first column, but return the 3rd column (columns start counting after the match)"
  debug: msg="The atomic mass of Lithium is {{ lookup('csvfile', 'Li file=elements.csv delimiter=, col=2') }}"
"""

RETURN = """
  _raw:
    description:
      - value(s) stored in file column
"""

import codecs
import csv
from collections import MutableSequence

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils._text import to_bytes, to_native, to_text


class CSVRecoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding='utf-8'):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class CSVReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        f = CSVRecoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [to_text(s) for s in row]

    def __iter__(self):
        return self


class LookupModule(LookupBase):

    def read_csv(self, filename, key, delimiter, encoding='utf-8', dflt=None, col=1):

        try:
            f = open(filename, 'r')
            creader = CSVReader(f, delimiter=to_bytes(delimiter), encoding=encoding)

            for row in creader:
                if row[0] == key:
                    return row[int(col)]
        except Exception as e:
            raise AnsibleError("csvfile: %s" % to_native(e))

        return dflt

    def run(self, terms, variables=None, **kwargs):

        ret = []

        for term in terms:
            params = term.split()
            key = params[0]

            paramvals = {
                'col': "1",          # column to return
                'default': None,
                'delimiter': "TAB",
                'file': 'ansible.csv',
                'encoding': 'utf-8',
            }

            # parameters specified?
            try:
                for param in params[1:]:
                    name, value = param.split('=')
                    assert(name in paramvals)
                    paramvals[name] = value
            except (ValueError, AssertionError) as e:
                raise AnsibleError(e)

            if paramvals['delimiter'] == 'TAB':
                paramvals['delimiter'] = "\t"

            lookupfile = self.find_file_in_search_path(variables, 'files', paramvals['file'])
            var = self.read_csv(lookupfile, key, paramvals['delimiter'], paramvals['encoding'], paramvals['default'], paramvals['col'])
            if var is not None:
                if isinstance(var, MutableSequence):
                    for v in var:
                        ret.append(v)
                else:
                    ret.append(var)
        return ret
