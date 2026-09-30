W=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm
for f in B/3205309 B/rm04701 B/rm04501 A/3205309; do
 s=$(date +%s.%N); ogr2ogr -f FlatGeobuf -overwrite /work/out/fgb/$(echo $f|tr / _)_osm_links.fgb /work/out/$f.gpkg osm_links; e=$(date +%s.%N); echo "$f fgb_s=$(echo "$e-$s"|bc)"
done
ls -la /work/out/fgb
