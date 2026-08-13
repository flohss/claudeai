"""Reinforcement-learning upgrade path for the decision layer.

`DecisionAgent` (agent.py) is rule-based and works from the first
session. This module defines a Gymnasium environment around the same
accept/reject feedback loop so that, once enough real sessions have
produced labeled data, a policy can be trained with stable-baselines3 to
replace (or blend with) the hand-written rules — e.g. learning *when*
proposing pays off per section/style rather than using the fixed
cooldown/threshold constants in DecisionConfig.

There is no simulator here: `NeuraSetEnv.step` expects the caller (the
orchestrator, replaying logged sessions) to supply real
observation/reward transitions. Training against it before such logs
exist would just fit noise, so `train_ppo` is provided but not invoked
by default anywhere in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from neura_set.types import MusicalContext, SectionLabel

try:
    import gymnasium as gym
    from gymnasium import spaces

    _HAS_GYM = True
except ImportError:  # pragma: no cover - exercised only without the RL extra installed
    gym = None
    spaces = None
    _HAS_GYM = False

_SECTION_ORDER = list(SectionLabel)

# [tempo/200, key_root/11, key_is_minor, rms, centroid/8000, onset_density/4,
#  section_onehot(len(_SECTION_ORDER))]
OBS_DIM = 6 + len(_SECTION_ORDER)


def context_to_observation(context: MusicalContext) -> np.ndarray:
    section_onehot = np.zeros(len(_SECTION_ORDER), dtype=np.float32)
    section_onehot[_SECTION_ORDER.index(context.section)] = 1.0
    base = np.array(
        [
            min(context.tempo_bpm / 200.0, 2.0),
            context.key_root_pc / 11.0,
            float(context.key_is_minor),
            min(context.rms_energy, 1.0),
            min(context.spectral_centroid_hz / 8000.0, 2.0),
            min(context.onset_density_per_beat / 4.0, 2.0),
        ],
        dtype=np.float32,
    )
    return np.concatenate([base, section_onehot])


@dataclass
class Transition:
    observation: np.ndarray
    action: int  # 0 = don't propose, 1 = propose
    reward: float  # +1 accepted, -1 rejected, 0 no proposal made
    next_observation: np.ndarray
    done: bool = False


class NeuraSetEnv(gym.Env if _HAS_GYM else object):
    """Gymnasium environment replaying logged (context, action, feedback)
    transitions. `gymnasium` is only required if you actually train —
    the rest of NEURA-SET imports this module fine without it.

    Usage once you have logs:
        env = NeuraSetEnv(transitions)
        model = train_ppo(env)
    """

    metadata = {"render_modes": []}

    def __init__(self, transitions: list[Transition]) -> None:
        if not _HAS_GYM:
            raise ImportError(
                "gymnasium is required to use NeuraSetEnv — install the RL "
                "extras (`pip install gymnasium stable-baselines3`)."
            )
        super().__init__()
        self.transitions = transitions
        self._i = 0
        self.observation_space = spaces.Box(low=-2.0, high=2.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(2)

    def reset(self, *, seed: int | None = None, options: dict | None = None):  # noqa: ANN001
        self._i = 0
        obs = self.transitions[0].observation if self.transitions else np.zeros(OBS_DIM, dtype=np.float32)
        return obs, {}

    def step(self, action: int):  # noqa: ANN001
        if self._i >= len(self.transitions):
            return np.zeros(OBS_DIM, dtype=np.float32), 0.0, True, False, {}
        t = self.transitions[self._i]
        self._i += 1
        done = self._i >= len(self.transitions)
        reward = t.reward if action == t.action else 0.0
        next_obs = t.next_observation
        return next_obs, reward, done, False, {}


def train_ppo(env: NeuraSetEnv, total_timesteps: int = 10_000):  # noqa: ANN201
    """Train a PPO policy over logged transitions. Requires
    stable-baselines3; imported lazily so the rest of NEURA-SET doesn't
    need it installed to run."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_checker import check_env

    check_env(env, warn=True)
    model = PPO("MlpPolicy", env, verbose=0)
    model.learn(total_timesteps=total_timesteps)
    return model
