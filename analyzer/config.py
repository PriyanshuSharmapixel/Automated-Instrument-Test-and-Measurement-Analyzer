"""Strict configuration parsing: reject invalid limits before acquisition."""

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class TestCase:
    name: str
    frequency_hz: float
    amplitude_v: float
    frequency_tolerance_hz: float
    amplitude_tolerance_v: float
    repeats: int = 20

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Test name must be a nonempty string")
        for field in ("frequency_hz", "amplitude_v", "frequency_tolerance_hz", "amplitude_tolerance_v"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"{field} must be a finite number")
            if value < 0:
                raise ValueError(f"{field} cannot be negative")
        if self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be positive")
        if type(self.repeats) is not int or not 2 <= self.repeats <= 1000:
            raise ValueError("repeats must be an integer from 2 to 1000")


@dataclass(frozen=True)
class Simulation:
    seed: int = 42
    scenario: str = "normal"
    frequency_noise_hz: float = 10.0
    amplitude_noise_v: float = 0.002
    fault_every: int = 7

    def __post_init__(self):
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("seed must be an integer from 0 to 4294967295")
        if self.scenario not in {"normal", "bias", "drift", "timeout", "malformed"}:
            raise ValueError("Unknown simulation scenario")
        for field in ("frequency_noise_hz", "amplitude_noise_v"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{field} must be finite and nonnegative")
        if type(self.fault_every) is not int or self.fault_every < 1:
            raise ValueError("fault_every must be a positive integer")


@dataclass(frozen=True)
class Plan:
    title: str
    tests: tuple[TestCase, ...]
    simulation: Simulation = Simulation()
    retries: int = 1

    def __post_init__(self):
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Plan title cannot be blank")
        if not 1 <= len(self.tests) <= 30 or not all(isinstance(t, TestCase) for t in self.tests):
            raise ValueError("Supply between 1 and 30 test cases")
        if len({t.name for t in self.tests}) != len(self.tests):
            raise ValueError("Test names must be unique")
        if type(self.retries) is not int or not 0 <= self.retries <= 3:
            raise ValueError("retries must be an integer from 0 to 3")

    def to_dict(self):
        data = asdict(self)
        data["tests"] = list(data["tests"])
        return data


def parse_plan(data: dict) -> Plan:
    try:
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")
        if set(data) - {"title", "tests", "simulation", "retries"}:
            raise ValueError("Unknown plan field")
        return Plan(
            title=data["title"], tests=tuple(TestCase(**item) for item in data["tests"]),
            simulation=Simulation(**data.get("simulation", {})), retries=data.get("retries", 1),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid configuration: {exc}") from exc


def load_plan(path: str | Path) -> Plan:
    return parse_plan(json.loads(Path(path).read_text(encoding="utf-8")))
