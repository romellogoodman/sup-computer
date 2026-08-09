# pona chat arm -- the word-level model for the keyboard UI, trained from
# scratch on the natural corpus interleaved with oracle-filtered dialogues
# (data/build_chat_corpus.py). Same body and schedule as the word arm; the
# only variable is the corpus mixture.
#
# Frozen release copy — run in place:
#   python train.py config.py

out_dir = '.'
data_root = '.'
dataset = 'tokenized-chat'

eval_interval = 50
eval_iters = 100
log_interval = 20

always_save_checkpoint = False
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128

n_layer = 6
n_head = 6
n_embd = 192
dropout = 0.1

learning_rate = 3e-4
max_iters = 1500
lr_decay_iters = 1500
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 50

device = 'mps'
compile = False
