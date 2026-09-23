from __future__ import annotations

"""Software-first quantum and nanotechnology research layer for KRISHNA LAB BOT.

This module provides:
- a bounded local state-vector simulator for small educational/research circuits;
- optional provider discovery for Qiskit and PennyLane;
- nanoscale geometry/property planning with optional pymatgen/ASE provider discovery;
- a quantum+nano bridge for research areas such as quantum materials and nanophotonics.

It does not claim access to real QPUs, nanofabrication equipment, or validated
materials calculations merely because software packages are present.
"""

import cmath
import importlib.util
import math


class QuantumNanoLab:
    VERSION = "krishna-quantum-nano-lab-v1"
    MAX_LOCAL_QUBITS = 8

    @staticmethod
    def _installed(module: str) -> bool:
        try:
            return importlib.util.find_spec(module) is not None
        except Exception:
            return False

    def status(self) -> dict:
        return {
            "version": self.VERSION,
            "quantum": {
                "local_statevector": True,
                "max_local_qubits": self.MAX_LOCAL_QUBITS,
                "qiskit_available": self._installed("qiskit"),
                "pennylane_available": self._installed("pennylane"),
                "real_qpu_verified": False,
                "research_areas": [
                    "quantum circuits",
                    "Hamiltonian simulation planning",
                    "variational algorithms",
                    "quantum chemistry planning",
                    "quantum sensing models",
                    "quantum machine learning benchmarking",
                ],
            },
            "nano": {
                "geometry_model": True,
                "pymatgen_available": self._installed("pymatgen"),
                "ase_available": self._installed("ase"),
                "materials_project_adapter_configured": False,
                "nanofabrication_verified": False,
                "research_areas": [
                    "nanomaterials",
                    "surface-to-volume effects",
                    "nanophotonics",
                    "nanoelectronics",
                    "quantum dots",
                    "nanoscale sensors",
                    "defects and interfaces",
                ],
            },
            "bridge": {
                "research_areas": [
                    "quantum materials",
                    "quantum dots",
                    "nanophotonics",
                    "spin defects",
                    "nanoscale quantum sensing",
                    "superconducting and mesoscopic devices",
                    "molecular and materials simulation",
                ],
                "policy": "software simulation first; physical quantum hardware and nanofabrication remain adapter- and evidence-gated",
            },
        }

    @staticmethod
    def _normalize_gate_name(value: str) -> str:
        return str(value or "").strip().lower().replace("-", "").replace("_", "")

    @staticmethod
    def _single_matrix(gate: str, theta: float | None = None):
        s = 1 / math.sqrt(2)
        if gate == "x":
            return ((0j, 1+0j), (1+0j, 0j))
        if gate == "y":
            return ((0j, -1j), (1j, 0j))
        if gate == "z":
            return ((1+0j, 0j), (0j, -1+0j))
        if gate == "h":
            return ((s+0j, s+0j), (s+0j, -s+0j))
        if gate in {"rx", "ry", "rz"}:
            if theta is None:
                raise ValueError(f"{gate} requires theta")
            t = float(theta) / 2.0
            if gate == "rx":
                return ((math.cos(t)+0j, -1j*math.sin(t)), (-1j*math.sin(t), math.cos(t)+0j))
            if gate == "ry":
                return ((math.cos(t)+0j, -math.sin(t)+0j), (math.sin(t)+0j, math.cos(t)+0j))
            return ((cmath.exp(-1j*t), 0j), (0j, cmath.exp(1j*t)))
        raise ValueError(f"unsupported single-qubit gate: {gate}")

    @staticmethod
    def _apply_single(state, n, target, matrix):
        out = list(state)
        step = 1 << target
        size = 1 << n
        for base in range(0, size, step << 1):
            for offset in range(step):
                i0 = base + offset
                i1 = i0 + step
                a0, a1 = state[i0], state[i1]
                out[i0] = matrix[0][0]*a0 + matrix[0][1]*a1
                out[i1] = matrix[1][0]*a0 + matrix[1][1]*a1
        return out

    @staticmethod
    def _apply_cx(state, n, control, target):
        if control == target:
            raise ValueError("control and target must differ")
        out = list(state)
        size = 1 << n
        for i in range(size):
            if ((i >> control) & 1) == 1 and ((i >> target) & 1) == 0:
                j = i | (1 << target)
                out[i], out[j] = state[j], state[i]
        return out

    def quantum_simulate(self, payload: dict) -> dict:
        n = int(payload.get("qubits") or 1)
        if n < 1 or n > self.MAX_LOCAL_QUBITS:
            raise ValueError(f"qubits must be between 1 and {self.MAX_LOCAL_QUBITS}")
        gates = list(payload.get("gates") or [])
        if len(gates) > 256:
            raise ValueError("gate count exceeds bounded local simulation limit")

        size = 1 << n
        state = [0j] * size
        state[0] = 1+0j

        normalized = []
        for raw in gates:
            row = dict(raw or {})
            gate = self._normalize_gate_name(row.get("gate"))
            if gate == "cx":
                control = int(row.get("control"))
                target = int(row.get("target"))
                if min(control, target) < 0 or max(control, target) >= n:
                    raise ValueError("qubit index out of range")
                state = self._apply_cx(state, n, control, target)
                normalized.append({"gate": "cx", "control": control, "target": target})
            else:
                target = int(row.get("target") or 0)
                if target < 0 or target >= n:
                    raise ValueError("qubit index out of range")
                theta = row.get("theta")
                matrix = self._single_matrix(gate, theta)
                state = self._apply_single(state, n, target, matrix)
                entry = {"gate": gate, "target": target}
                if theta is not None:
                    entry["theta"] = float(theta)
                normalized.append(entry)

        probabilities = {}
        amplitudes = {}
        for index, amp in enumerate(state):
            bits = format(index, f"0{n}b")
            probability = float((amp.real*amp.real) + (amp.imag*amp.imag))
            if probability > 1e-14:
                probabilities[bits] = round(probability, 12)
                amplitudes[bits] = {
                    "real": round(float(amp.real), 12),
                    "imag": round(float(amp.imag), 12),
                }

        return {
            "engine": "krishna-local-statevector",
            "physical": False,
            "qubits": n,
            "gates": normalized,
            "probabilities": probabilities,
            "amplitudes": amplitudes,
            "normalization": round(sum(probabilities.values()), 12),
            "claim_scope": "classical simulation of a bounded quantum-circuit model; not evidence of quantum advantage or real-QPU execution",
        }

    def quantum_plan(self, payload: dict) -> dict:
        question = str(payload.get("question") or payload.get("objective") or "").strip()
        if not question:
            raise ValueError("question or objective is required")
        goal = question.lower()
        tracks = ["classical baseline", "small local state-vector simulation"]
        if any(x in goal for x in ("molecule", "chemistry", "material", "hamilton")):
            tracks += ["Hamiltonian construction", "variational/energy-estimation benchmark"]
        if any(x in goal for x in ("sensor", "sensing", "field", "frequency", "magnetic")):
            tracks += ["quantum sensing model", "noise and sensitivity benchmark"]
        if any(x in goal for x in ("machine learning", "classification", "learning", "qml")):
            tracks += ["classical ML baseline", "variational quantum model benchmark"]
        return {
            "kind": "quantum_research_plan",
            "question": question[:4000],
            "tracks": list(dict.fromkeys(tracks)),
            "providers": {
                "local_statevector": True,
                "qiskit": self._installed("qiskit"),
                "pennylane": self._installed("pennylane"),
                "real_qpu_verified": False,
            },
            "evidence_rules": [
                "compare against a classical baseline",
                "record noise/model assumptions",
                "do not claim quantum advantage without a valid matched benchmark",
                "separate simulator results from real-QPU measurements",
            ],
        }

    def nano_geometry(self, payload: dict) -> dict:
        shape = str(payload.get("shape") or "").strip().lower()
        if shape == "sphere":
            r = float(payload.get("radius_nm") or 0)
            if r <= 0:
                raise ValueError("radius_nm must be > 0")
            area = 4 * math.pi * r*r
            volume = (4/3) * math.pi * r*r*r
            dims = {"radius_nm": r}
        elif shape == "cube":
            a = float(payload.get("edge_nm") or 0)
            if a <= 0:
                raise ValueError("edge_nm must be > 0")
            area = 6*a*a
            volume = a*a*a
            dims = {"edge_nm": a}
        elif shape == "cylinder":
            r = float(payload.get("radius_nm") or 0)
            h = float(payload.get("height_nm") or 0)
            if r <= 0 or h <= 0:
                raise ValueError("radius_nm and height_nm must be > 0")
            area = 2*math.pi*r*h + 2*math.pi*r*r
            volume = math.pi*r*r*h
            dims = {"radius_nm": r, "height_nm": h}
        else:
            raise ValueError("shape must be sphere, cube or cylinder")

        return {
            "engine": "krishna-nano-geometry",
            "physical": False,
            "shape": shape,
            "dimensions": dims,
            "surface_area_nm2": round(area, 12),
            "volume_nm3": round(volume, 12),
            "surface_to_volume_per_nm": round(area/volume, 12),
            "claim_scope": "geometric nanoscale descriptor only; material properties require validated physical/atomistic models",
        }

    def nano_plan(self, payload: dict) -> dict:
        objective = str(payload.get("objective") or payload.get("question") or "").strip()
        if not objective:
            raise ValueError("objective or question is required")
        text = objective.lower()
        analyses = ["structure/provenance", "size and surface effects", "uncertainty and experimental comparison"]
        if any(x in text for x in ("electronic", "band", "semiconductor", "conduct")):
            analyses += ["electronic-structure workflow", "band/DOS comparison"]
        if any(x in text for x in ("optical", "photon", "light", "plasmon")):
            analyses += ["optical-property workflow", "nanophotonic response benchmark"]
        if any(x in text for x in ("defect", "vacancy", "interface", "surface")):
            analyses += ["defect/interface model", "surface-energy comparison"]
        if any(x in text for x in ("mechanical", "strength", "elastic")):
            analyses += ["elastic/mechanical model"]
        return {
            "kind": "nano_research_plan",
            "objective": objective[:4000],
            "analyses": list(dict.fromkeys(analyses)),
            "providers": {
                "pymatgen": self._installed("pymatgen"),
                "ase": self._installed("ase"),
                "materials_project_adapter_configured": False,
                "nanofabrication_verified": False,
            },
            "evidence_rules": [
                "separate geometric descriptors from calculated material properties",
                "record calculator/functional/potential and convergence settings for atomistic results",
                "compare simulations with independent experimental or trusted reference data where available",
                "do not infer biocompatibility, toxicity or clinical efficacy from a materials simulation alone",
            ],
        }

    def bridge_plan(self, payload: dict) -> dict:
        objective = str(payload.get("objective") or payload.get("question") or "").strip()
        if not objective:
            raise ValueError("objective or question is required")
        return {
            "kind": "quantum_nano_bridge",
            "objective": objective[:4000],
            "candidate_areas": [
                "quantum materials",
                "quantum dots",
                "nanophotonics",
                "spin-defect sensing",
                "nanoscale quantum sensors",
                "mesoscopic/superconducting devices",
                "molecular and materials quantum simulation",
            ],
            "workflow": [
                "define measurable target",
                "establish classical/materials baseline",
                "construct bounded quantum or atomistic model",
                "simulate and quantify uncertainty",
                "compare with trusted literature/reference data",
                "only then design reviewed physical measurement/fabrication",
            ],
            "physical_execution": False,
        }
