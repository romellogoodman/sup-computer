#!/bin/zsh
# Experiment 13 seed sweep: the frozen v3 recipe, only the seed varies.
set -u
cd "$(dirname "$0")/../../models/shakespeare-nanogpt-3"
for s in 1 2 3 4 5 6 7 8; do
  d=../../runs/seed-sweep/seed-$s; mkdir -p $d
  echo "=== seed $s start $(date)" >> ../../runs/seed-sweep/sweep.log
  PYTHONUNBUFFERED=1 uv run python train.py --seed=$s --out_dir=$d --data_root=../../data > $d/train.log 2>&1
  echo "=== seed $s exit $? $(date)" >> ../../runs/seed-sweep/sweep.log
done
# control: seed 1 stopped at 1000 iters on the same schedule
d=../../runs/seed-sweep/seed-1-iter1000; mkdir -p $d
echo "=== control start $(date)" >> ../../runs/seed-sweep/sweep.log
PYTHONUNBUFFERED=1 uv run python train.py --seed=1 --max_iters=1000 --out_dir=$d --data_root=../../data > $d/train.log 2>&1
echo "=== control exit $? $(date)" >> ../../runs/seed-sweep/sweep.log
echo "=== SWEEP DONE $(date)" >> ../../runs/seed-sweep/sweep.log
