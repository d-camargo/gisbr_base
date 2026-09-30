import json, sys, time, urllib.request, os
sys.path.insert(0, os.path.expanduser('~/projects/gisbr'))
from gisbr.core import regioes_metropolitanas as r
W = os.environ['W']
os.makedirs(W+'/malhas/mun', exist_ok=True)
for rid in ['04701','04501','04901']:
    for c in r.codes(rid):
        p = f"{W}/malhas/mun/{c}.geojson"
        if os.path.exists(p): continue
        u = f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{c}?formato=application/vnd.geo+json"
        for t in range(3):
            try:
                d = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent':'gisbr-medicao'}), timeout=60).read()
                open(p,'wb').write(d); break
            except Exception as e:
                print(c, 'erro', e); time.sleep(3)
print('ok')
