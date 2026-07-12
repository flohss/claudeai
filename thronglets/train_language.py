"""Train a real, gradient-based emergent language - the "more ambitious" path.

simulation.py's colors emerge from blind evolutionary drift: two states can
end up sharing a color purely by chance, because nothing in that model is
actually optimizing for successful communication, only surviving long enough
to reproduce. This script instead trains a Speaker and a Listener network
with backpropagation to directly minimize communication error, using the
same state/token vocabulary (5 states, 6 tokens including silence) so the
outcome is a fair, apples-to-apples comparison.

The game, each step:
  1. A state (idle / food / mate / danger / distress) is sampled - by
     default with the same skewed frequency idle dominates with in the real
     simulation, since that skew is exactly what causes idle to "win"
     collisions there.
  2. The Speaker sees the state and emits a token (Gumbel-Softmax, so the
     discrete choice stays differentiable during training).
  3. The Listener sees only the token (never the true state) and predicts
     which state produced it.
  4. Both networks are trained jointly, by backpropagating the Listener's
     prediction error straight through the channel to the Speaker - i.e.
     ambiguity is penalized directly, every step, rather than hoped for.

This needs PyTorch (`pip install torch`), a genuinely heavy dependency that
is not expected to work on Termux - unlike main.py/main_tui.py/main_web.py,
this script is a separate, optional experiment and does not touch the real-
time simulation or its renderers.
"""

import argparse
import json

import torch
import torch.nn as nn
import torch.nn.functional as F

from simulation import DANGER, DISTRESS, FOOD, IDLE, MATE, N_STATES, N_TOKENS

STATE_NAMES = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call",
               DISTRESS: "distress-call"}
DEFAULT_CHECKPOINT = "language_model.pt"
DEFAULT_VOCAB_EXPORT = "language_model.json"

# Roughly the state frequencies actually observed in simulation.py's runs:
# idle dominates because it's the default when nothing else applies.
REALISTIC_WEIGHTS = torch.tensor([0.72, 0.13, 0.08, 0.04, 0.03])  # idle, food, mate, danger, distress


class Speaker(nn.Module):
    def __init__(self, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(N_STATES, hidden), nn.ReLU(),
            nn.Linear(hidden, N_TOKENS),
        )

    def forward(self, state_onehot):
        return self.net(state_onehot)  # logits over tokens


class Listener(nn.Module):
    def __init__(self, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(N_TOKENS, hidden), nn.ReLU(),
            nn.Linear(hidden, N_STATES),
        )

    def forward(self, token_onehot):
        return self.net(token_onehot)  # logits over states


def sample_states(batch_size, weights):
    return torch.multinomial(weights, batch_size, replacement=True)


def save_checkpoint(path, speaker, listener):
    torch.save({"speaker": speaker.state_dict(), "listener": listener.state_dict()}, path)
    print(f"\nSaved what it learned to '{path}' - reload it later with --load {path}")


def load_checkpoint(path):
    checkpoint = torch.load(path, weights_only=True)
    speaker = Speaker()
    listener = Listener()
    speaker.load_state_dict(checkpoint["speaker"])
    listener.load_state_dict(checkpoint["listener"])
    speaker.eval()
    listener.eval()
    print(f"Loaded a previously trained brain from '{path}' (no training this run).")
    return speaker, listener


def train(episodes, batch_size, skewed, lr, seed, verbose=True):
    torch.manual_seed(seed)
    speaker = Speaker()
    listener = Listener()
    optimizer = torch.optim.Adam(list(speaker.parameters()) + list(listener.parameters()), lr=lr)
    weights = REALISTIC_WEIGHTS if skewed else torch.ones(N_STATES) / N_STATES

    for step in range(episodes):
        temperature = max(0.5, 2.0 - step / episodes * 1.5)  # anneal: exploratory -> near-discrete

        states = sample_states(batch_size, weights)
        state_onehot = F.one_hot(states, N_STATES).float()

        token_logits = speaker(state_onehot)
        token_onehot = F.gumbel_softmax(token_logits, tau=temperature, hard=True)

        state_logits = listener(token_onehot)
        loss = F.cross_entropy(state_logits, states)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if verbose and (step % max(1, episodes // 20) == 0 or step == episodes - 1):
            with torch.no_grad():
                acc = (state_logits.argmax(dim=1) == states).float().mean().item()
            print(f"step {step:6d}/{episodes}   loss {loss.item():.3f}   listener accuracy {acc:.0%}   temp {temperature:.2f}")

    return speaker, listener


def export_vocabulary(speaker, listener, path):
    """Bake the trained networks down to two small lookup tables (state->token,
    token->state) and write them as plain JSON - no PyTorch needed to read this
    back, so simulation.py and the renderers can seed a game with it without
    ever importing torch. This is the bridge between the experiment and the
    actual (Termux-friendly) game."""
    with torch.no_grad():
        state_onehot = F.one_hot(torch.arange(N_STATES), N_STATES).float()
        state_to_token = speaker(state_onehot).argmax(dim=1).tolist()

        token_onehot = F.one_hot(torch.arange(N_TOKENS), N_TOKENS).float()
        token_to_state = listener(token_onehot).argmax(dim=1).tolist()

    with open(path, "w") as f:
        json.dump({"state_to_token": state_to_token, "token_to_state": token_to_state}, f, indent=2)
    print(f"Exported a game-ready vocabulary to '{path}' (no PyTorch needed to use it).")


def evaluate(speaker, listener):
    """Returns (token per state, whether any two states collide, held-out accuracy)."""
    all_onehot = F.one_hot(torch.arange(N_STATES), N_STATES).float()
    with torch.no_grad():
        tokens = speaker(all_onehot).argmax(dim=1)

    seen = set()
    collisions = False
    for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
        token = tokens[state].item()
        if token in seen:
            collisions = True
        seen.add(token)

    with torch.no_grad():
        states = sample_states(4000, torch.ones(N_STATES) / N_STATES)
        state_onehot = F.one_hot(states, N_STATES).float()
        tokens_soft = F.gumbel_softmax(speaker(state_onehot), tau=0.3, hard=True)
        preds = listener(tokens_soft).argmax(dim=1)
        acc = (preds == states).float().mean().item()

    return tokens, collisions, acc


def report_vocabulary(speaker, listener):
    print("\nEmergent vocabulary (deterministic, temperature -> 0):")
    tokens, collisions, acc = evaluate(speaker, listener)

    seen = {}
    for state in (DANGER, FOOD, DISTRESS, MATE, IDLE):
        token = tokens[state].item()
        label = STATE_NAMES[state]
        marker = f"  <-- same token as '{seen[token]}' !" if token in seen else ""
        seen.setdefault(token, label)
        print(f"  {label:<10} -> token {token}{marker}")

    print()
    if collisions:
        print("Still some homonymy - the pressure was real but training was short, or")
        print("the states are genuinely hard to tell apart from context alone.")
    else:
        print("No collisions: every state got its own token. Unlike the evolved")
        print("version, gradient descent directly penalizes ambiguity every step,")
        print("so it doesn't get to just get lucky (or unlucky) and drift away.")
    print(f"\nOverall communication accuracy on held-out samples: {acc:.1%}")


def sweep(n_seeds, episodes, batch_size, skewed, lr):
    """Train n_seeds independent runs and report how often collisions happen."""
    collisions = 0
    accuracies = []
    for seed in range(n_seeds):
        speaker, listener = train(episodes, batch_size, skewed, lr, seed, verbose=False)
        _, had_collision, acc = evaluate(speaker, listener)
        accuracies.append(acc)
        collisions += had_collision
        print(f"seed {seed}: {'COLLISION' if had_collision else 'clean':<9}  accuracy {acc:.1%}")
    clean = n_seeds - collisions
    print(f"\n{clean}/{n_seeds} seeds converged with zero homonymy "
          f"(mean accuracy {sum(accuracies) / n_seeds:.1%})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--uniform", action="store_true",
                         help="sample states uniformly instead of matching the real sim's idle-heavy skew")
    parser.add_argument("--sweep", type=int, default=0,
                         help="train this many seeds and report the collision rate, instead of a single run")
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT,
                         help=f"file to save to / load from (default: {DEFAULT_CHECKPOINT})")
    parser.add_argument("--load", action="store_true",
                         help="skip training - load a previously saved brain instead")
    parser.add_argument("--export", type=str, default=DEFAULT_VOCAB_EXPORT,
                         help=f"where to write the game-ready vocabulary (default: {DEFAULT_VOCAB_EXPORT})")
    args = parser.parse_args()

    if args.sweep:
        sweep(args.sweep, args.episodes, args.batch_size, not args.uniform, args.lr)
        return

    if args.load:
        speaker, listener = load_checkpoint(args.checkpoint)
    else:
        speaker, listener = train(args.episodes, args.batch_size, not args.uniform, args.lr, args.seed)
        save_checkpoint(args.checkpoint, speaker, listener)

    report_vocabulary(speaker, listener)
    export_vocabulary(speaker, listener, args.export)


if __name__ == "__main__":
    main()
