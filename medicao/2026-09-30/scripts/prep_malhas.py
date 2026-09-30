import json, os, sys
sys.path.insert(0,'/gisbr')
from qgis.core import QgsApplication, QgsGeometry, QgsJsonUtils, QgsFields
QgsApplication.setPrefixPath('/usr', True)
app = QgsApplication([], False); app.initQgis()
from gisbr.core import regioes_metropolitanas as r
out = {}
for rid in ['04701','04501','04901']:
    geoms = []
    for c in r.codes(rid):
        import gzip
        b = open(f'/work/malhas/mun/{c}.geojson','rb').read()
        d = (gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b).decode()
        for f in QgsJsonUtils.stringToFeatureList(d, QgsFields()):
            geoms.append(f.geometry())
    u = QgsGeometry.unaryUnion(geoms)
    bb = u.boundingBox()
    out[rid] = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
    open(f'/work/malhas/rm{rid}.geojson','w').write(json.dumps({"type":"Feature","properties":{"rm":rid,"n_mun":len(geoms)},"geometry":json.loads(u.asJson(7))}))
    print(rid, len(geoms), out[rid], u.isGeosValid())
json.dump(out, open('/work/malhas/bboxes.json','w'))
