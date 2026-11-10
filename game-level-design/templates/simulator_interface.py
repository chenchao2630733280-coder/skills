# Copy and adapt this interface for your game.
from typing import Any, Iterable

def initial_state(level_config: dict, seed: int) -> Any:
    raise NotImplementedError

def legal_actions(state: Any) -> list:
    raise NotImplementedError

def step(state: Any, action: Any, rng: Any):
    """Return next_state, reward, done, info."""
    raise NotImplementedError

def policy(state: Any, player_profile: dict) -> Any:
    raise NotImplementedError

def run_episode(level_config: dict, seed: int, policy_fn, player_profile: dict) -> dict:
    raise NotImplementedError

def batch_evaluate(level_config: dict, seeds: Iterable[int], policies: dict, profiles: dict) -> dict:
    raise NotImplementedError
