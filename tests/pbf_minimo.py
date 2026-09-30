"""Helper: escreve PBFs minusculos com pyosmium."""
import osmium
from osmium.osm import mutable


def escreve(path, nos, ways):
    """nos: {id: (lon, lat)}; ways: {id: ([refs], {tags})}."""
    with osmium.SimpleWriter(str(path)) as w:
        for i, (lon, lat) in sorted(nos.items()):
            w.add_node(mutable.Node(id=i, location=(lon, lat)))
        for i, (refs, tags) in sorted(ways.items()):
            w.add_way(mutable.Way(id=i, nodes=refs, tags=tags))


def le(path):
    """(ids de nos, ids de ways) de um PBF."""
    n, w = set(), set()
    for o in osmium.FileProcessor(str(path), osmium.osm.NODE | osmium.osm.WAY):
        (n if o.is_node() else w).add(o.id)
    return n, w
