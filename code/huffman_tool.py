#!/usr/bin/env python3
"""
Huffman Tool v3.0
------------------
Features:
- Streaming global frequency table (char or word mode).
- One global Huffman codebook for the entire file.
- Hybrid chunking: compressed file split into chunks by size, but in word mode
  we prefer to cut on sentence boundaries.
- No per-chunk frequency tables; metadata is:
    <file>.huff.global.json  -> single global frequency table + mode
    <file>.huff.chunks.json  -> list of {offset, length, padding, tokens}

This avoids loading the entire book into memory in word-level mode while also
avoiding huge duplicated frequency tables in the metadata.
"""

import sys
import os
import json
import heapq
import re
from collections import Counter

from graphviz import Digraph

# ====== PATHS ======
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ====== TOKENIZATION ======
# Same semantics as your previous version.
TOKEN_PATTERN = re.compile(
    r"[A-Za-z_]+"      # words
    r"|[0-9]"          # individual digits
    r"|[^\w\s]"        # punctuation/symbols
    r"|\s",            # whitespace (space, tab, newline, etc.)
    flags=re.UNICODE
)


def tokenize_text(text, mode="char"):
    """Non-streaming tokenizer (kept for compatibility / tests)."""
    if mode == "word":
        return TOKEN_PATTERN.findall(text)
    else:
        return list(text)


def stream_tokens_from_file(file_path, mode="char", chunk_size=1024 * 1024):
    """
    Streaming tokenizer over a file.
    Yields tokens one by one without loading entire file in memory.

    - For char mode: yields individual characters.
    - For word mode: yields tokens from TOKEN_PATTERN and
      safely handles alphabetic words that may span chunk boundaries.
    """
    if mode == "char":
        with open(file_path, "r", encoding="utf-8") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                for ch in chunk:
                    yield ch
    else:
        buffer = ""
        with open(file_path, "r", encoding="utf-8") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                buffer += chunk
                tokens = TOKEN_PATTERN.findall(buffer)

                # Only alphabetic words can be partially cut across chunks.
                if buffer and buffer[-1].isalpha():
                    if tokens:
                        *complete_tokens, last_token = tokens
                    else:
                        complete_tokens, last_token = [], buffer

                    for t in complete_tokens:
                        yield t

                    buffer = last_token
                else:
                    for t in tokens:
                        yield t
                    buffer = ""

        if buffer:
            for t in TOKEN_PATTERN.findall(buffer):
                yield t


def build_frequency_table_streaming(file_path, mode="char"):
    """
    Build a frequency table by streaming through the file.
    Does not load entire text into memory.
    """
    freq = {}
    total = 0
    for token in stream_tokens_from_file(file_path, mode=mode):
        freq[token] = freq.get(token, 0) + 1
        total += 1
    return freq, total


# ====== HUFFMAN CORE ======
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

    """
    def build_frequency_table(self, tokens):
        freq = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        return freq
    """
    def build_huffman_tree(self, freq_table):
        heap = [Node(char=char, freq=freq) for char, freq in freq_table.items()]
        heapq.heapify(heap)
        if not heap:
            return None
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

            if output_file:
                with open(output_file, "a", encoding="utf-8") as f:
                    char_repr = (
                        node.char if node.char not in ['\n', '\t', ' ']
                        else repr(node.char)
                    )
                    freq = freq_table[node.char] if freq_table else "?"
                    bits_used = freq * len(code)
                    f.write(f"{char_repr:<20} | {freq:<10} | {code:<20} | {bits_used}\n")
            return

        self.generate_codes(node.left, prefix + "0", output_file, freq_table)
        self.generate_codes(node.right, prefix + "1", output_file, freq_table)

    
    # New: decode using an already-built tree/codes (for chunked/global decode)
    def decode_with_tree(self, encoded_text, mode="char"):
        """
        Decode using self.root / self.codes assumed already initialized.
        freq_table is not needed here; used for repeated chunk decoding with same tree.
        """
        if not encoded_text or self.root is None:
            return ""

        decoded_tokens = []
        node = self.root

        for bit in encoded_text:
            node = node.left if bit == "0" else node.right
            if node and node.char is not None:
                decoded_tokens.append(node.char)
                node = self.root

        return "".join(decoded_tokens)

    
    def unpack_bits(self, byte_data, padding):
        bitstring = ''.join(f"{byte:08b}" for byte in byte_data)
        if padding:
            bitstring = bitstring[:-padding]
        return bitstring

    
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


# ====== STREAMING GLOBAL-CODEBOOK COMPRESSOR (HYBRID CHUNKS) ======

def compress_file_streaming_hybrid(file_path, mode="char",
                                   target_chunk_bytes=512 * 1024):
    """
    Two-pass streaming compression with one global Huffman codebook
    and chunk metadata based only on offsets/lengths.

    1) First pass: build global freq table by streaming tokens.
    2) Build one Huffman tree + codes.
    3) Second pass: re-stream tokens, encode using global codes,
       and write compressed bytes split into hybrid chunks.

    Metadata:
        - <file>.huff.global.json : {"version":3, "mode":..., "freq":..., "total_tokens":...}
        - <file>.huff.chunks.json : {"version":3, "mode":..., "target_chunk_bytes":..., "chunks":[...]}
    """
    if mode not in ("char", "word"):
        raise ValueError("mode must be 'char' or 'word'")

    print(f"[INFO] Building global frequency table for: {file_path}")
    freq_table, total_tokens = build_frequency_table_streaming(file_path, mode=mode)
    if not freq_table:
        print("[ERROR] Empty file or no tokens found.")
        return

    hc = HuffmanCoding()
    print("[INFO] Building global Huffman tree...")
    root = hc.build_huffman_tree(freq_table)
    hc.generate_codes(root)
    hc.root = root  # store for reuse

    # Prepare output paths
    base_name = os.path.basename(file_path)
    compressed_filename = base_name + ".huff"
    compressed_path = os.path.join(OUTPUT_DIR, compressed_filename)
    global_meta_path = compressed_path + ".global.json"
    chunks_meta_path = compressed_path + ".chunks.json"

    # -------------------------------------------------------------------------
    # NEW: Write code.txt report (global codes, frequencies, bits used)
    # -------------------------------------------------------------------------
    report_name = os.path.splitext(base_name)[0] + "_codes.txt"
    report_path = os.path.join(DATA_DIR, report_name)

    print(f"[INFO] Writing code report: {report_path}")

    if os.path.exists(report_path):
        os.remove(report_path)

    total_bits = 0

    with open(report_path, "w", encoding="utf-8") as rf:
        level = "Word-Level" if mode == "word" else "Character-Level"
        rf.write(f"Huffman Encoding Report ({level})\n")
        rf.write(f"Total Tokens: {total_tokens}\n")
        rf.write(f"Unique Symbols: {len(freq_table)}\n")
        rf.write("=" * 80 + "\n")
        rf.write(f"{'Symbol':<20} | {'Frequency':<10} | {'Code':<20} | Bits Used\n")
        rf.write("-" * 80 + "\n")

        for sym, freq in sorted(freq_table.items(), key=lambda x: -x[1]):
            code = hc.codes[sym]
            bits_used = freq * len(code)
            total_bits += bits_used

            repr_sym = sym if sym not in [" ", "\n", "\t"] else repr(sym)

            rf.write(f"{repr_sym:<20} | {freq:<10} | {code:<20} | {bits_used}\n")

        # estimated original size
        original_bits = total_tokens * (8 if mode == "char" else 16)
        compression_ratio = (1 - total_bits / original_bits) * 100

        rf.write("\n" + "=" * 80 + "\n")
        rf.write(f"Original size (symbol-based bits): {original_bits}\n")
        rf.write(f"Compressed size (symbol-based bits): {total_bits}\n")
        rf.write(f"Estimated compression ratio: {compression_ratio:.2f}%\n")

    print(f"[INFO] Code report saved to: {report_path}")


    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write global frequency metadata ONCE
    print(f"[INFO] Writing global metadata: {global_meta_path}")
    global_meta = {
        "version": 3,
        "mode": mode,
        "total_tokens": total_tokens,
        "unique_symbols": len(freq_table),
        "freq": freq_table
    }
    with open(global_meta_path, "w", encoding="utf-8") as jf:
        json.dump(global_meta, jf, indent=2, ensure_ascii=False)

    # Second pass: encode + chunk
    print("[INFO] Starting second pass: encoding with global codes...")
    chunks_meta = {
        "version": 3,
        "mode": mode,
        "target_chunk_bytes": target_chunk_bytes,
        "chunks": []
    }

    sentence_boundaries = {".", "!", "?", "\n"}
    chunk_index = 0

    with open(compressed_path, "wb") as cf:
        bit_buffer = ""
        chunk_start_offset = cf.tell()
        bytes_written_chunk = 0
        tokens_in_chunk = 0
        total_tokens_seen = 0

        # To help hybrid splitting, remember previous token if needed
        prev_token = None

        for token in stream_tokens_from_file(file_path, mode=mode):
            code = hc.codes[token]
            bit_buffer += code
            tokens_in_chunk += 1
            total_tokens_seen += 1

            # Flush whole bytes
            while len(bit_buffer) >= 8:
                byte_bits = bit_buffer[:8]
                cf.write(int(byte_bits, 2).to_bytes(1, byteorder="big"))
                bit_buffer = bit_buffer[8:]
                bytes_written_chunk += 1

            # Decide if we should close this chunk (hybrid logic)
            good_boundary = True
            if mode == "word":
                # Prefer to cut after sentence-like boundaries
                if token in sentence_boundaries:
                    good_boundary = True
                else:
                    good_boundary = False

            # If we've hit or exceeded target size and boundary is good (or we're in char mode),
            # finalize this chunk.
            if bytes_written_chunk >= target_chunk_bytes and (mode == "char" or good_boundary):
                padding = (8 - (len(bit_buffer) % 8)) % 8
                if padding:
                    bit_buffer += "0" * padding
                    while len(bit_buffer) >= 8:
                        byte_bits = bit_buffer[:8]
                        cf.write(int(byte_bits, 2).to_bytes(1, byteorder="big"))
                        bit_buffer = bit_buffer[8:]
                        bytes_written_chunk += 1

                chunk_length = bytes_written_chunk
                chunks_meta["chunks"].append({
                    "index": chunk_index,
                    "offset": chunk_start_offset,
                    "length": chunk_length,
                    "padding": padding,
                    "tokens": tokens_in_chunk
                })

                chunk_index += 1
                chunk_start_offset = cf.tell()
                bytes_written_chunk = 0
                tokens_in_chunk = 0
                bit_buffer = ""

            prev_token = token

        # EOF: flush remaining bits & finalize last chunk
        if bit_buffer or bytes_written_chunk > 0 or tokens_in_chunk > 0:
            padding = (8 - (len(bit_buffer) % 8)) % 8
            if padding:
                bit_buffer += "0" * padding
            while len(bit_buffer) >= 8:
                byte_bits = bit_buffer[:8]
                cf.write(int(byte_bits, 2).to_bytes(1, byteorder="big"))
                bit_buffer = bit_buffer[8:]
                bytes_written_chunk += 1

            if bytes_written_chunk > 0 or tokens_in_chunk > 0:
                chunk_length = bytes_written_chunk
                chunks_meta["chunks"].append({
                    "index": chunk_index,
                    "offset": chunk_start_offset,
                    "length": chunk_length,
                    "padding": padding,
                    "tokens": tokens_in_chunk
                })

    chunks_meta["total_chunks"] = len(chunks_meta["chunks"])
    chunks_meta["total_tokens"] = total_tokens_seen

    print(f"[INFO] Writing chunk metadata: {chunks_meta_path}")
    with open(chunks_meta_path, "w", encoding="utf-8") as jf:
        json.dump(chunks_meta, jf, indent=2)

    # File-size-based compression ratio
    original_size_bytes = os.path.getsize(file_path)
    compressed_size_bytes = os.path.getsize(compressed_path)
    if original_size_bytes > 0:
        ratio = (1 - compressed_size_bytes / original_size_bytes) * 100
        print(f"[INFO] Actual compression ratio (file sizes): {ratio:.2f}%")
        print(f"       Original size:   {original_size_bytes} bytes")
        print(f"       Compressed size: {compressed_size_bytes} bytes")

    print("[INFO] Streaming hybrid compression complete.")

    tree_name = os.path.splitext(base_name)[0] + "_tree"
    report_path = os.path.join(OUTPUT_DIR, tree_name)
    hc.visualize_tree(root, report_path)

def decompress_file_streaming_hybrid(huff_path):
    """
    Decompress a .huff file created by compress_file_streaming_hybrid().
    Uses:
        <huff_path>.global.json  -- global freq table.
        <huff_path>.chunks.json  -- chunk offsets, lengths, paddings.
    Writes:
        output/uncompressed_<basename>.txt
    """
    global_meta_path = huff_path + ".global.json"
    chunks_meta_path = huff_path + ".chunks.json"

    if not os.path.exists(global_meta_path):
        raise FileNotFoundError(f"Global metadata not found: {global_meta_path}")
    if not os.path.exists(chunks_meta_path):
        raise FileNotFoundError(f"Chunks metadata not found: {chunks_meta_path}")

    with open(global_meta_path, "r", encoding="utf-8") as jf:
        global_meta = json.load(jf)

    with open(chunks_meta_path, "r", encoding="utf-8") as jf:
        chunks_meta = json.load(jf)

    mode = global_meta.get("mode", "char")
    freq_table = global_meta["freq"]
    chunks = chunks_meta["chunks"]

    print(f"[INFO] Decompressing {huff_path}")
    print(f"       Mode: {mode}, Chunks: {len(chunks)}")

    with open(huff_path, "rb") as cf:
        data = cf.read()

    hc = HuffmanCoding()
    root = hc.build_huffman_tree(freq_table)
    hc.generate_codes(root)
    hc.root = root

    parts = []
    for chunk in chunks:
        offset = chunk["offset"]
        length = chunk["length"]
        padding = chunk["padding"]

        chunk_bytes = data[offset: offset + length]
        bitstring = hc.unpack_bits(chunk_bytes, padding)
        decoded_text = hc.decode_with_tree(bitstring, mode=mode)
        parts.append(decoded_text)

    full_text = "".join(parts)

    base_name = os.path.basename(huff_path)
    if base_name.endswith(".huff"):
        base_name = base_name[:-5]

    output_path = os.path.join(OUTPUT_DIR, f"uncompressed_{base_name}.txt")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"[INFO] Decompression complete. Output: {output_path}")
    return output_path


# ====== CLI ENTRYPOINT ======

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print("Usage:")
        print("  python huffman_tool.py <input_filename> compress [char|word] [target_chunk_kb]")
        print("  python huffman_tool.py <huff_filename> decompress")
        print()
        print("Examples:")
        print("  python huffman_tool.py book.txt compress word 512")
        print("  python huffman_tool.py book.txt.huff decompress")
        sys.exit(1)

    op = sys.argv[2].lower()

    if op == "compress":
        mode = sys.argv[3].lower() if len(sys.argv) >= 4 else "char"
        target_kb = int(sys.argv[4]) if len(sys.argv) == 5 else 512
        target_bytes = target_kb * 1024

        input_filename = sys.argv[1]
        file_path = os.path.join(DATA_DIR, input_filename)
        if not os.path.exists(file_path):
            print(f"Error: Input file not found: {file_path}")
            sys.exit(1)

        compress_file_streaming_hybrid(file_path, mode=mode,
                                       target_chunk_bytes=target_bytes)

    elif op == "decompress":
        huff_filename = sys.argv[1]
        huff_path = os.path.join(OUTPUT_DIR, huff_filename)
        if not os.path.exists(huff_path):
            print(f"Error: .huff file not found in output/: {huff_path}")
            sys.exit(1)
        decompress_file_streaming_hybrid(huff_path)

    else:
        print("Invalid operation. Use 'compress' or 'decompress'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
