#!/bin/bash
git remote set-url origin git@github-Alexei:Metrologia-code/PyProjects.git
git config user.name "Alexei-Ch"
git config user.email "billy.solitaire@gmail.com"
eval $(ssh-agent -s)
git status