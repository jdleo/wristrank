#!/usr/bin/env python3
"""WristRank bulk catalog builder.

Base = the curated catalog already in ~/workspace/wristrank/data/watches.json.
Adds ref-level entries from the 284K-listing Chrono24 dataset (yotam.csv):
group listings by (brand, ref), keep refs with >=25 listings, price = the ref's
own median, photo = best-scoring image-search result, downloaded + verified.
Resumable: progress in bulk_progress.jsonl, existing images are cache hits.
"""
import csv, re, json, os, sys, subprocess, tempfile, threading, collections, statistics
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

random_note = "deterministic: candidates sorted by listing count desc"
DATA = os.path.expanduser('~/workspace/wristrank-data')
APP = os.path.expanduser('~/workspace/wristrank')
OUTDIR = os.path.join(APP, 'public', 'watches')
PROGRESS = os.path.join(DATA, 'bulk_progress.jsonl')

LADIES = re.compile(r'ladies|\bwomen\b|\blady\b|lady-|lukia|femme|damen|princess|\bgirl\b', re.I)
BAD_DOMAINS = ('watchfinder', 'watchbase', 'chrono24.com', 'amazon.', 'walmart', 'ebay.')
GOOD_DOMAINS = ('everywatch', 'watchclub', 'bobswatches', 'europeanwatch', 'hodinkee',
                'crownandcaliber', 'thewatchpages', 'watchcharts', 'jomashop', 'bernardwatch')

def parse_price(s):
    if not s: return None
    m = re.sub(r'[^0-9.]', '', s)
    try:
        v = float(m)
        return v if 30 <= v <= 2_000_000 else None
    except Exception:
        return None

def tier_of(p): return 1 if p < 500 else 2 if p < 2000 else 3 if p < 6000 else 4 if p < 15000 else 5

def famkey(model):
    toks = [t for t in re.split(r'[^A-Za-z]+', model or '') if len(t) > 1]
    return ' '.join(toks[:2]).lower()

def norm_ref(r): return re.sub(r'[^A-Z0-9]', '', (r or '').upper())

def slugify(s):
    return (re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:56] or 'watch')

# ---------- base catalog ----------
base = json.load(open(os.path.join(APP, 'data', 'watches.json')))
base_refs = {norm_ref(w['ref']) for w in base if w.get('ref')}
base_ids = {w['id'] for w in base}
counts = collections.Counter(w['tier'] for w in base)
print('base:', len(base), dict(sorted(counts.items())))

# ---------- candidates from the CSV ----------
groups = {}
with open(os.path.join(DATA, 'yotam.csv'), encoding='utf-8', errors='replace') as f:
    for r in csv.DictReader(f):
        if r.get('sex') == "Women's watch": continue
        p = parse_price(r.get('price'))
        if p is None: continue
        brand = (r.get('brand') or '').strip()
        ref = (r.get('ref') or '').strip()
        model = (r.get('model') or '').strip()
        if not brand or not ref or ref in ('None', '-'): continue
        if len(ref) < 3 or not any(c.isdigit() for c in ref): continue
        g = groups.setdefault((brand, ref), {'prices': [], 'models': collections.Counter()})
        g['prices'].append(p)
        if model: g['models'][model] += 1

TARGET = {1: 80, 2: 230, 3: 360, 4: 260, 5: 160}
cands = []
for (brand, ref), g in groups.items():
    n = len(g['prices'])
    if n < 8: continue
    med = int(statistics.median(g['prices']))
    sample = g['models'].most_common(1)[0][0] if g['models'] else ''
    if LADIES.search(sample): continue
    if norm_ref(ref) in base_refs: continue
    cands.append({'brand': brand, 'ref': ref, 'n': n, 'price': med,
                  'tier': tier_of(med), 'model': sample, 'fam': famkey(sample)})
cands.sort(key=lambda c: -c['n'])
print('candidates:', len(cands))

brand_add = collections.Counter()
fam_add = collections.Counter()
selected = []
for c in cands:
    if counts[c['tier']] >= TARGET[c['tier']]: continue
    if brand_add[c['brand']] >= 140: continue
    if fam_add[(c['brand'], c['fam'])] >= 8: continue
    selected.append(c)
    counts[c['tier']] += 1
    brand_add[c['brand']] += 1
    fam_add[(c['brand'], c['fam'])] += 1
print('selected:', len(selected), 'projected tiers:', dict(sorted(counts.items())))

# family-level pass: fills tiers the ref pass could not (esp. T1/T2)
fam_groups = {}
with open(os.path.join(DATA, 'yotam.csv'), encoding='utf-8', errors='replace') as f:
    for r in csv.DictReader(f):
        if r.get('sex') == "Women's watch": continue
        p = parse_price(r.get('price'))
        if p is None: continue
        brand = (r.get('brand') or '').strip()
        model = (r.get('model') or '').strip()
        if not brand or not model: continue
        fk = famkey(model)
        if not fk: continue
        g = fam_groups.setdefault((brand, fk), {'prices': [], 'models': collections.Counter()})
        g['prices'].append(p); g['models'][model] += 1
fam_cands = []
for (brand, fk), g in fam_groups.items():
    if len(g["prices"]) < 80: continue
    med = int(statistics.median(g['prices']))
    sample = g['models'].most_common(1)[0][0]
    if LADIES.search(sample) or LADIES.search(fk): continue
    fam_cands.append({'brand': brand, 'ref': '', 'n': len(g['prices']), 'price': med,
                      'tier': tier_of(med), 'model': sample, 'fam': fk, 'family_entry': True})
fam_cands.sort(key=lambda c: -c['n'])
fam_brand_add = collections.Counter()
for c in fam_cands:
    if counts[c['tier']] >= TARGET[c['tier']]: continue
    if fam_brand_add[c["brand"]] >= 40: continue
    if any(s['brand'] == c['brand'] and s['fam'] == c['fam'] and s.get('family_entry') for s in selected): continue
    selected.append(c); counts[c['tier']] += 1; fam_brand_add[c['brand']] += 1
print('after family pass:', len(selected), 'projected tiers:', dict(sorted(counts.items())))
if os.environ.get('DRY'):
    import collections as _c
    print('bulk by brand:', dict(_c.Counter(c['brand'] for c in selected).most_common()))
    for c in selected[:5]: print('  sample:', c)
    sys.exit(0)

# ---------- image hunt ----------
done = {}
if os.path.exists(PROGRESS):
    for line in open(PROGRESS):
        try:
            d = json.loads(line)
            done[d['key']] = d
        except Exception: pass
lock = threading.Lock()

def score_result(res, c):
    hay = ((res.get('title') or '') + ' ' + (res.get('page_url') or '') + ' ' + (res.get('media_url') or '')).upper()
    hay_norm = re.sub(r'[^A-Z0-9]', '', hay)
    s = 0
    if norm_ref(c['ref']) and norm_ref(c['ref']) in hay_norm: s += 5
    if c['brand'].split()[0].upper() in hay: s += 2
    for tok in c['fam'].split():
        if tok.upper() in hay: s += 1
    url = res.get('media_url') or ''
    if any(g in url for g in GOOD_DOMAINS): s += 2
    if any(b in url for b in BAD_DOMAINS): s -= 6
    return s

def fetch_verify(url, out):
    if os.path.exists(out):
        try:
            with Image.open(out) as im:
                if min(im.size) >= 300: return True
        except Exception: pass
    fd, tmp = tempfile.mkstemp(suffix='.bin'); os.close(fd)
    try:
        r = subprocess.run(['curl', '-sL', '--max-time', '40', '-A',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36',
            '-o', tmp, url], capture_output=True, timeout=55)
        if r.returncode != 0 or os.path.getsize(tmp) < 8000: return False
        im = Image.open(tmp).convert('RGB')
        if min(im.size) < 300: return False
        im.thumbnail((800, 800))
        im.save(out, 'JPEG', quality=78)
        return True
    except Exception:
        return False
    finally:
        try: os.unlink(tmp)
        except Exception: pass

def hunt(c):
    key = c['brand'] + '|' + (c['ref'] or 'fam:' + c['fam'])
    wid = c['_wid']
    out = os.path.join(OUTDIR, wid + '.jpg')
    disp = (c['model'] or c['fam'].title())[:64]
    entry = {'id': wid, 'brand': c['brand'], 'model': disp, 'ref': c['ref'],
             'price': c['price'], 'tier': c['tier'], 'img': f'/watches/{wid}.jpg',
             'source': 'chrono24-family-median' if c.get('family_entry') else 'chrono24-ref-median'}
    if key in done and done[key].get('ok'):
        return entry if os.path.exists(out) else None
    if os.path.exists(out) and fetch_verify('', out):
        with lock:
            with open(PROGRESS, 'a') as f: f.write(json.dumps({'key': key, 'ok': True, 'cached': True}) + '\n')
        return entry
    q = f"{c['brand']} {disp} {c['ref']} watch"
    try:
        r = subprocess.run(['/opt/hatch/bin/image-search', q, '--max-results', '5'],
                           capture_output=True, text=True, timeout=60)
        results = json.loads(r.stdout).get('results', [])
    except Exception:
        results = []
    results = [x for x in results if x.get('media_url')]
    results.sort(key=lambda x: -score_result(x, c))
    ok = False
    for res in results[:3]:
        if fetch_verify(res['media_url'], out):
            ok = True; break
    with lock:
        with open(PROGRESS, 'a') as f: f.write(json.dumps({'key': key, 'ok': ok}) + '\n')
    return entry if ok else None

for c in selected:
    wid = slugify(c['brand'] + ' ' + (c['model'] or c['fam']) + ' ' + (c['ref'] or 'line'))
    b, i = wid, 2
    while wid in base_ids:
        wid = f'{b}-{i}'; i += 1
    base_ids.add(wid); c['_wid'] = wid

new_entries = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for i, entry in enumerate(ex.map(hunt, selected)):
        if entry: new_entries.append(entry)
        if (i + 1) % 50 == 0:
            print(f'  progress {i + 1}/{len(selected)} kept={len(new_entries)}', flush=True)

merged = base + new_entries
final_counts = collections.Counter(w['tier'] for w in merged)
print('FINAL:', len(merged), dict(sorted(final_counts.items())), 'brands:', len(set(w['brand'] for w in merged)))
json.dump(merged, open(os.path.join(APP, 'data', 'watches.json'), 'w'), indent=1)
print('wrote watches.json')
