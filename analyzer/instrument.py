"""An injectable instrument interface and a reproducible software simulator.

The simulator is NOT an emulator of a specific R&S instrument. Its toy command
dialect illustrates SCPI-style write/query separation, without hardware access.
"""

from typing import Protocol
import numpy as np
from .config import Simulation, TestCase


class Instrument(Protocol):
    def identify(self) -> str: ...
    def configure(self, case: TestCase) -> None: ...
    def acquire(self) -> tuple[str, str]: ...
    def close(self) -> None: ...


class SimulatedInstrument:
    def __init__(self, settings: Simulation):
        self.settings = settings
        self.rng = np.random.default_rng(settings.seed)
        self.case = None
        self.acquisitions = 0
        self.closed = False
        self.command_log = []

    def _open(self):
        if self.closed:
            raise RuntimeError("Instrument is closed")

    def identify(self):
        self._open()
        self.command_log.append("*IDN?")
        return "PORTFOLIO,SIMULATED-METER,SOFTWARE-ONLY,1.0"

    def configure(self, case):
        self._open()
        self.case = case
        self.acquisitions = 0
        self.command_log.extend([f"CONF:FREQ {case.frequency_hz}", f"CONF:AMPL {case.amplitude_v}"])

    def acquire(self):
        self._open()
        if self.case is None:
            raise RuntimeError("Configure instrument before acquisition")
        self.acquisitions += 1
        self.command_log.extend(["MEAS:FREQ?", "MEAS:AMPL?"])
        scenario = self.settings.scenario
        if self.acquisitions % self.settings.fault_every == 0:
            if scenario == "timeout":
                raise TimeoutError("Injected simulator timeout; no physical device was contacted")
            if scenario == "malformed":
                return "NOT_A_NUMBER", "nan"
        f = self.case.frequency_hz + self.rng.normal(0, self.settings.frequency_noise_hz)
        a = self.case.amplitude_v + self.rng.normal(0, self.settings.amplitude_noise_v)
        if scenario == "bias":
            f += 0.002 * self.case.frequency_hz
            a += 0.1
        if scenario == "drift":
            f += 0.0001 * self.case.frequency_hz * (self.acquisitions - 1)
            a += 0.005 * (self.acquisitions - 1)
        return repr(float(f)), repr(float(a))

    def close(self):
        self.closed = True
