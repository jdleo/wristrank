import json, re, random, statistics, collections, urllib.request, urllib.parse, io, os, sys
from PIL import Image

random.seed(42)
HF = "https://huggingface.co/datasets/noxneural/watches_chrono24/resolve/main/"

# ---------- 1. image pool from noxneural ----------
d = json.load(open('/tmp/nox.json'))
sibs = [s['rfilename'] for s in d.get('siblings', []) if s['rfilename'].lower().endswith('.jpg')]
watches = {}
for s in sibs:
    p = s.split('/')
    if len(p) >= 3:
        watches.setdefault('/'.join(p[:2]), set()).add(p[-1])

def clean(s):
    s = s.replace('_', ' ').replace('  ', ' ').strip()
    s = s.replace('A  Lange', 'A. Lange').replace('H Moser', 'H. Moser').replace('F P Journe', 'F.P. Journe')
    s = s.replace('B R M', 'BRM').replace('Bell  Ross', 'Bell & Ross').replace('Eberhard  Co', 'Eberhard & Co.')
    s = s.replace('Baume  Mercier', 'Baume & Mercier').replace('Carl F  Bucherer', 'Carl F. Bucherer')
    s = s.replace('Dubey  Schaldenbrand', 'Dubey & Schaldenbrand').replace('Bedat  Co', 'Bedat & Co.')
    return s

BAD = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\u0400-\u04ff]|ladies|\bwomen\b|\blady\b|girl|princess|femme|damen|\bmiss\b|queen|mother of pearl ladies', re.I)
FASHION = {'Gucci','Chanel','Dior','Fendi','Armani','Hugo Boss','Burberry','Guess','Diesel','Fossil','Ice Watch','Dolce  Gabbana','Gant','Esprit','Festina','Breil','Apple','Garmin','Daniel Roth'}
SMART = re.compile(r'smartwatch|apple watch|garmin|fenix|forerunner|venu|epix', re.I)

pool = []
for w, imgs in watches.items():
    if 'image_1.jpg' not in imgs: continue
    brand_dir, name = w.split('/', 1)
    brand, model = clean(brand_dir), clean(name)
    if BAD.search(model) or brand in FASHION or SMART.search(model): continue
    # model display: strip leading duplicate brand name
    disp = model
    if disp.lower().startswith(brand.lower()):
        disp = disp[len(brand):].strip(' -_') or disp
    if len(disp) < 3: disp = model
    pool.append({'brand': brand, 'model': disp[:64], 'path': w + '/image_1.jpg'})
print('core pool:', len(pool))

# ---------- 2. marquee reference roster ----------
ROSTER = [
 # brand, display model, ref, price USD, tier, image: ('chrono', brand, [model keywords]) or ('hf', dirbrand, [name keywords])
 ('Rolex','Submariner Date','124060',17501,5,('chrono','Rolex','submariner date')),
 ('Rolex','Submariner No Date','124060',13750,4,('chrono','Rolex','submariner no')),
 ('Rolex','GMT-Master II','126710BLRO',20765,5,('chrono','Rolex','gmt master')),
 ('Rolex','Daytona','116500LN',42886,5,('chrono','Rolex','daytona')),
 ('Rolex','Datejust 36','126234',12500,4,('chrono','Rolex','datejust')),
 ('Rolex','Oyster Perpetual 41','124300',7451,4,('chrono','Rolex','oyster perpetual')),
 ('Rolex','Explorer','124270',9027,4,('chrono','Rolex','explorer')),
 ('Rolex','Explorer II','226570',11174,4,('chrono','Rolex','explorer ii')),
 ('Rolex','Day-Date 40','228238',46000,5,('chrono','Rolex','day date')),
 ('Rolex','Sea-Dweller','126600',15995,5,('chrono','Rolex','sea dweller')),
 ('Rolex','Yacht-Master 40','126622',18275,5,('chrono','Rolex','yacht master')),
 ('Rolex','Air-King','126900',6450,4,('chrono','Rolex','air king')),
 ('Rolex','Milgauss','116400GV',12597,4,('chrono','Rolex','milgauss')),
 ('Rolex','Sky-Dweller','326934',27039,5,('chrono','Rolex','sky dweller')),
 ('Rolex','Cellini Moonphase','50535',4745,3,('chrono','Rolex','cellini')),
 ('Omega','Speedmaster Moonwatch Professional','310.30.42.50.01.001',8494,4,('chrono','Omega','speedmaster professional')),
 ('Omega','Seamaster Diver 300M','210.30.42.20.03.001',5499,3,('chrono','Omega','seamaster diver')),
 ('Omega','Seamaster Aqua Terra','220.10.41.21.03.004',5737,3,('chrono','Omega','seamaster aqua')),
 ('Omega','Seamaster Planet Ocean','215.30.44.21.01.001',6613,4,('chrono','Omega','seamaster planet')),
 ('Omega','Speedmaster Racing','329.30.44.51.01.001',5858,3,('chrono','Omega','speedmaster racing')),
 ('Omega','De Ville Prestige','424.10.40.20.02.001',4370,3,('chrono','Omega','de ville')),
 ('Omega','Constellation','131.10.39.20.02.001',3317,3,('chrono','Omega','constellation')),
 ('Omega','Seamaster Vintage','165.024',2056,3,('chrono','Omega','seamaster')),
 ('Omega','Geneve Vintage','166.041',1043,2,('chrono','Omega','gen ve')),
 ('Patek Philippe','Nautilus','5711/1A-010',139702,5,('chrono','Patek Philippe','nautilus')),
 ('Patek Philippe','Aquanaut','5167A-001',93000,5,('chrono','Patek Philippe','aquanaut')),
 ('Patek Philippe','Calatrava','5196J-001',23435,5,('chrono','Patek Philippe','calatrava')),
 ('Patek Philippe','Annual Calendar','5146J-001',59500,5,('chrono','Patek Philippe','annual calendar')),
 ('Patek Philippe','Perpetual Calendar','5320G-001',101390,5,('chrono','Patek Philippe','perpetual calendar')),
 ('Patek Philippe','World Time','5230G-001',66250,5,('chrono','Patek Philippe','world time')),
 ('Audemars Piguet','Royal Oak Selfwinding','15510ST.OO.1320ST.01',53913,5,('hf','Audemars Piguet',['royal oak','selfwinding'])),
 ('Audemars Piguet','Royal Oak Offshore Chronograph','26470ST.OO.A027CA.01',43000,5,('hf','Audemars Piguet',['royal oak offshore'])),
 ('Audemars Piguet','Code 11.59 Selfwinding','15210CR.OO.A002CR.01',39000,5,('chrono','Audemars Piguet','code')),
 ('Vacheron Constantin','Overseas Selfwinding','4500V/110A-B128',31350,5,('chrono','Vacheron Constantin','overseas')),
 ('Vacheron Constantin','Patrimony','81180/000G-9298',17252,5,('chrono','Vacheron Constantin','patrimony')),
 ('Vacheron Constantin','Historiques American 1921','82035/000G-B735',19154,5,('chrono','Vacheron Constantin','historiques')),
 ('A. Lange & Söhne','Lange 1','191.032',42659,5,('hf','A_ Lange _ Söhne',['lange 1'])),
 ('A. Lange & Söhne','Saxonia Thin','201.027',24000,5,('hf','A_ Lange _ Söhne',['saxonia'])),
 ('Tudor','Black Bay Fifty-Eight','M79030N-0001',4140,3,('chrono','Tudor','black bay')),
 ('Tudor','Pelagos','M25600TN-0001',4850,3,('chrono','Tudor','pelagos')),
 ('Tudor','Black Bay GMT','M79830RB-0001',4400,3,('chrono','Tudor','black bay')),
 ('Tudor','Royal','M28600-0005',2565,3,('chrono','Tudor','royal')),
 ('Cartier','Tank Must','WSTA0041',4290,3,('hf','Cartier',['tank'])),
 ('Cartier','Santos de Cartier','WSSA0018',7844,4,('chrono','Cartier','santos')),
 ('Cartier','Ballon Bleu','WSBB0025',7556,4,('chrono','Cartier','ballon bleu')),
 ('Cartier','Pasha de Cartier','WSPA0009',3800,3,('chrono','Cartier','pasha')),
 ('IWC','Pilot Chronograph 41','IW388101',8000,4,('hf','IWC',['pilot','chronograph'])),
 ('IWC','Big Pilot 43','IW329301',11396,4,('chrono','IWC','big pilot')),
 ('IWC','Portugieser Chronograph','IW3716',8400,4,('chrono','IWC','portuguese chronograph')),
 ('IWC','Portofino Automatic','IW356501',5174,3,('chrono','IWC','portofino automatic')),
 ('Breitling','Navitimer B01 Chronograph','AB0138',8465,4,('hf','Breitling',['navitimer'])),
 ('Breitling','Superocean Heritage','AB2010',5060,3,('chrono','Breitling','superocean heritage')),
 ('Breitling','Chronomat B01','AB0134',6500,4,('chrono','Breitling','chronomat')),
 ('Breitling','Superocean Automatic','A17376',4446,3,('chrono','Breitling','superocean')),
 ('Breitling','Avenger Automatic','A17328',4300,3,('chrono','Breitling','avenger')),
 ('TAG Heuer','Carrera Chronograph','CBN2A1A',4799,3,('chrono','TAG Heuer','carrera')),
 ('TAG Heuer','Aquaracer Professional','WBP201A',2455,3,('chrono','TAG Heuer','aquaracer')),
 ('TAG Heuer','Monaco','CBL2111',6460,4,('chrono','TAG Heuer','monaco')),
 ('TAG Heuer','Formula 1 Quartz','WAZ1110',1590,2,('chrono','TAG Heuer','formula quartz')),
 ('TAG Heuer','Carrera Calibre 16','CV201AR',3048,3,('chrono','TAG Heuer','carrera calibre')),
 ('Panerai','Luminor Marina','PAM01312',6576,4,('chrono','Panerai','luminor marina')),
 ('Panerai','Luminor Submersible','PAM01229',11200,4,('chrono','Panerai','luminor submersible')),
 ('Panerai','Radiomir','PAM00992',7845,4,('chrono','Panerai','radiomir days')),
 ('Jaeger-LeCoultre','Reverso Classic','Q2548440',9900,4,('hf','Jaeger-LeCoultre',['reverso'])),
 ('Jaeger-LeCoultre','Master Ultra Thin Moon','Q1368420',12500,4,('hf','Jaeger-LeCoultre',['master','ultra thin'])),
 ('Jaeger-LeCoultre','Polaris Automatic','Q9008471',8200,4,('hf','Jaeger-LeCoultre',['polaris'])),
 ('Zenith','Chronomaster El Primero','03.3100.3600',7152,4,('chrono','Zenith','el primero')),
 ('Zenith','Defy Skyline','03.9300.3620',8097,4,('chrono','Zenith','defy')),
 ('Hublot','Classic Fusion Titanium','542.NX.1171.LR',10685,4,('hf','Hublot',['classic fusion'])),
 ('Hublot','Big Bang Unico','441.NX.1171.RX',18978,5,('hf','Hublot',['big bang'])),
 ('Hublot','Spirit of Big Bang','601.NX.0173.LR',24999,5,('chrono','Hublot','spirit of')),
 ('Grand Seiko','Snowflake','SBGA211',6600,4,('hf','Grand Seiko',['snowflake'])),
 ('Grand Seiko','Heritage Hi-Beat','SBGH271',6100,4,('hf','Grand Seiko',['hi-beat'])),
 ('Grand Seiko','Evolution 9','SLGA007',9100,4,('hf','Grand Seiko',['evolution'])),
 ('Longines','HydroConquest','L3.781.4',1742,2,('chrono','Longines','hydroconquest')),
 ('Longines','Conquest','L3.830.4',1183,2,('chrono','Longines','conquest')),
 ('Longines','Master Collection','L2.893.4',2453,3,('chrono','Longines','master collection')),
 ('Longines','Spirit','L3.810.4',2715,3,('chrono','Longines','spirit')),
 ('Longines','Flagship Heritage','L4.795.4',1505,2,('chrono','Longines','flagship')),
 ('Oris','Aquis Date','01 733 7730 4135',2113,3,('chrono','Oris','aquis date')),
 ('Oris','Big Crown Pointer Date','01 754 7741 3165',2179,3,('chrono','Oris','big crown')),
 ('Oris','Divers Sixty-Five','01 733 7707 4055',2067,3,('chrono','Oris','divers sixty')),
 ('Oris','Artelier Date','01 733 7670 4051',1508,2,('chrono','Oris','artelier date')),
 ('Seiko','Prospex Alpinist','SPB121',794,2,('chrono','Seiko','prospex')),
 ('Seiko','Presage Cocktail Time','SRPB41',667,2,('chrono','Seiko','presage')),
 ('Seiko','King Seiko','SPB291',989,2,('chrono','Seiko','king')),
 ('Seiko','Astron GPS Solar','SSH003',1685,2,('chrono','Seiko','astron gps')),
 ('Seiko','5 Sports','SRPD55',344,1,('chrono','Seiko','sports')),
 ('Seiko','Chronograph SSB','SSB031',413,1,('chrono','Seiko','chronograph')),
 ('Seiko','Solar Chronograph','SSC081',236,1,('chrono','Seiko','solar')),
 ('Seiko','Premier Kinetic','SRN045',469,1,('chrono','Seiko','premier')),
 ('Sinn','556 I','556.010',1650,2,('chrono','Sinn','556')),
 ('Sinn','104 St Sa','104.010',1790,2,('chrono','Sinn','104')),
 ('Richard Mille','RM 011 Flyback Chronograph','RM011',263410,5,('chrono','Richard Mille','rm')),
]
print('roster:', len(ROSTER))

# ---------- 3. (image index removed; roster images come from the hunt) ----------

# ---------- 4. image fetch + verify ----------
import subprocess, tempfile
def fetch_img(url, out):
    if os.path.exists(out):
        try:
            with Image.open(out) as im:
                if min(im.size) >= 300: return im.size
        except Exception: pass
    tmp = None
    try:
        for attempt in range(2):
            fd, tmp = tempfile.mkstemp(suffix='.bin'); os.close(fd)
            r = subprocess.run(['curl', '-sL', '--max-time', '45', '-A',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36',
                '-o', tmp, url], capture_output=True, timeout=70)
            if r.returncode != 0 or os.path.getsize(tmp) < 8000: continue
            im = Image.open(tmp).convert('RGB')
            w, h = im.size
            if min(w, h) < 300: return None
            im.thumbnail((900, 900))
            im.save(out, 'JPEG', quality=82)
            return im.size
        raise IOError('curl fetch failed')
    finally:
        if tmp:
            try: os.unlink(tmp)
            except Exception: pass

outdir = os.path.expanduser('~/workspace/wristrank/public/watches')
os.makedirs(outdir, exist_ok=True)
catalog, used_paths, failed = [], set(), []

def slugify(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:48] or 'watch'

def add_watch(brand, model, ref, price, tier, url, source):
    wid = slugify(brand + ' ' + model)
    base, i = wid, 2
    while wid in (w['id'] for w in catalog):
        wid = f'{base}-{i}'; i += 1
    out = os.path.join(outdir, wid + '.jpg')
    try:
        size = fetch_img(url, out)
    except Exception as e:
        failed.append((brand, model, str(e)[:60])); return False
    if not size:
        failed.append((brand, model, 'too small')); return False
    catalog.append({'id': wid, 'brand': brand, 'model': model, 'ref': ref, 'price': price,
                    'tier': tier, 'img': f'/watches/{wid}.jpg', 'source': source})
    return True

hunt = json.load(open(os.path.expanduser('~/workspace/wristrank-data/roster_images.json')))
for idx, (brand, model, ref, price, tier, spec) in enumerate(ROSTER):
    url = (hunt.get(str(idx)) or {}).get('url', '')
    if url and add_watch(brand, model, ref, price, tier, url, 'dealer-photo'):
        continue
    failed.append((brand, model, 'no image'))

print('roster placed:', len(catalog), 'failed:', len(failed))
for f in failed: print('  FAIL:', f)

# ---------- 5. curated fill (prices = computed Chrono24 medians) ----------
fill_spec = json.load(open(os.path.expanduser('~/workspace/wristrank-data/fill_spec.json')))
fill_imgs = json.load(open(os.path.expanduser('~/workspace/wristrank-data/fill_images.json')))
def _url(v):
    return v.get('url', '') if isinstance(v, dict) else (v or '')
for key in sorted(fill_spec, key=lambda k: int(k[1:])):
    e = fill_spec[key]
    url = _url(fill_imgs.get(key))
    if url and add_watch(e['brand'], e['model'], e['ref'], e['price'], e['tier'], url, 'dealer-photo'):
        continue
    failed.append((e['brand'], e['model'], 'fill no image'))

print('FINAL catalog:', len(catalog), 'tiers:', dict(sorted(collections.Counter(w['tier'] for w in catalog).items())))
print('brands:', len(set(w['brand'] for w in catalog)))
os.makedirs(os.path.expanduser('~/workspace/wristrank/data'), exist_ok=True)
json.dump(catalog, open(os.path.expanduser('~/workspace/wristrank/data/watches.json'), 'w'), indent=1)
print('total failures:', len(failed))
for f in failed: print('  FAIL:', f)
