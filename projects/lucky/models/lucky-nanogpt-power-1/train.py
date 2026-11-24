"""train.py -- frozen training loop for lucky-nanogpt-power-1.

A snapshot of projects/lucky/train.py with the shared engine vendored
beside it (model.py, configurator.py, common.py). Examples are cut at
draw boundaries: the last 8 draws -> the next draw, loss on the final
draw only. Powerball whites are reshuffled every epoch.

    python prepare.py     # draws.csv -> draws.bin + meta.pkl
    python train.py       # reads config.py -> ckpt.pt (early-stopped),
                          # ckpt_final.pt, ckpt_last.pt, log.jsonl
    python train.py config.py --init_from=resume   # continue an interrupted run
"""

import json
import math
import os
import sys
import time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)  # runs in place: every path in config.py is relative to this folder
sys.path.insert(0, HERE)
if not any(not a.startswith('--') for a in sys.argv[1:]):
    sys.argv.insert(1, 'config.py')
from model import GPT, GPTConfig  # noqa: E402

from common import (  # noqa: E402
    bits_per_draw, block_size as game_block_size, floor_bits, load_dataset,
    shuffle_whites, to_xy, windows, K_HISTORY)

# -----------------------------------------------------------------------------
# defaults; a config file and --key=value flags override them
out_dir = 'projects/lucky/runs/out'
data_root = 'projects/lucky/data/pick3'
dataset = 'tokenized'
game = 'pick3'          # 'pick3' or 'powerball'
history = 0             # draws of context: 0 (control) or 8 (history)
eval_interval = 100
log_interval = 50
batch_size = 256
max_iters = 3000
init_from = 'scratch'   # or 'resume': continue from out_dir/ckpt_last.pt
# model
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.0
bias = False
# optimizer
learning_rate = 3e-4
weight_decay = 1e-1
beta1 = 0.9
beta2 = 0.99
grad_clip = 1.0
warmup_iters = 100
lr_decay_iters = 3000
min_lr = 3e-5
# system
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
seed = 1337
# -----------------------------------------------------------------------------
config_keys = [k for k, v in globals().items() if not k.startswith('_') and isinstance(v, (int, float, bool, str))]
exec(open(os.path.join(HERE, 'configurator.py')).read())
config = {k: globals()[k] for k in config_keys}
# -----------------------------------------------------------------------------

assert history in (0, K_HISTORY), f"history must be 0 or {K_HISTORY}"
block_size = game_block_size(game, history)
config['block_size'] = block_size
os.makedirs(out_dir, exist_ok=True)
torch.manual_seed(seed)

draws, meta = load_dataset(os.path.join(data_root, dataset))
splits = meta['splits']
# The first K_HISTORY draws have no full history. Both versions skip them as
# targets, so the control and the history model see the same targets.
train_idx = torch.arange(max(splits['train'][0], K_HISTORY), splits['train'][1])
val_idx = torch.arange(*splits['val'])
test_idx = torch.arange(*splits['test'])
steps_per_epoch = math.ceil(len(train_idx) / batch_size)
floor = floor_bits(game)
print(f"{game}, history {history}: {len(train_idx)} train targets, {len(val_idx)} val, {len(test_idx)} test; "
      f"block_size {block_size}; {steps_per_epoch} steps/epoch; floor {floor:.3f} bits/draw")

model_args = dict(n_layer=n_layer, n_head=n_head, n_embd=n_embd, block_size=block_size,
                  bias=bias, vocab_size=meta['vocab_size'], dropout=dropout)
model = GPT(GPTConfig(**model_args))
model.to(device)
optimizer = model.configure_optimizers(weight_decay, learning_rate, (beta1, beta2), device)


def get_lr(it):
    if it < warmup_iters:
        return learning_rate * (it + 1) / (warmup_iters + 1)
    if it > lr_decay_iters:
        return min_lr
    ratio = (it - warmup_iters) / (lr_decay_iters - warmup_iters)
    return min_lr + 0.5 * (1.0 + math.cos(math.pi * ratio)) * (learning_rate - min_lr)


def epoch_batches(epoch):
    # the epoch's order and white shuffles come from (seed, epoch) alone, so a
    # resumed run replays the interrupted epoch exactly
    data_gen = torch.Generator().manual_seed(seed * 100003 + epoch)
    order = train_idx[torch.randperm(len(train_idx), generator=data_gen)]
    for s in range(0, len(order), batch_size):
        win = windows(draws, order[s:s + batch_size], history)
        if game == 'powerball':
            win = shuffle_whites(win, data_gen)
        yield to_xy(game, win)


def save(name, iter_num, best_val, best_step):
    torch.save({
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'model_args': model_args,
        'iter_num': iter_num,
        'best_val_loss': best_val,
        'best_step': best_step,
        'config': config,
    }, os.path.join(out_dir, name))


log_path = os.path.join(out_dir, 'log.jsonl')
iter_num, best_val, best_step = 0, float('inf'), 0
resumed_at = -1
if init_from == 'resume':
    last = torch.load(os.path.join(out_dir, 'ckpt_last.pt'), map_location=device, weights_only=True)
    model.load_state_dict(last['model'])
    optimizer.load_state_dict(last['optimizer'])
    iter_num, best_val, best_step = last['iter_num'], last['best_val_loss'], last['best_step']
    resumed_at = iter_num  # this step's eval is already in the log
    with open(log_path) as f:
        kept = [line for line in f if json.loads(line)['step'] <= iter_num]
    with open(log_path, 'w') as f:
        f.writelines(kept)
    print(f"resuming from step {iter_num}")
else:
    open(log_path, 'w').close()
epoch = iter_num // steps_per_epoch
skip = iter_num % steps_per_epoch
recent = []
t0, it0 = time.time(), iter_num
done = False
while not done:
    for b, (x, y) in enumerate(epoch_batches(epoch)):
        if b < skip:
            continue
        if (iter_num % eval_interval == 0 or iter_num == max_iters) and iter_num != resumed_at:
            val = bits_per_draw(model, game, draws, val_idx, history, device).mean().item()
            test = bits_per_draw(model, game, draws, test_idx, history, device).mean().item()
            model.train()
            train_loss = sum(recent) / len(recent) if recent else None
            rec = {'step': iter_num, 'epoch': round(iter_num / steps_per_epoch, 2),
                   'train_loss_nats_per_token': train_loss,
                   'val_bits_per_draw': val, 'test_bits_per_draw': test, 'floor_bits_per_draw': floor}
            with open(log_path, 'a') as f:
                f.write(json.dumps(rec) + '\n')
            flag = ''
            if val < best_val and iter_num > 0:
                best_val, best_step = val, iter_num
                save('ckpt.pt', iter_num, best_val, best_step)
                flag = '  saving checkpoint'
            save('ckpt_last.pt', iter_num, best_val, best_step)
            print(f"step {iter_num}: val {val:.4f} test {test:.4f} bits/draw "
                  f"(floor {floor:.4f}, best val {best_val:.4f} @ {best_step}){flag}", flush=True)
            recent = []
        if iter_num == max_iters:
            done = True
            break
        for group in optimizer.param_groups:
            group['lr'] = get_lr(iter_num)
        _, loss = model(x.to(device), y.to(device))
        loss.backward()
        if grad_clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        recent.append(loss.item())
        if iter_num % log_interval == 0:
            dt = (time.time() - t0) / (iter_num - it0 + 1)
            print(f"iter {iter_num}: loss {recent[-1]:.4f}, time {dt * 1000:.1f}ms", flush=True)
        iter_num += 1
    epoch += 1
    skip = 0

save('ckpt_final.pt', iter_num, best_val, best_step)
print(f"done: {iter_num} steps, {epoch} epochs; early stop = step {best_step} (val {best_val:.4f} bits/draw)")
