#!/bin/sh
# The gatsby-nanogpt-3 size sweep: three runs on nested subsets of
# tiny-green-light-stories v3, largest first (so if time runs short, the run most
# likely to ship is already done), sequential on MPS (parallel runs contend).
# Each run's step budget grows with its data; best-val checkpointing keeps the
# minimum. Launch detached from the repo root:
#   nohup sh projects/gatsby/run_v3_sweep.sh > projects/gatsby/runs/v3-sweep.log 2>&1 & disown
set -e
for spec in full:8000 10k:4000 5k:2500; do
  name=${spec%%:*}; iters=${spec##*:}
  dir=projects/gatsby/runs/v3-$name
  mkdir -p "$dir"
  echo "=== v3-$name: $iters iters ($(date))"
  PYTHONUNBUFFERED=1 caffeinate -is uv run python core/nanogpt_core/train.py \
    projects/gatsby/config/v3.py --dataset=gatsby_v3_$name \
    --max_iters=$iters --lr_decay_iters=$iters --out_dir=$dir > "$dir/train.log" 2>&1
  grep "step .*val loss" "$dir/train.log" | sort -t' ' -k8 -g | head -1
done
echo "=== sweep done ($(date))"
