"""BAT42 Schottky diode model for antiparallel activation pairs."""

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class DiodeParams:
    """Parameters for a Schottky diode (antiparallel pair activation).

    Default values from BAT42 datasheet.
    """
    Is: float = 1e-7      # Saturation current (A)
    N: float = 1.1         # Ideality factor
    VT: float = 0.02585    # Thermal voltage at 27C (V)


# Standard BAT42 parameters used throughout the project
BAT42 = DiodeParams()


def diode_current_into(v_node, v_ref, params=BAT42):
    """Net current into node from an antiparallel diode pair.

    The pair consists of two diodes in opposite orientation between
    v_node and v_ref. The net current is:
        I = -2 * Is * sinh((v_node - v_ref) / (N * VT))

    Positive current flows into the node (sinking toward v_ref when
    v_node > v_ref).
    """
    nVt = params.N * params.VT
    x = np.clip((v_node - v_ref) / nVt, -500, 500)
    return -2 * params.Is * np.sinh(x)
