#!/bin/bash
W=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm
for rid in 04701 04501 04901; do
  bb=$(python3 -c "import json;print(' '.join(str(x) for x in json.load(open('$W/malhas/bboxes.json'))['$rid']))")
  s=$(date +%s.%N)
  $W/scripts/qrun.sh ex$rid python3 /work/scripts/pyextract.py /work/pbf/sudeste-highway.osm.pbf /work/pbf/rm/rm$rid.osm.pbf $bb > $W/logs/B_${rid}_pyextract.txt 2>&1; echo "rc=$?" >> $W/logs/B_${rid}_pyextract.txt
  $W/scripts/qrun.sh cv$rid python3 /work/scripts/pbf2overpass.py /work/pbf/rm/rm$rid.osm.pbf /work/cache_B/osm_overpass_rm$rid.json > $W/logs/B_${rid}_conv.txt 2>&1; echo "rc=$?" >> $W/logs/B_${rid}_conv.txt
  $W/scripts/qrun.sh rb$rid python3 /work/scripts/run_path.py B $rid > $W/logs/B_${rid}_run.txt 2>&1; echo "rc=$?" >> $W/logs/B_${rid}_run.txt
done
echo FIM > $W/logs/chain_b.done
