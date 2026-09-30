#!/bin/bash
# uso: step_b.sh RMID  -> extract + tags-filter (osmium container, 3g)
W=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm
rid=$1
bbox=$(python3 -c "import json;b=json.load(open('$W/malhas/bboxes.json'))['$rid'];print(','.join(str(x) for x in b))")
mkdir -p $W/pbf/rm
L=$W/logs/B_$rid.txt
echo "bbox=$bbox" > $L
PBF=sudeste-highway.osm.pbf  # DESVIO: prefiltrado (extract direto do Sudeste deu OOM em 3g)
podman run --rm --memory=3g --memory-swap=3g -v $W:/work --entrypoint sh iboates/osmium -c "
set -x
/usr/bin/time -v osmium extract -b $bbox --strategy complete_ways --overwrite -o /work/pbf/rm/rm$rid.extract.osm.pbf /work/pbf/$PBF 2>/work/logs/B_${rid}_extract.time; echo extract_rc=\$?
echo extract_cgroup_peak_bytes=\$(cat /sys/fs/cgroup/memory.peak)
/usr/bin/time -v osmium tags-filter --overwrite -o /work/pbf/rm/rm$rid.osm.pbf /work/pbf/rm/rm$rid.extract.osm.pbf w/highway 2>/work/logs/B_${rid}_filter.time; echo filter_rc=\$?
echo filter_cgroup_peak_bytes=\$(cat /sys/fs/cgroup/memory.peak)
" >> $L 2>&1
cat $L | grep -v '^+'
for s in extract filter; do echo "== $s"; egrep "Elapsed|Maximum resident|Exit status" $W/logs/B_${rid}_$s.time; done
ls -la $W/pbf/rm/
