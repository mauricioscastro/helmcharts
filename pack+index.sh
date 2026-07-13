#!/bin/sh
ls | grep -v -e charts -e README -e index.yaml -e helmfiles -e pack+index | while read p; do 
    helm package -u -d charts/ $p
done; 
helm repo index . --url https://charts.mscastro.net
