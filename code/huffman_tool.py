import sys
import os
import json
import heapq
import pickle
from collections import Counter
from graphviz import Digraph
import networkx as nx
import matplotlib.pyplot as plt

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
RES_DIR = os.path.join(BASE_DIR, "results")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

class Node:
    """Node in the Huffman tree"""
    def __init__(self, char=None, freq=0, left=None, right=None):
        self.char = char
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCoding:
    def __init__(self):
        self.codes = {}
        self.reverse_codes = {}
        self.root = None

    def build_frequency_table(self, tokens):
        freq = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        return freq

    def build_huffman_tree(self, freq_table):
        heap = [Node(char=char, freq=freq) for char, freq in freq_table.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = Node(freq=left.freq + right.freq, left=left, right=right)
            heapq.heappush(heap, parent)
        return heap[0]


    def generate_codes(self, node, prefix="", output_file=None, freq_table=None):
        if node is None:
            return
    
        if node.char is not None:
            code = prefix if prefix else "0"
            self.codes[node.char] = code
            self.reverse_codes[code] = node.char
    
            # Write to file if path provided
            if output_file:
                with open(output_file, "a", encoding="utf-8") as f:
                    char_repr = node.char if node.char not in ['\n', '\t', ' '] else repr(node.char)
                    freq = freq_table[node.char] if freq_table else "?"
                    bits_used = freq * len(code)
                    f.write(f"{char_repr:<10} | {freq:<10} | {code:<10} | {bits_used}\n")
            return
    
        self.generate_codes(node.left, prefix + "0", output_file, freq_table)
        self.generate_codes(node.right, prefix + "1", output_file, freq_table)

        
    def encode(self, text, code_output_path=None, mode="char"):
        """
        Compress text using Huffman codes.
        mode: "char" for character-level (default), "word" for word-level compression.
        """
        if not text:
            return "", {}
    
        # Step 1 — Tokenize input based on mode
        if mode == "word":
            tokens = text.split()          # Split by whitespace into words
        else:
            tokens = list(text)            # Split into characters
    
        # Step 2 — Build frequency table and tree
        freq_table = self.build_frequency_table(tokens)
        self.root = self.build_huffman_tree(freq_table)
    
        # Step 3 — Prepare output file
        if code_output_path and os.path.exists(code_output_path):
            os.remove(code_output_path)
    
        # Step 4 — Write header info
        if code_output_path:
            with open(code_output_path, "w", encoding="utf-8") as f:
                level = "Word-Level" if mode == "word" else "Character-Level"
                f.write(f"Huffman Encoding Report ({level})\n")
                f.write(f"Original Text Length: {len(tokens)} tokens\n")
                f.write("Symbol Table:\n")
                f.write("Symbol | Frequency | Huffman Code | Bits Used\n")
                f.write("=" * 60 + "\n")
    
        # Step 5 — Generate codes & optionally write them
        self.generate_codes(self.root, output_file=code_output_path, freq_table=freq_table)
    
        # Step 6 — Compute compression statistics
        compressed_bits = sum(freq_table[sym] * len(self.codes[sym]) for sym in freq_table)
        original_bits = len(tokens) * (8 if mode == "char" else 16)  # Approx per-symbol bits
        compression_ratio = (1 - compressed_bits / original_bits) * 100
    
        # Step 7 — Write summary
        if code_output_path:
            with open(code_output_path, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"Original size (bits): {original_bits}\n")
                f.write(f"Compressed size (bits): {compressed_bits}\n")
                f.write(f"Compression ratio: {compression_ratio:.2f}%\n")
                f.write(f"Unique symbols: {len(freq_table)}\n")
                most_freq = max(freq_table, key=freq_table.get)
                least_freq = min(freq_table, key=freq_table.get)
                f.write(f"Most frequent symbol: '{most_freq}' ({freq_table[most_freq]} times)\n")
                f.write(f"Least frequent symbol: '{least_freq}' ({freq_table[least_freq]} times)\n")
    
        # Step 8 — Build final encoded string
        encoded = "".join(self.codes[sym] for sym in tokens)
        return encoded, freq_table

    
    def decode(self, encoded_text, freq_table, mode="char"):
        """Decode an encoded Huffman string using the frequency table."""
        if not encoded_text or not freq_table:
            return ""
    
        # Rebuild the Huffman tree
        self.root = self.build_huffman_tree(freq_table)
        self.generate_codes(self.root)
    
        decoded = []
        node = self.root
    
        for bit in encoded_text:
            # Defensive: skip invalid bits
            if node is None:
                node = self.root
                continue
    
            # Traverse tree
            node = node.left if bit == "0" else node.right
    
            # Leaf reached
            if node and node.char is not None:
                decoded.append(node.char)
                node = self.root
    
        return " ".join(decoded) if mode == "word" else "".join(decoded)

    
    def calculate_compression_ratio(self, original_size_bits, compressed_size_bits):
        """Return compression ratio as percentage saved.
        original_size_bits and compressed_size_bits are integers (bits)."""
        if original_size_bits <= 0:
            return 0.0
        return (1 - (compressed_size_bits / original_size_bits)) * 100
        

    def visualize_tree(self, root, filename="huffman_tree"):
        if not root:
            print("[WARNING] No Huffman tree found.")
            return
    
        dot = Digraph(comment="Huffman Binary Tree", format="png")
        dot.attr('node', shape='circle', style='filled', color='lightblue2', fontname="Helvetica")
    
        def add_nodes_edges(node, parent=None, edge_label=""):
            if not node:
                return
            node_label = f"{node.char if node.char else '*'}\n{node.freq}"
            dot.node(str(id(node)), node_label)
            if parent:
                dot.edge(str(id(parent)), str(id(node)), label=edge_label, color='red')
            add_nodes_edges(node.left, node, "0")
            add_nodes_edges(node.right, node, "1")
    
        add_nodes_edges(root)
        dot.attr(label="Huffman Binary Tree", fontsize="20", labelloc="t", fontname="Helvetica-Bold")
        output_path = dot.render(filename, cleanup=True)
        print(f"[INFO] Huffman tree saved as {output_path}")

    def pack_bits(self, bitstring):
        """Convert a string like '01001101...' into real bytes."""
        # Pad bitstring to make it divisible by 8
        padding = 8 - (len(bitstring) % 8)
        if padding != 8:
            bitstring += "0" * padding
    
        # Save padding info (needed during decode)
        return int(bitstring, 2).to_bytes(len(bitstring) // 8, byteorder='big'), padding

    def unpack_bits(self, byte_data, padding):
        bitstring = ''.join(f"{byte:08b}" for byte in byte_data)
        if padding:
            bitstring = bitstring[:-padding]
        return bitstring


# Helper functions for encoding to binary
def pad_encoded_text(encoded_text):
    extra_padding = 8 - len(encoded_text) % 8
    encoded_text += "0" * extra_padding
    padded_info = "{0:08b}".format(extra_padding)
    return padded_info + encoded_text


def remove_padding(padded_encoded_text):
    padded_info = padded_encoded_text[:8]
    extra_padding = int(padded_info, 2)
    encoded_text = padded_encoded_text[8:]
    return encoded_text[:-extra_padding]


def to_bytes(padded_encoded_text):
    b = bytearray()
    for i in range(0, len(padded_encoded_text), 8):
        byte = padded_encoded_text[i:i + 8]
        b.append(int(byte, 2))
    return bytes(b)



import os
import json

def compress_file(file_path, mode="char"):
    # Read original text
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    hc = HuffmanCoding()

    # Generate encoded bitstring and frequency table; write codes file
    codes_file = f"{file_path}_codes.txt"
    encoded, freq_table = hc.encode(text, code_output_path=codes_file, mode=mode)

    # Pack bits, write compressed file and metadata
    packed_bytes, padding = hc.pack_bits(encoded)
    compressed_filename = os.path.basename(file_path) + ".huff"

    # Determine where to save compressed and JSON (adjust as needed for your directory layout)
    compressed_path = os.path.join(os.path.dirname(file_path), "../output", compressed_filename)
    json_path = compressed_path + ".freq.json"

    # Ensure output directory exists
    output_dir = os.path.dirname(compressed_path)
    os.makedirs(output_dir, exist_ok=True)

    # Write compressed data
    with open(compressed_path, "wb") as f:
        f.write(bytes([padding]))
        f.write(packed_bytes)

    # Write frequency table JSON
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(freq_table, jf, indent=2)

    # Optional: generate tree image
    if hc.root:
        tree_path = os.path.join(output_dir, os.path.basename(file_path) + "_tree.png")
        try:
            hc.visualize_tree(hc.root, filename=tree_path)
        except Exception:
            pass  # skip if Graphviz isn't available

    # ── NEW: compute actual file sizes and append to codes file ──
    original_size_bytes = os.path.getsize(file_path)
    compressed_size_bytes = os.path.getsize(compressed_path)

    if original_size_bytes > 0:
        ratio = (1 - compressed_size_bytes / original_size_bytes) * 100
        with open(codes_file, "a", encoding="utf-8") as cf:
            cf.write(f"\nActual compression ratio (file sizes): {ratio:.2f}%\n")
            cf.write(f"Original size: {original_size_bytes} bytes, "
                     f"Compressed size: {compressed_size_bytes} bytes\n")

    print(f"[INFO] Compression complete. Compressed file saved to: {compressed_path}")



def decompress_file(file_path, mode="char"):
    hc = HuffmanCoding()

    with open(file_path, "rb") as f:
        padding = f.read(1)[0]
        packed_bytes = f.read()

    freq_path = file_path + ".freq.json"
    with open(freq_path, "r", encoding="utf-8") as f:
        freq_table = json.load(f)

    encoded = hc.unpack_bits(packed_bytes, padding)
    decoded = hc.decode(encoded, freq_table, mode=mode)

    # Determine output directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    output_dir = os.path.join(parent_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Base filename (remove .huff)
    filename = os.path.basename(file_path).replace(".huff", "")
    output_path = os.path.join(output_dir, f"uncompressed_{filename}.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(decoded)

    print(f"[INFO] Decompression complete using {mode}-level Huffman decoding.")
    print(f"[INFO] Output: {output_path}")




# Assuming you already have compress_file() and decompress_file() defined
# and both functions accept a `mode` argument (default "char")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python huffman_tool.py <file_path> <compress|decompress> [char|word]")
        sys.exit(1)

    input_filename = sys.argv[1]
    operation = sys.argv[2].lower()
    mode = sys.argv[3].lower() if len(sys.argv) == 4 else "char"

    if mode not in ("char", "word"):
        print("Invalid encoding mode. Use 'char' or 'word'.")
        sys.exit(1)

    # Construct full path: CURRENT_DIR/data/<file>
    if operation == "compress":
        file_path = os.path.join(DATA_DIR, input_filename)
    elif operation == "decompress":
        file_path = os.path.join(OUTPUT_DIR, input_filename)

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    if operation == "compress":
        compress_file(file_path, mode=mode)
    elif operation == "decompress":
        decompress_file(file_path, mode=mode)
    else:
        print("Invalid operation. Use 'compress' or 'decompress'.")
        sys.exit(1)

    