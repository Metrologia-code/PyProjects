#!/bin/bash
git remote set-url origin git@github-Luparev:Metrologia-code/PyProjects.git
git config user.name "Luparev"
git config user.email "luparev@gmail.com"
eval $(ssh-agent -s)
git status