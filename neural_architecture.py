"""
Friday Neural Architecture - Neural networks and deep learning.
Build, train, and use neural networks for various tasks.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


# ─── Simple Neural Network ─────────────────────────────────#

class SimpleNeuralNetwork:
    """A simple feedforward neural network implemented from scratch."""
    
    def __init__(self, layer_sizes: List[int]):
        """
        Initialize network with given layer sizes.
        Example: [10, 20, 5] = input:10, hidden:20, output:5
        """
        self.layer_sizes = layer_sizes
        self.weights = []
        self.biases = []
        self._initialize_parameters()
        
    def _initialize_parameters(self):
        """Initialize weights and biases randomly."""
        import random
        import math
        
        for i in range(len(self.layer_sizes) - 1):
            # He initialization
            fan_in = self.layer_sizes[i]
            limit = math.sqrt(2.0 / fan_in)
            
            w = [
                [random.uniform(-limit, limit) for _ in range(self.layer_sizes[i + 1])]
                for _ in range(self.layer_sizes[i])
            ]
            b = [0.0] * self.layer_sizes[i + 1]
            
            self.weights.append(w)
            self.biases.append(b)
        
    def _relu(self, x: float) -> float:
        """ReLU activation."""
        return max(0.0, x)
    
    def _relu_derivative(self, x: float) -> float:
        """Derivative of ReLU."""
        return 1.0 if x > 0.0 else 0.0
    
    def _forward(self, inputs: List[float]) -> Tuple[List[List[float]], List[List[float]]]:
        """
        Forward pass through the network.
        Returns (activations, z_values) for each layer.
        """
        activations = [inputs]
        z_values = []
        
        current = inputs[:]
        
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = [
                sum(w[j][k] * current[j] for j in range(len(current))) + b[k]
                for k in range(len(b))
            ]
            z_values.append(z)
            
            if i < len(self.weights) - 1:
                current = [self._relu(zz) for zz in z]
            else:
                current = z  # No activation on output layer
            
            activations.append(current)
        
        return activations, z_values
    
    def predict(self, inputs: List[float]) -> List[float]:
        """Make a prediction."""
        activations, _ = self._forward(inputs)
        return activations[-1]
    
    def _compute_loss(self, predictions: List[float], targets: List[float]) -> float:
        """Mean squared error loss."""
        return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(predictions)
    
    def train(
        self,
        training_data: List[Tuple[List[float], List[float]]],
        epochs: int = 100,
        learning_rate: float = 0.01,
        verbose: bool = True
    ) -> List[float]:
        """
        Train the network using backpropagation.
        Returns loss history.
        """
        import random
        loss_history = []
        
        for epoch in range(epochs):
            total_loss = 0.0
            random.shuffle(training_data)
            
            for inputs, targets in training_data:
                # Forward pass
                activations, z_values = self._forward(inputs)
                predictions = activations[-1]
                
                # Compute loss
                loss = self._compute_loss(predictions, targets)
                total_loss += loss
                
                # Backward pass (simplified)
                # Output layer gradient
                output_error = [(p - t) for p, t in zip(predictions, targets)]
                
                # Update output layer
                output_idx = len(self.weights) - 1
                for j in range(len(self.weights[output_idx])):
                    for k in range(len(self.biases[output_idx])):
                        gradient = output_error[k] * activations[output_idx][j]
                        self.weights[output_idx][j][k] -= learning_rate * gradient
                    self.biases[output_idx][k] -= learning_rate * output_error[k]
                
                # Hidden layer gradients (simplified)
                for layer_idx in range(len(self.weights) - 2, -1, -1):
                    for j in range(len(self.weights[layer_idx])):
                        for k in range(len(self.biases[layer_idx])):
                            # Simplified: propagate error backward
                            error = output_error[k] if layer_idx == len(self.weights) - 2 else 0.0
                            gradient = error * self._relu_derivative(z_values[layer_idx][k]) * activations[layer_idx][j]
                            self.weights[layer_idx][j][k] -= learning_rate * gradient
                        self.biases[layer_idx][k] -= learning_rate * error * self._relu_derivative(z_values[layer_idx][k])
            
            avg_loss = total_loss / len(training_data)
            loss_history.append(avg_loss)
            
            if verbose and epoch % 10 == 0:
                print(f"Epoch {epoch}: Loss = {avg_loss:.6f}")
        
        return loss_history
    
    def save(self, path: str):
        """Save network to file."""
        data = {
            "layer_sizes": self.layer_sizes,
            "weights": self.weights,
            "biases": self.biases,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'SimpleNeuralNetwork':
        """Load network from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        net = cls(data["layer_sizes"])
        net.weights = data["weights"]
        net.biases = data["biases"]
        return net


# ─── Neural Architecture Search ─────────────────────────────────#

class NeuralArchitectureSearch:
    """Simple neural architecture search for finding good network architectures."""
    
    def __init__(self, input_size: int, output_size: int):
        self.input_size = input_size
        self.output_size = output_size
        self.best_architecture = None
        self.best_score = float('inf')
        
    def _generate_random_architecture(self) -> List[int]:
        """Generate a random architecture."""
        import random
        num_hidden = random.randint(1, 3)
        hidden_sizes = [random.randint(5, 50) for _ in range(num_hidden)]
        return [self.input_size] + hidden_sizes + [self.output_size]
    
    def _evaluate_architecture(
        self,
        layer_sizes: List[int],
        train_data: List[Tuple[List[float], List[float]]],
        val_data: List[Tuple[List[float], List[float]]],
        epochs: int = 50
    ) -> float:
        """Train and evaluate a network architecture."""
        try:
            net = SimpleNeuralNetwork(layer_sizes)
            net.train(train_data, epochs=epochs, verbose=False)
            
            # Evaluate on validation data
            total_loss = 0.0
            for inputs, targets in val_data:
                predictions = net.predict(inputs)
                loss = net._compute_loss(predictions, targets)
                total_loss += loss
            
            return total_loss / len(val_data)
        except Exception:
            return float('inf')
    
    def search(
        self,
        train_data: List[Tuple[List[float], List[float]]],
        val_data: List[Tuple[List[float], List[float]]],
        num_trials: int = 10,
        epochs_per_trial: int = 50
    ) -> Dict[str, Any]:
        """
        Search for the best architecture.
        Returns {best_architecture, best_score, all_results}
        """
        results = []
        
        for trial in range(num_trials):
            arch = self._generate_random_architecture()
            print(f"Trial {trial + 1}/{num_trials}: Testing {arch}")
            
            score = self._evaluate_architecture(arch, train_data, val_data, epochs_per_trial)
            
            results.append({
                "architecture": arch,
                "score": score,
            })
            
            if score < self.best_score:
                self.best_score = score
                self.best_architecture = arch
                print(f"  New best! Score: {score:.6f}")
        
        # Sort by score
        results.sort(key=lambda x: x["score"])
        
        return {
            "best_architecture": self.best_architecture,
            "best_score": self.best_score,
            "all_results": results[:5],  # Top 5
        }


# ─── Time Series Predictor ─────────────────────────────────#

class TimeSeriesPredictor:
    """Predict time series using neural networks."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.network = None
        self.mean = 0.0
        self.std = 1.0
        
    def _normalize(self, data: List[float]) -> List[float]:
        """Normalize data to zero mean and unit variance."""
        if len(data) < 2:
            return data[:]
        
        self.mean = sum(data) / len(data)
        variance = sum((x - self.mean) ** 2 for x in data) / len(data)
        self.std = variance ** 0.5
        
        if self.std == 0:
            return [0.0] * len(data)
        
        return [(x - self.mean) / self.std for x in data]
    
    def _create_sequences(self, data: List[float]) -> List[Tuple[List[float], List[float]]]:
        """Create input-output sequences for training."""
        if len(data) <= self.window_size:
            return []
        
        sequences = []
        for i in range(len(data) - self.window_size):
            inputs = data[i:i + self.window_size]
            target = data[i + self.window_size]
            sequences.append((inputs, [target]))
        
        return sequences
    
    def train(self, time_series: List[float], epochs: int = 100):
        """Train the predictor on a time series."""
        # Normalize
        normalized = self._normalize(time_series)
        
        # Create sequences
        sequences = self._create_sequences(normalized)
        if not sequences:
            return "❌ Not enough data. Need more than window_size points."
        
        # Split into train/validation
        split = int(0.8 * len(sequences))
        train_data = sequences[:split]
        val_data = sequences[split:]
        
        # Create and train network
        self.network = SimpleNeuralNetwork([self.window_size, 50, 20, 1])
        
        print(f"Training on {len(train_data)} samples...")
        loss_history = self.network.train(train_data, epochs=epochs, verbose=False)
        
        # Calculate validation loss
        val_loss = 0.0
        for inputs, target in val_data:
            pred = self.network.predict(inputs)
            val_loss += (pred[0] - target[0]) ** 2
        val_loss /= len(val_data)
        
        return f"✅ Training complete. Final loss: {loss_history[-1]:.6f}, Val loss: {val_loss:.6f}"
    
    def predict_next(self, recent_values: List[float]) -> float:
        """Predict the next value."""
        if not self.network:
            return 0.0
        
        if len(recent_values) < self.window_size:
            return 0.0
        
        # Normalize
        normalized = [(x - self.mean) / self.std for x in recent_values[-self.window_size:]]
        
        # Predict
        pred_normalized = self.network.predict(normalized)[0]
        
        # Denormalize
        return pred_normalized * self.std + self.mean


# ─── Singleton Instances ─────────────────────────────────#

_networks: Dict[str, SimpleNeuralNetwork] = {}
_nas: Optional[NeuralArchitectureSearch] = None
_predictor: Optional[TimeSeriesPredictor] = None

def get_network(name: str = "default") -> Optional[SimpleNeuralNetwork]:
    """Get or create a neural network."""
    if name not in _networks:
        return None
    return _networks[name]

def create_network(name: str, layer_sizes: List[int]) -> SimpleNeuralNetwork:
    """Create a new neural network."""
    global _networks
    net = SimpleNeuralNetwork(layer_sizes)
    _networks[name] = net
    return net

def get_nas(input_size: int, output_size: int) -> NeuralArchitectureSearch:
    """Get or create NAS."""
    global _nas
    if _nas is None:
        _nas = NeuralArchitectureSearch(input_size, output_size)
    return _nas

def get_predictor(window_size: int = 10) -> TimeSeriesPredictor:
    """Get or create time series predictor."""
    global _predictor
    if _predictor is None:
        _predictor = TimeSeriesPredictor(window_size)
    return _predictor


# ─── Tool Function for Friday ─────────────────────────────────#

def neural_tool(
    action: str = "create",
    name: str = None,
    layer_sizes: str = None,  # JSON list
    data: str = None,  # JSON list of numbers
    epochs: int = 100,
) -> str:
    """
    Friday tool for neural network operations.
    Actions: create, train, predict, nas, timeseries
    """
    if action == "create":
        if not name or not layer_sizes:
            return "❌ name and layer_sizes (JSON list) required."
        
        try:
            sizes = json.loads(layer_sizes)
            net = create_network(name, sizes)
            return f"✅ Created network '{name}' with layers: {sizes}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    if action == "train":
        if not name or not data:
            return "❌ name and data (JSON list of training data) required."
        
        net = get_network(name)
        if not net:
            return f"❌ Network '{name}' not found."
        
        try:
            train_data = json.loads(data)
            # Convert to training format
            formatted_data = [(train_data[i], train_data[i + 1]) for i in range(len(train_data) - 1)]
            
            loss_history = net.train(formatted_data, epochs=epochs)
            return f"✅ Training complete. Final loss: {loss_history[-1]:.6f}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    if action == "predict":
        if not name or not data:
            return "❌ name and data (JSON list of inputs) required."
        
        net = get_network(name)
        if not net:
            return f"❌ Network '{name}' not found."
        
        try:
            inputs = json.loads(data)
            prediction = net.predict(inputs)
            return f"✅ Prediction: {prediction}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    if action == "nas":
        if not data:
            return "❌ data required for NAS."
        
        try:
            dataset = json.loads(data)
            # Assume input size = len(dataset[0]), output size = len(dataset[0][1])
            input_size = len(dataset[0][0])
            output_size = len(dataset[0][1])
            
            nas = get_nas(input_size, output_size)
            
            # Split into train/val
            split = int(0.8 * len(dataset))
            train = dataset[:split]
            val = dataset[split:]
            
            result = nas.search(train, val, num_trials=5, epochs_per_trial=20)
            
            lines = ["### NEURAL ARCHITECTURE SEARCH RESULTS", ""]
            lines.append(f"**Best Architecture**: {result['best_architecture']}")
            lines.append(f"**Best Score**: {result['best_score']:.6f}")
            lines.append("")
            lines.append("**Top 5 Results**:")
            for r in result["all_results"]:
                lines.append(f"  - {r['architecture']}: {r['score']:.6f}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    if action == "timeseries":
        if not data:
            return "❌ data (time series values) required."
        
        try:
            time_series = json.loads(data)
            predictor = get_predictor()
            
            result = predictor.train(time_series, epochs=epochs)
            
            # Predict next value
            next_val = predictor.predict_next(time_series)
            
            return f"{result}\n✅ Next predicted value: {next_val:.2f}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Neural Architecture...\n")
    
    # Test simple network
    print("--- Simple Network ---")
    net = SimpleNeuralNetwork([3, 5, 2])
    print(f"Created network with layers: {net.layer_sizes}")
    
    # Test training
    print("\n--- Training ---")
    train_data = [([i, i*2, i**2], [i*3, i*4]) for i in range(10)]
    loss_history = net.train(train_data, epochs=50, verbose=False)
    print(f"Final loss: {loss_history[-1]:.6f}")
    
    # Test prediction
    print("\n--- Prediction ---")
    prediction = net.predict([5, 10, 25])
    print(f"Prediction for [5, 10, 25]: {prediction}")
