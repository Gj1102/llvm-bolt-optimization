#!/usr/bin/env bash
for case in correlated dispersed ordinary; do
  echo "$case"
  grep -E 'small-function|profile|relocation|hot|WARNING' /home/gj/bolt-course-4794/experiments/$case/on.log
done
head -8 /home/gj/bolt-course-4794/experiments/correlated/profile.fdata
