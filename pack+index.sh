#!/bin/sh
ls | grep -v -e charts -e README -e index.yaml -e helmfiles -e pack+index | while read p; do 
    helm package -u -d charts/ $p
done; 
helm repo index . --url https://charts.mscastro.net
git add -A
git commit -a -m "update main"
git push
git checkout gh-pages
git restore --source main index.yaml charts/ helmfiles/ README.md
git add -A
git commit -a -m "update repo"
git push
git checkout main
