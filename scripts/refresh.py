"""Prepare monthly domestic export values from Statistics Canada's CIMT files."""
import argparse
from collections import defaultdict
from datetime import date
import csv
import gzip
import io
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/CIMT-CICM_Dom_Exp_{}.zip'
FIRST_YEAR = 2023
PRODUCTS = {
    'lobster': ('Lobster, live, fresh or chilled', '030632'),
    'frozen': ('Frozen lobster', '030612'),
    'prepared': ('Prepared or preserved lobster', '160530'),
    'softwood': ('Softwood lumber', '440711,440712,440713,440714,440719'),
    'wheat': ('Wheat and meslin', '1001'),
    'oil': ('Crude petroleum oils', '2709'),
    'fish': ('Fish, crustaceans and other aquatic invertebrates', '03'),
    'wood': ('Wood, wood articles and wood charcoal', '44'),
    'all': ('All merchandise', 'All HS chapters'),
}

def parse_archive(path, year, values, countries, provinces):
    months = set()
    with zipfile.ZipFile(path) as archive:
        def member(pattern):
            found = [n for n in archive.namelist() if re.search(pattern, n, re.I)]
            if len(found) != 1:
                raise ValueError(f'{year}: unexpected members matching {pattern}: {found}')
            return found[0]

        for pattern, names, code_slice in [('CtyDesc[.]txt$', countries, slice(0, 2)),
                                           ('ProvDesc[.]txt$', provinces, slice(3, 5))]:
            for line in archive.read(member(pattern)).decode('latin-1').splitlines():
                if len(line) > 105 and line[11:17] <= f'{year}12' and line[18:24] >= f'{year}01':
                    names[line[code_slice].strip()] = line[25:107].strip()
        for level, report in [(2, '020'), (6, '018')]:
            file = member(f'ODPFN{report}_[0-9]{{6}}N[.]csv$')
            level_months = set()
            with archive.open(file) as source:
                reader = csv.reader(io.TextIOWrapper(source, encoding='utf-8-sig'))
                header = next(reader)
                if header[1:4] != [f'HS{level}', 'Country/Pays', 'Province'] or header[5] != 'Value/Valeur':
                    raise ValueError(f'Unexpected CSV header in {file}')
                lookups = {key: item for item, (_, codes) in PRODUCTS.items()
                           for key in codes.split(',') if key.isdigit() and ((len(key) == 2) == (level == 2))}
                for month, code, country, province, state, value, *_ in reader:
                    if not month.startswith(str(year)) or not re.fullmatch(r'\d{4}(0[1-9]|1[012])', month):
                        raise ValueError(f'Unexpected month {month}')
                    level_months.add(month)
                    # Each US row is an individual state; the archive contains no US total rows.
                    product = lookups.get(code) or lookups.get(code[:4])
                    if level == 2 or product:
                        if not province or not country or value == '':
                            raise ValueError(f'Incomplete key or value in {file}')
                        key = (month, province, country)
                        if level == 2:
                            values[(*key, 'all')] += int(value)
                        if product:
                            values[(*key, product)] += int(value)
            if months and months != level_months:
                raise ValueError(f'Chapter and commodity files cover different months in {year}')
            months = level_months
    ordered = sorted(months)
    if not ordered or ordered != [f'{year}{m:02d}' for m in range(1, len(ordered) + 1)]:
        raise ValueError(f'Incomplete month sequence for {year}')
    return ordered

def refresh(folder, cache=None):
    folder = Path(folder)
    today = date.today()
    values = defaultdict(int)
    countries, provinces, months, sources = {}, {}, [], []
    for year in range(FIRST_YEAR, today.year + 1):
        url = URL.format(year)
        with tempfile.TemporaryDirectory() as tmp:
            archive = (Path(cache) if cache else Path(tmp)) / f'{year}.zip'
            if not archive.exists():
                try:
                    request = Request(url, headers={'User-Agent':'CoolCode/1.0 (+https://coolcode.ca/exportneighbours/)'})
                    with urlopen(request, timeout=120) as response, archive.open('wb') as f:
                        shutil.copyfileobj(response, f)
                except HTTPError as exc:
                    if year == today.year and exc.code == 404:
                        break
                    raise
            year_months = parse_archive(archive, year, values, countries, provinces)
            if year_months[-1][-2:] != '12' and year < today.year - 1:
                raise ValueError(f'Missing December {year}')
            months.extend(year_months)
            sources.append(url)
    if len(months) < 24 or len(provinces) < 13 or len(countries) < 150 or not values:
        raise ValueError('Source coverage failed validation')
    if any(int(b[:4])*12 + int(b[4:]) - int(a[:4])*12 - int(a[4:]) != 1 for a,b in zip(months,months[1:])):
        raise ValueError('Gap in monthly coverage')
    if any(p not in provinces or c not in countries for _, p, c, _ in values):
        raise ValueError('Unknown province or destination in source')
    existing = folder / 'edition.json'
    if existing.exists() and months[-1] < json.loads(existing.read_text())['months'][-1]:
        raise ValueError('Refusing to shorten the published date range')
    edition = dict(months=months, start=f'{months[0][:4]}-{months[0][4:]}', end=f'{months[-1][:4]}-{months[-1][4:]}',
                   retrieved=today.isoformat(), provinces=provinces, countries=countries, products=PRODUCTS,
                   sources=sources, count=len(values))
    folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        data = Path(tmp) / 'exports.csv.gz'
        with data.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf8', newline='') as text:
                writer = csv.writer(text, lineterminator='\n')
                writer.writerow(['month','province','destination','product','domestic_export_cad'])
                for k,v in sorted(values.items()):
                    writer.writerow([*k,v])
        data.replace(folder / data.name)
        meta = Path(tmp) / 'edition.json'
        meta.write_text(json.dumps(edition, sort_keys=True, indent=2, ensure_ascii=False)+'\n')
        meta.replace(existing)
    print(f'{len(values):,} monthly cells, {months[0]}–{months[-1]}.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, help='Directory containing optional YYYY.zip archives')
    args=parser.parse_args()
    refresh(ROOT / 'data', args.cache)
