import csv
import itertools
import os

from runrex.io import sqlai
from runrex.text.document import Document


def get_next_from_directory(directory, directories, version=None, filenames=None,
                            encoding='utf8'):
    if directory or directories:
        directories = directories or []
        if directory:
            directories.insert(0, directory)
        for directory in directories:
            if os.path.isdir(directory):
                yield from _get_next_from_directory(directory, encoding, filenames, version)
            else:  # is file (e.g., CSV)
                for doc_name, text in _get_next_from_file(directory, encoding):
                    yield doc_name, None, text


def _get_next_from_file(file, name_col='doc_id', text_col='text_col', encoding='utf8'):
    if file.endswith('.csv'):
        with open(file, encoding=encoding, newline='') as fh:
            for row in csv.DictReader(fh):
                yield row[name_col], row[text_col]
    else:
        raise ValueError(f'Unrecognized file type (expected CSV): {file}')


def _get_next_from_directory(directory, encoding, filenames, version):
    if version:
        corpus_dir = os.path.join(directory, version)
    else:
        corpus_dir = directory
    if filenames:  # only look for specified files
        for file in filenames:
            fp = os.path.join(corpus_dir, file)
            try:
                with open(fp, encoding=encoding) as fh:
                    text = fh.read()
            except FileNotFoundError:
                continue
            else:
                yield '.'.join(file.split('.')[:-1]) or file, None, text
    else:
        for entry in os.scandir(corpus_dir):
            if '.' in entry.name:
                doc_name = '.'.join(entry.name.split('.')[:-1])
            else:
                doc_name = entry.name
            with open(entry.path, encoding=encoding) as fh:
                text = fh.read()
            if not text:
                continue
            yield doc_name, None, text


def get_next_from_connections(*connections):
    for connection in connections:
        for doc_name, text in get_next_from_sql(**connection):
            yield doc_name, None, text


def get_next_from_sql(name=None, driver=None, server=None,
                      database=None, name_col=None, text_col=None, encoding='utf8'):
    """
    :param name_col:
    :param text_col:
    :param name: tablename (if connecting to database)
    :param driver: db driver  (if connecting to database)
    :param server: name of server (if connecting to database)
    :param database: name of database (if connecting to database)
    """
    if name and driver and server and database:
        eng = sqlai.get_engine(driver=driver, server=server, database=database)
        for doc_name, text in eng.execute(f'select {name_col}, {text_col} from {name}'):
            yield doc_name, text
    elif name and not driver and not server and not database:  # this is a directory
        yield from _get_next_from_file(name, name_col=name_col, text_col=text_col, encoding=encoding)


def get_next_from_corpus(directory=None, directories=None, version=None,
                         connections=None, skipper=None, start=0, end=None,
                         filenames=None, encoding='utf8', ssplit=None):
    """

    :param ssplit: sentence splitting function
    :param filenames:
    :param encoding:
    :param connections:
    :param directories: list of directories to look through
    :param skipper:
    :param directory: first to look through (for backwards compatibility)
    :param version: text|lemma|token
    :param start:
    :param end:
    :return: iterator yielding documents
    """
    i = -1
    for doc_name, path, text in itertools.chain(
            get_next_from_directory(directory, directories, version, filenames, encoding),
            get_next_from_connections(*connections or list())
    ):
        if skipper and doc_name in skipper:
            continue
        i += 1
        if i < start:
            continue
        elif end and i >= end:
            break
        if not text and not path:  # one of these required
            continue
        yield Document(doc_name, file=path, text=text, ssplit=ssplit)


class Skipper:

    def __init__(self, path=None, rebuild=False, ignore=False):
        self.fp = path
        self.fh = None
        self.rebuild = rebuild
        self.ignore = ignore
        self.skips = self._read_skips()

    def _read_skips(self):
        if self.fp and os.path.exists(self.fp) and not self.ignore:
            with open(self.fp) as fh:
                return {x.strip() for x in fh if x.strip()}
        return set()

    def add(self, doc_name):
        if doc_name not in self.skips:
            self.skips.add(doc_name)
            if self.fp:
                self.fh.write(doc_name + '\n')

    def __contains__(self, item):
        return item in self.skips

    def __enter__(self):
        if self.fp:
            self.fh = open(self.fp, 'w' if self.rebuild else 'a')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fp:
            self.fh.close()
