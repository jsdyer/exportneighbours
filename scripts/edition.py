"""Build browser-sized product files and discovery metadata from the checked snapshot."""
import csv
import gzip
import json
import shutil
from collections import defaultdict
from pathlib import Path

LANDING = 'https://coolcode.ca/exportneighbours/'
LICENSE = 'https://www.statcan.gc.ca/en/reference/licence'
SOURCE = 'https://open.canada.ca/data/en/dataset/2909a648-5753-4924-878a-b069392d9cde'

def prepare(data, stage):
    meta = json.loads((data / 'edition.json').read_text())
    target = stage / 'data'
    target.mkdir()
    records = defaultdict(lambda: defaultdict(dict))
    count = 0
    with gzip.open(data / 'exports.csv.gz', 'rt', encoding='utf8') as f:
        for row in csv.DictReader(f):
            m,p,c,k,v = (row[key] for key in ['month','province','destination','product','domestic_export_cad'])
            if m not in meta['months'] or p not in meta['provinces'] or c not in meta['countries'] or k not in meta['products']:
                raise ValueError(f'Unrecognized snapshot key in {row}')
            dest = records[p,k][m]
            if c in dest:
                raise ValueError(f'Duplicate snapshot row {row}')
            dest[c] = int(v)
            count += 1
    if count != meta['count']:
        raise ValueError('Data and edition row counts differ')
    for p in meta['provinces']:
        for k in meta['products']:
            (target / f'{p}-{k}.json').write_text(json.dumps(records[p,k], separators=(',',':')))
    for name in ('edition.json','exports.csv.gz'):
        shutil.copyfile(data / name, target / name)
    return {
        '@context':'https://schema.org', '@type':'Dataset', 'name':'Export Neighbours monthly Canadian domestic merchandise exports',
        'url': LANDING, 'identifier': LANDING+'#monthly-exports',
        'description': 'Monthly Canadian customs-basis domestic export values in nominal CAD by province or territory of origin and destination. Includes all merchandise and eight selected Harmonized System product groupings. The archive starts in January 2023.',
        'creator': {'@type':'Organization','name':'CoolCode','url':'https://coolcode.ca/'},
        'isBasedOn': SOURCE, 'license': LICENSE, 'spatialCoverage':'Canada',
        'temporalCoverage': meta['start']+'/'+meta['end'], 'dateModified':meta['retrieved'],
        'variableMeasured':'Domestic merchandise export value (current Canadian dollars)',
        'distribution': {'@type':'DataDownload','contentUrl': LANDING+'data/exports.csv.gz','encodingFormat':'application/gzip','name':'Monthly domestic exports, gzip-compressed CSV'}
    }
