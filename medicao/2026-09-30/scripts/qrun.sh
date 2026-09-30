#!/bin/bash
# uso: qrun.sh NOME_CONTAINER cmd...
W=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm
n=$1; shift
exec podman run --rm --name $n --memory=3g --memory-swap=3g -v $HOME/projects/gisbr:/gisbr:ro -v $W:/work -e PYTHONPATH=/gisbr:/work/pylibs -e QT_QPA_PLATFORM=offscreen -e W=/work docker.io/qgis/qgis:3.44 "$@"
