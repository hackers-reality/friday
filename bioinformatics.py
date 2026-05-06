"""
Friday Bioinformatics - DNA/RNA analysis and genetic algorithms.
Protein folding, sequence alignment, genetic algorithms.
"""
from __future__ import annotations

import random
import math
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter


# ─── DNA Sequence ───────────────────────────#

class DNASequence:
    """Represents a DNA sequence."""
    
    VALID_BASES = {'A', 'T', 'G', 'C'}
    
    def __init__(self, sequence: str, name: str = "untitled"):
        self.name = name
        self.sequence = sequence.upper().replace(" ", "")
        self._validate()
        
    def _validate(self):
        """Validate DNA sequence."""
        invalid = set(self.sequence) - self.VALID_BASES
        if invalid:
            raise ValueError(f"Invalid bases: {invalid}")
        
    def reverse_complement(self) -> 'DNASequence':
        """Return reverse complement of sequence."""
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        rev_comp = ''.join(complement[b] for b in reversed(self.sequence))
        return DNASequence(rev_comp, f"{self.name}_revcomp")
    
    def transcribe(self) -> str:
        """Transcribe DNA to RNA (T -> U)."""
        return self.sequence.replace('T', 'U')
    
    def gc_content(self) -> float:
        """Calculate GC content percentage."""
        if not self.sequence:
            return 0.0
        gc_count = sum(1 for b in self.sequence if b in ('G', 'C'))
        return (gc_count / len(self.sequence)) * 100
    
    def find_motif(self, motifi: str) -> List[int]:
        """Find all positions of a motifi."""
        positions = []
        motifi = motifi.upper()
        start = 0
        while True:
            pos = self.sequence.find(motifi, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    def nucleotide_count(self) -> Dict[str, int]:
        """Count each nucleotide."""
        return dict(Counter(self.sequence))
    
    def to_fasta(self) -> str:
        """Convert to FASTA format."""
        return f">{self.name}\n{self.sequence}"
    
    @classmethod
    def from_fasta(cls, fasta: str) -> 'DNASequence':
        """Parse FASTA format."""
        lines = fasta.strip().split('\n')
        name = lines[0][1:]  # Remove '>'
        sequence = ''.join(lines[1:])
        return cls(sequence, name)
    
    def __len__(self):
        return len(self.sequence)
    
    def __str__(self):
        return f"DNA({self.name}: {self.sequence[:50]}...)" if len(self) > 50 else f"DNA({self.name}: {self.sequence})"


# ─── RNA Sequence ───────────────────────────#

class RNASequence(DNASequence):
    """Represents an RNA sequence."""
    
    VALID_BASES = {'A', 'U', 'G', 'C'}
    
    def __init__(self, sequence: str, name: str = "untitled"):
        self.name = name
        self.sequence = sequence.upper().replace(" ", "").replace("T", "U")
        self._validate()
        
    def transcribe(self) -> str:
        """RNA to DNA (U -> T)."""
        return self.sequence.replace('U', 'T')
    
    def translate(self) -> str:
        """Translate RNA to protein (simplified)."""
        codon_table = {
            'UUU': 'F', 'UUC': 'F', 'UUA': 'L', 'UUG': 'L',
            'UCU': 'S', 'UCC': 'S', 'UCA': 'S', 'UCG': 'S',
            'UAU': 'Y', 'UAC': 'Y', 'UGU': 'C', 'UGC': 'C',
            'UGG': 'W', 'CUU': 'L', 'CUC': 'L', 'CUA': 'L',
            'CUG': 'L', 'CCU': 'P', 'CCC': 'P', 'CCA': 'P',
            'CCG': 'P', 'CAU': 'H', 'CAC': 'H', 'CAA': 'Q',
            'CAG': 'Q', 'CGU': 'R', 'CGC': 'R', 'CGA': 'R',
            'CGG': 'R', 'AUU': 'I', 'AUC': 'I', 'AUA': 'I',
            'AUG': 'M', 'ACU': 'T', 'ACC': 'T', 'ACA': 'T',
            'ACG': 'T', 'AAU': 'N', 'AAC': 'N', 'AAA': 'K',
            'AAG': 'K', 'AGU': 'S', 'AGC': 'S', 'AGA': 'R',
            'AGG': 'R', 'GUU': 'V', 'GUC': 'V', 'GUA': 'V',
            'GUG': 'V', 'GCU': 'A', 'GCC': 'A', 'GCA': 'A',
            'GCG': 'A', 'GAU': 'D', 'GAC': 'D', 'GAA': 'E',
            'GAG': 'E', 'GGU': 'G', 'GGC': 'G', 'GGA': 'G',
            'GGG': 'G', 'UAA': '_', 'UAG': '_', 'UGA': '_',  # Stop codons
        }
        
        protein = []
        for i in range(0, len(self.sequence) - 2, 3):
            codon = self.sequence[i:i+3]
            amino = codon_table.get(codon, '?')
            if amino == '_':  # Stop
                break
            protein.append(amino)
        
        return ''.join(protein)


# ─── Sequence Alignment ───────────────────────────#

class SequenceAlignment:
    """Sequence alignment algorithms."""
    
    @staticmethod
    def needleman_wunsch(seq1: str, seq2: str, match: int = 1, mismatch: int = -1, gap: int = -1) -> Tuple[str, str, int]:
        """
        Global alignment (Needleman-Wunsch algorithm).
        Returns (aligned1, aligned2, score).
        """
        n, m = len(seq1), len(seq2)
        
        # Initialize score matrix
        score = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            score[i][0] = i * gap
        for j in range(1, m + 1):
            score[0][j] = j * gap
        
        # Fill matrix
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if seq1[i-1] == seq2[j-1]:
                    diagonal = score[i-1][j-1] + match
                else:
                    diagonal = score[i-1][j-1] + mismatch
                
                up = score[i-1][j] + gap
                left = score[i][j-1] + gap
                
                score[i][j] = max(diagonal, up, left)
        
        # Traceback
        aligned1, aligned2 = [], []
        i, j = n, m
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and (
                (seq1[i-1] == seq2[j-1] and score[i][j] == score[i-1][j-1] + match) or
                (seq1[i-1] != seq2[j-1] and score[i][j] == score[i-1][j-1] + mismatch)
            ):
                aligned1.append(seq1[i-1])
                aligned2.append(seq2[j-1])
                i -= 1
                j -= 1
            elif i > 0 and score[i][j] == score[i-1][j] + gap:
                aligned1.append(seq1[i-1])
                aligned2.append('-')
                i -= 1
            else:
                aligned1.append('-')
                aligned2.append(seq2[j-1])
                j -= 1
        
        return (''.join(reversed(aligned1)), ''.join(reversed(aligned2)), score[n][m])
    
    @staticmethod
    def smith_waterman(seq1: str, seq2: str, match: int = 1, mismatch: int = -1, gap: int = -1) -> Tuple[str, str, int]:
        """
        Local alignment (Smith-Waterman algorithm).
        Returns (aligned1, aligned2, score).
        """
        n, m = len(seq1), len(seq2)
        
        score = [[0] * (m + 1) for _ in range(n + 1)]
        max_score = 0
        max_pos = (0, 0)
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if seq1[i-1] == seq2[j-1]:
                    diagonal = score[i-1][j-1] + match
                else:
                    diagonal = score[i-1][j-1] + mismatch
                
                up = score[i-1][j] + gap
                left = score[i][j-1] + gap
                
                score[i][j] = max(0, diagonal, up, left)
                
                if score[i][j] > max_score:
                    max_score = score[i][j]
                    max_pos = (i, j)
        
        # Traceback from max position
        aligned1, aligned2 = [], []
        i, j = max_pos
        
        while i > 0 and j > 0 and score[i][j] > 0:
            if seq1[i-1] == seq2[j-1] and score[i][j] == score[i-1][j-1] + match:
                aligned1.append(seq1[i-1])
                aligned2.append(seq2[j-1])
                i -= 1
                j -= 1
            elif score[i][j] == score[i-1][j] + gap:
                aligned1.append(seq1[i-1])
                aligned2.append('-')
                i -= 1
            else:
                aligned1.append('-')
                aligned2.append(seq2[j-1])
                j -= 1
        
        return (''.join(reversed(aligned1)), ''.join(reversed(aligned2)), max_score


# ─── Genetic Algorithm ───────────────────────────#

class GeneticAlgorithm:
    """Generic genetic algorithm implementation."""
    
    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism: bool = True,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism
        self.population = []
        self.fitness_history = []
        
    def individual_repr(self) -> Any:
        """Generate random individual. Override this."""
        return [random.random() for _ in range(10)]
    
    def fitness_function(self, individual: Any) -> float:
        """Calculate fitness. Override this."""
        return sum(individual)
    
    def mutate(self, individual: Any) -> Any:
        """Mutate an individual."""
        mutated = individual[:]
        for i in range(len(mutated)):
            if random.random() < self.mutation_rate:
                mutated[i] = random.random()
        return mutated
    
    def crossover(self, parent1: Any, parent2: Any) -> Tuple[Any, Any]:
        """Crossover two parents to produce children."""
        if random.random() > self.crossover_rate:
            return parent1[:], parent2[:]
        
        # Single-point crossover
        point = random.randint(1, len(parent1) - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]
        return child1, child2
    
    def run(self, generations: int = 100) -> Tuple[Any, float]:
        """Run the genetic algorithm."""
        # Initialize population
        self.population = [self.individual_repr() for _ in range(self.population_size)]
        
        for gen in range(generations):
            # Calculate fitness
            fitness = [(ind, self.fitness_function(ind)) for ind in self.population]
            fitness.sort(key=lambda x: x[1], reverse=True)
            
            self.fitness_history.append(fitness[0][1])
            
            # Create new population
            new_population = []
            
            # Elitism: keep best individual
            if self.elitism and fitness:
                new_population.append(fitness[0][0])
            
            # Fill rest with crossover and mutation
            while len(new_population) < self.population_size:
                # Selection (tournament)
                candidates = random.sample(fitness, min(5, len(fitness)))
                parent1 = max(candidates, key=lambda x: x[1])[0]
                
                candidates = random.sample(fitness, min(5, len(fitness)))
                parent2 = max(candidates, key=lambda x: x[1])[0]
                
                child1, child2 = self.crossover(parent1, parent2)
                new_population.append(self.mutate(child1))
                if len(new_population) < self.population_size:
                    new_population.append(self.mutate(child2))
            
            self.population = new_population[:self.population_size]
        
        # Return best individual
        fitness = [(ind, self.fitness_function(ind)) for ind in self.population]
        fitness.sort(key=lambda x: x[1], reverse=True)
        return fitness[0][0], fitness[0][1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the run."""
        if not self.fitness_history:
            return {"error": "Not run yet"}
        
        return {
            "generations": len(self.fitness_history),
            "best_fitness": self.fitness_history[-1],
            "improvement": self.fitness_history[-1] - self.fitness_history[0],
            "history": self.fitness_history[:10],  # First 10
        }


# ─── Protein Folding (Simplified) ───────────────────────────#

class ProteinFolding:
    """Simplified protein folding (2D HP model)."""
    
    def __init__(self, sequence: str):
        self.sequence = sequence.upper()
        self.hydrophobic = {'A', 'I', 'L', 'M', 'F', 'W', 'Y', 'V'}  # Simplified
        self.structure = []  # List of (x, y) coordinates
        
    def fold(self) -> float:
        """Fold protein to minimize energy (simplified)."""
        # Start at origin
        self.structure = [(0, 0)]
        energy = 0
        
        for i in range(1, len(self.sequence)):
            # Simple fold: alternate directions
            if i % 2 == 0:
                next_pos = (self.structure[-1][0] + 1, self.structure[-1][1])
            else:
                next_pos = (self.structure[-1][0], self.structure[-1][1] + 1)
            
            self.structure.append(next_pos)
            
            # Check for hydrophobic contacts
            if self.sequence[i] in self.hydrophobic:
                for j in range(i-2):  # Skip adjacent
                    if self.sequence[j] in self.hydrophobic:
                        dist = abs(self.structure[i][0] - self.structure[j][0]) + \
                               abs(self.structure[i][1] - self.structure[j][1])
                        if dist == 1:  # Adjacent in grid
                            energy -= 1  # Favorable
        
        return energy
    
    def to_string(self) -> str:
        """Visualize 2D structure."""
        if not self.structure:
            return "Not folded yet"
        
        # Find bounds
        min_x = min(p[0] for p in self.structure)
        max_x = max(p[0] for p in self.structure)
        min_y = min(p[1] for p in self.structure)
        max_y = max(p[1] for p in self.structure)
        
        # Create grid
        height = max_y - min_y + 1
        width = max_x - min_x + 1
        grid = [[' '] * width for _ in range(height)]
        
        # Place residues
        for i, (x, y) in enumerate(self.structure):
            grid_y = y - min_y
            grid_x = x - min_x
            if 0 <= grid_y < height and 0 <= grid_x < width:
                grid[grid_y][grid_x] = self.sequence[i]
        
        return '\n'.join(''.join(row) for row in grid)


# ─── Tool Function for Friday ────────────────────────────#

def bioinfo_tool(
    action: str = "analyze",
    sequence: str = None,
    sequence2: str = None,
    algorithm: str = "global",
) -> str:
    """
    Friday tool for bioinformatics.
    Actions: analyze, align, genetic, fold, translate
    """
    if action == "analyze":
        if not sequence:
            return "❌ Sequence required."
        
        dna = DNASequence(sequence)
        lines = [f"### DNA ANALYSIS: {dna.name}", ""]
        lines.append(f"**Length**: {len(dna)} bp")
        lines.append(f"**GC Content**: {dna.gc_content():.1f}%")
        lines.append(f"**Nucleotide Count**: {dna.nucleotide_count()}")
        lines.append(f"**Sequence**: {dna.sequence[:50]}..." if len(dna) > 50 else f"**Sequence**: {dna.sequence}")
        return "\n".join(lines)
    
    if action == "align":
        if not sequence or not sequence2:
            return "❌ Two sequences required."
        
        if algorithm == "global":
            aligned1, aligned2, score = SequenceAlignment.needleman_wunsch(sequence, sequence2)
        elif algorithm == "local":
            aligned1, aligned2, score = SequenceAlignment.smith_waterman(sequence, sequence2)
        else:
            return f"❌ Unknown algorithm: {algorithm}"
        
        lines = [f"### SEQUENCE ALIGNMENT ({algorithm.upper()})", ""]
        lines.append(f"**Score**: {score}")
        lines.append("")
        lines.append(f"**Sequence 1**: {aligned1}")
        lines.append(f"**Sequence 2**: {aligned2}")
        return "\n".join(lines)
    
    if action == "genetic":
        if not sequence:
            return "❌ Fitness function not defined. Use custom implementation."
        
        # Simple example: maximize number of 'A's
        ga = GeneticAlgorithm(population_size=50, generations=100)
        
        # Override for this specific problem
        target_length = len(sequence)
        ga.individual_repr = lambda: ''.join(random.choice(['A', 'T', 'G', 'C']) for _ in range(target_length))
        ga.fitness_function = lambda ind: sum(1 for c in ind if c == 'A')
        
        best, fitness = ga.run(generations=50)
        stats = ga.get_statistics()
        
        lines = ["### GENETIC ALGORITHM", ""]
        lines.append(f"**Best Individual**: {''.join(best)}")
        lines.append(f"**Fitness**: {fitness} / {target_length}")
        lines.append(f"**Generations**: {stats['generations']}")
        lines.append(f"**Improvement**: {stats['improvement']}")
        return "\n".join(lines)
    
    if action == "fold":
        if not sequence:
            return "❌ Protein sequence required."
        
        protein = ProteinFolding(sequence)
        energy = protein.fold()
        
        lines = ["### PROTEIN FOLDING (2D HP Model)", ""]
        lines.append(f"**Sequence**: {sequence}")
        lines.append(f"**Energy**: {energy} (lower is better)")
        lines.append("")
        lines.append("**2D Structure**:")
        lines.append(protein.to_string())
        return "\n".join(lines)
    
    if action == "translate":
        if not sequence:
            return "❌ RNA sequence required."
        
        rna = RNASequence(sequence)
        protein = rna.translate()
        
        lines = ["### TRANSLATION", ""]
        lines.append(f"**RNA**: {sequence}")
        lines.append(f"**Protein**: {protein}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Bioinformatics...\n")
    
    # Test DNA analysis
    print("--- DNA Analysis ---")
    print(bioinfo_tool("analyze", sequence="ATGCGTACGTAGCTAGCTGAC"))
    
    # Test alignment
    print("\n--- Sequence Alignment ---")
    print(bioinfo_tool("align", sequence="GATTACA", sequence2="GCATACA"))
    
    # Test translation
    print("\n--- Translation ----")
    print(bioinfo_tool("translate", sequence="AUGGCCAUGGCGCCCAGAACUGAGA"))
