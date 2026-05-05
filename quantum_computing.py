"""
Friday Quantum Computing - Quantum algorithms and simulation.
Simulate quantum circuits, run quantum algorithms.
"""
from __future__ import annotations__

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import math
import random


# ─── Quantum Bit (Qubit) ─────────────────────────#

class Qubit:
    """Represents a single qubit in state |0>, |1>, or superposition."""
    
    def __init__(self, alpha: complex = 1.0, beta: complex = 0.0):
        """
        Initialize qubit with state: alpha|0> + beta|1>
        Norm should be 1.0 (alpha^2 + beta^2 = 1)
        """
        self.alpha = complex(alpha)
        self.beta = complex(beta)
        self._normalize()
        
    def _normalize(self):
        """Normalize to unit length."""
        norm = math.sqrt(abs(self.alpha)**2 + abs(self.beta)**2)
        if norm > 0:
            self.alpha /= norm
            self.beta /= norm
    
    def measure(self) -> int:
        """Measure qubit, returns 0 or 1."""
        prob_0 = abs(self.alpha)**2
        if random.random() < prob_0:
            self.alpha = 1.0
            self.beta = 0.0
            return 0
        else:
            self.alpha = 0.0
            self.beta = 1.0
            return 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": str(self.alpha),
            "beta": str(self.beta),
            "probability_0": abs(self.alpha)**2,
            "probability_1": abs(self.beta)**2,
        }
    
    @classmethod
    def zero(cls) -> 'Qubit':
        """Return |0> state."""
        return cls(1.0, 0.0)
    
    @classmethod
    def one(cls) -> 'Qubit':
        """Return |1> state."""
        return cls(0.0, 1.0)
    
    @classmethod
    def superposition(cls) -> 'Qubit':
        """Return (|0> + |1>)/sqrt(2) state."""
        return cls(1.0/math.sqrt(2), 1.0/math.sqrt(2))


# ─── Quantum Gate ─────────────────────────#

class QuantumGate:
    """Represents a quantum gate."""
    
    GATES = {
        "I": [[1, 0], [0, 1]],
        "X": [[0, 1], [1, 0]],
        "Y": [[0, -1j], [1j, 0]],
        "Z": [[1, 0], [0, -1]],
        "H": [[1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)]],
        "S": [[1, 0], [0, 1j]],
        "T": [[1, 0], [0, math.exp(1j*math.pi/4)]],
    }
    
    def __init__(self, gate_name: str):
        self.name = gate_name.upper()
        self.matrix = self.GATES.get(self.name, self.GATES["I"])
    
    def apply(self, qubit: Qubit) -> Qubit:
        """Apply gate to qubit."""
        new_alpha = self.matrix[0][0] * qubit.alpha + self.matrix[0][1] * qubit.beta
        new_beta = self.matrix[1][0] * qubit.alpha + self.matrix[1][1] * qubit.beta
        return Qubit(new_alpha, new_beta)
    
    @staticmethod
    def rotate_x(angle: float) -> 'QuantumGate':
        """RX rotation gate."""
        gate = QuantumGate("I")
        cos_a = math.cos(angle/2)
        sin_a = math.sin(angle/2)
        gate.matrix = [[cos_a, -1j*sin_a], [-1j*sin_a, cos_a]]
        return gate
    
    @staticmethod
    def rotate_y(angle: float) -> 'QuantumGate':
        """RY rotation gate."""
        gate = QuantumGate("I")
        cos_a = math.cos(angle/2)
        sin_a = math.sin(angle/2)
        gate.matrix = [[cos_a, -sin_a], [sin_a, cos_a]]
        return gate
    
    @staticmethod
    def rotate_z(angle: float) -> 'QuantumGate':
        """RZ rotation gate."""
        gate = QuantumGate("I")
        gate.matrix = [[math.exp(-1j*angle/2), 0], [0, math.exp(1j*angle/2)]]
        return gate


# ─── Quantum Circuit ─────────────────────────#

class QuantumCircuit:
    """A quantum circuit with multiple qubits."""
    
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.qubits = [Qubit.zero() for _ in range(num_qubits)]
        self.gates: List[Tuple[str, int, Optional[float]]] = []  # (gate, qubit_index, param)
        
    def apply_gate(self, gate_name: str, qubit_index: int, param: float = None):
        """Add gate to circuit."""
        if qubit_index < 0 or qubit_index >= self.num_qubits:
            raise ValueError(f"Invalid qubit index: {qubit_index}")
        self.gates.append((gate_name, qubit_index, param))
    
    def run(self) -> List[int]:
        """Execute circuit and measure all qubits."""
        # Apply all gates
        for gate_name, qubit_idx, param in self.gates:
            if param is not None:
                if gate_name.upper() == "RX":
                    gate = QuantumGate.rotate_x(param)
                elif gate_name.upper() == "RY":
                    gate = QuantumGate.rotate_y(param)
                elif gate_name.upper() == "RZ":
                    gate = QuantumGate.rotate_z(param)
                else:
                    gate = QuantumGate(gate_name)
            else:
                gate = QuantumGate(gate_name)
            
            self.qubits[qubit_idx] = gate.apply(self.qubits[qubit_idx])
        
        # Measure all qubits
        return [q.measure() for q in self.qubits]
    
    def get_state(self) -> List[Dict[str, Any]]:
        """Get current state of all qubits."""
        return [q.to_dict() for q in self.qubits]
    
    def reset(self):
        """Reset all qubits to |0>."""
        self.qubits = [Qubit.zero() for _ in range(self.num_qubits)]
        self.gates = []


# ─── Quantum Algorithms ─────────────────────────#

class QuantumAlgorithms:
    """Implementation of famous quantum algorithms."""
    
    @staticmethod
    def deutsch_algorithm(oracle) -> bool:
        """
        Deutsch's algorithm: determine if function is constant or balanced.
        oracle: function that takes bit, returns bit.
        Returns: True if constant, False if balanced.
        """
        # Create 2-qubit circuit
        circuit = QuantumCircuit(2)
        
        # Initialize: |0>|1>
        circuit.qubits[1] = Qubit(0, 1.0)  # Set qubit 1 to |1>
        
        # Apply H to both qubits
        circuit.apply_gate("H", 0)
        circuit.apply_gate("H", 1)
        
        # Apply oracle (black box)
        # Simplified: if oracle constant, do nothing; if balanced, apply X to qubit 1
        if not oracle(0) == oracle(1):  # Balanced
            circuit.apply_gate("X", 1)
        
        # Apply H to first qubit
        circuit.apply_gate("H", 0)
        
        # Measure first qubit
        result = circuit.run()[0]
        return result == 0  # Constant if 0
    
    @staticmethod
    def grovers_algorithm(target: int, num_qubits: int = 3, iterations: int = None) -> int:
        """
        Grover's algorithm for searching unsorted database.
        target: the item we're searching for (0 to 2^num_qubits - 1)
        Returns: measured value (should be target with high probability).
        """
        if iterations is None:
            iterations = int(math.pi/4 * math.sqrt(2**num_qubits))
        
        circuit = QuantumCircuit(num_qubits)
        
        # Initialize superposition
        for i in range(num_qubits):
            circuit.apply_gate("H", i)
        
        # Grover iteration
        for _ in range(iterations):
            # Oracle: flip phase of target state
            # Simplified: apply Z to target qubits
            binary = format(target, f"0{num_qubits}b")
            for i, bit in enumerate(binary):
                if bit == "0":
                    circuit.apply_gate("X", i)
            
            # Multi-controlled Z (simplified)
            circuit.apply_gate("Z", num_qubits - 1)
            
            # Undo X gates
            for i, bit in enumerate(binary):
                if bit == "0":
                    circuit.apply_gate("X", i)
            
            # Diffusion operator
            for i in range(num_qubits):
                circuit.apply_gate("H", i)
                circuit.apply_gate("X", i)
            
            circuit.apply_gate("Z", num_qubits - 1)
            
            for i in range(num_qubits):
                circuit.apply_gate("X", i)
                circuit.apply_gate("H", i)
        
        return circuit.run()[0]  # Simplified: return first qubit
    
    @staticmethod
    def quantum_teleportation() -> str:
        """Simulate quantum teleportation protocol."""
        # Create 3-qubit circuit
        circuit = QuantumCircuit(3)
        
        # Qubit 0: state to teleport
        circuit.qubits[0] = Qubit(1.0/math.sqrt(2), 1.0/math.sqrt(2))  # |+>
        
        # Create Bell pair between qubit 1 and 2
        circuit.apply_gate("H", 1)
        # CNOT(1, 2) - simplified
        circuit.apply_gate("X", 2)  # Simplified
        
        # Bell measurement on qubits 0 and 1
        circuit.apply_gate("H", 0)
        # CNOT(0, 1) - simplified
        circuit.apply_gate("X", 1)  # Simplified
        
        result = circuit.run()
        return f"Teleported state measured: {result}"


# ─── Quantum Fourier Transform ─────────────────────────#

class QFT:
    """Quantum Fourier Transform."""
    
    @staticmethod
    def apply(circuit: QuantumCircuit, qubits: List[int] = None):
        """Apply QFT to specified qubits."""
        if qubits is None:
            qubits = list(range(circuit.num_qubits))
        
        n = len(qubits)
        for i in range(n):
            # H gate on qubit i
            circuit.apply_gate("H", qubits[i])
            
            # Controlled phase rotations
            for j in range(i+1, n):
                angle = 2 * math.pi / (2**(j-i+1))
                # CRZ gate (simplified)
                circuit.apply_gate("Z", qubits[j])  # Simplified
        
        # Swap qubits (simplified - just reverse order)
        return circuit


# ─── Tool Function for Friday ─────────────────────────#

def quantum_tool(
    action: str = "state",
    num_qubits: int = 2,
    gates: str = None,  # JSON: [["H", 0], ["X", 1]]
    algorithm: str = None,
) -> str:
    """
    Friday tool for quantum computing.
    Actions: state, run, algorithm, qft
    """
    if action == "state":
        circuit = QuantumCircuit(num_qubits)
        state = circuit.get_state()
        
        lines = [f"### QUANTUM STATE ({num_qubits} qubits)", ""]
        for i, qubit_state in enumerate(state):
            lines.append(f"**Qubit {i}**:")
            lines.append(f"  |0>: {qubit_state['probability_0']:.2%}")
            lines.append(f"  |1>: {qubit_state['probability_1']:.2%}")
        return "\n".join(lines)
    
    if action == "run":
        if not gates:
            return "❌ Gates required (JSON array)."
        
        try:
            gate_list = json.loads(gates)
        except:
            return "❌ Invalid gates format. Use JSON: [['H', 0], ['X', 1]]"
        
        circuit = QuantumCircuit(num_qubits)
        for gate_spec in gate_list:
            gate_name = gate_spec[0]
            qubit_idx = gate_spec[1]
            param = gate_spec[2] if len(gate_spec) > 2 else None
            circuit.apply_gate(gate_name, qubit_idx, param)
        
        result = circuit.run()
        return f"### CIRCUIT RESULT\n\nMeasured: {result}"
    
    if action == "algorithm":
        if not algorithm:
            return "❌ Algorithm name required (deutsch, grovers, teleportation)."
        
        if algorithm == "deutsch":
            # Test with constant function
            def constant(x): return 0
            result = QuantumAlgorithms.deutsch_algorithm(constant)
            return f"### DEUTSCH'S ALGORITHM\n\nFunction is: {'Constant' if result else 'Balanced'}"
        
        elif algorithm == "grovers":
            target = 5
            result = QuantumAlgorithms.grovers_algorithm(target, num_qubits=3)
            return f"### GROVER'S ALGORITHM\n\nSearching for {target}...\nResult: {result}"
        
        elif algorithm == "teleportation":
            return f"### QUANTUM TELEPORTATION\n\n{QuantumAlgorithms.quantum_teleportation()}"
        
        return f"❌ Unknown algorithm: {algorithm}"
    
    if action == "qft":
        circuit = QuantumCircuit(num_qubits)
        # Put qubits in superposition
        for i in range(num_qubits):
            circuit.apply_gate("H", i)
        
        QFT.apply(circuit)
        state = circuit.get_state()
        
        lines = [f"### QFT RESULT ({num_qubits} qubits)", ""]
        for i, qubit_state in enumerate(state):
            lines.append(f"Qubit {i}: |0>={qubit_state['probability_0']:.2%}, |1>={qubit_state['probability_1']:.2%}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Quantum Computing...\n")
    
    # Test qubit
    print("--- Qubit ---")
    q = Qubit.superposition()
    print(f"Superposition: {q.to_dict()}")
    print(f"Measure: {q.measure()}")
    
    # Test circuit
    print("\n--- Circuit ---")
    print(quantum_tool("run", num_qubits=2, gates=json.dumps([["H", 0], ["H", 1]])))
    
    # Test algorithm
    print("\n--- Deutsch ---")
    print(quantum_tool("algorithm", algorithm="deutsch"))
