"""
Revised Unified Test Suite (All test artifacts go into test_files/)
Compatible with:
- Direct HuffmanCoding encode/decode (char/word)
- Streaming hybrid compressor/decompressor (v3)
"""

import os
import json
from collections import Counter

# Import from your real tool
from huffman_tool import (
    HuffmanCoding,
    compress_file_streaming_hybrid,
    decompress_file_streaming_hybrid,
    tokenize_text,
)

# =============================================================================
# DIRECTORIES (NEW)
# =============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
TEST_DIR = os.path.join(BASE_DIR, "test")
os.makedirs(TEST_DIR, exist_ok=True)
TEST_INPUT_DIR = os.path.join(TEST_DIR, "input")
TEST_OUTPUT_DIR = os.path.join(TEST_DIR, "output")
TEST_TREE_DIR = os.path.join(TEST_DIR, "trees")

os.makedirs(TEST_INPUT_DIR, exist_ok=True)
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
os.makedirs(TEST_TREE_DIR, exist_ok=True)

# =============================================================================
# SAMPLE TEST CASES
# =============================================================================
DIRECT_TESTS = {
    "best_case":   "aaaaaaaaaaaaaaaabbbbbbbbccccccdddddd",
    "average_case": "Huffman coding is a data compression algorithm.",
    "worst_case":   "abcdefghiJKLMNO123456789!@#$%^&"
}

WORD_TESTS = {
    "best_case":    "hello hello hello world world test test test",
    "average_case": "Huffman coding compresses text by assigning shorter codes to common words.",
    "worst_case":   "each word here is completely unique in this example"
}

# =============================================================================
# HELPERS
# =============================================================================

def write_test_file(filename, text):
    """Writes file under test_files/input/"""
    path = os.path.join(TEST_INPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def visualize_tree(freq_table, prefix):
    """Visualize Huffman tree under test_files/output/trees/"""
    hc = HuffmanCoding()
    root = hc.build_huffman_tree(freq_table)
    save_path = os.path.join(TEST_TREE_DIR, f"{prefix}.png")
    hc.visualize_tree(root, save_path)
    return save_path


# =============================================================================
# PART 1 — DIRECT TESTS
# =============================================================================
def run_direct_tests():
    print("\n" + "=" * 80)
    print("DIRECT (In-Memory) HUFFMAN TESTS — CHAR MODE")
    print("=" * 80)

    for name, text in DIRECT_TESTS.items():
        print(f"\n--- CHAR TEST: {name} ---")
        hc = HuffmanCoding()

        # Build freq + tree manually
        tokens = tokenize_text(text, mode="char")
        freq_table = Counter(tokens)
        root = hc.build_huffman_tree(freq_table)
        hc.generate_codes(root)
        
        # Encode
        encoded = "".join(hc.codes[t] for t in tokens)
        
        # Decode using tree
        decoded = hc.decode_with_tree(encoded, mode="char")

        print(f"Encoded bits: {len(encoded)}")
        print(f"Decoded OK: {decoded == text}")

        visualize_tree(freq_table, f"tree_char_{name}")

    print("\n" + "=" * 80)
    print("DIRECT (In-Memory) HUFFMAN TESTS — WORD MODE")
    print("=" * 80)

    for name, text in WORD_TESTS.items():
        print(f"\n--- WORD TEST: {name} ---")
        hc = HuffmanCoding()

        tokens = tokenize_text(text, mode="word")
        freq_table = Counter(tokens)

        root = hc.build_huffman_tree(freq_table)
        hc.generate_codes(root)
        
        # Encode
        encoded = "".join(hc.codes[t] for t in tokens)
        
        # Decode using tree
        decoded = hc.decode_with_tree(encoded, mode="word")

        print(f"Encoded bits: {len(encoded)}")
        print(f"Decoded OK: {decoded == text}")

        visualize_tree(freq_table, f"tree_word_{name}")


# =============================================================================
# PART 2 — HYBRID STREAMING COMPRESSOR TESTS
# =============================================================================
def run_streaming_tests():
    print("\n" + "=" * 80)
    print("STREAMING HYBRID CHUNKED TESTS")
    print("=" * 80)

    # Prepare test text files
    char_file = write_test_file("stream_char.txt", DIRECT_TESTS["average_case"])
    word_file = write_test_file("stream_word.txt", WORD_TESTS["average_case"])

    tests = [
        ("stream_char.txt", char_file, "char"),
        ("stream_word.txt", word_file, "word"),
    ]

    for fname, path, mode in tests:
        print(f"\n--- STREAM TEST: {fname} (mode={mode}) ---")

        # COMPRESS
        compress_file_streaming_hybrid(path, mode=mode, target_chunk_bytes=250)

        huff_path = os.path.join("output", fname + ".huff")  # tool always writes here
        global_json = huff_path + ".global.json"
        chunk_json = huff_path + ".chunks.json"

        print(f"[INFO] huff file: {huff_path}")
        print(f"[INFO] global meta: {global_json}")
        print(f"[INFO] chunk meta: {chunk_json}")

        # Validate metadata
        if not os.path.exists(huff_path):
            print("[ERROR] Missing .huff output!")
            continue
        if not os.path.exists(global_json) or not os.path.exists(chunk_json):
            print("[ERROR] Missing metadata!")
            continue

        # DECOMPRESS
        output_path = decompress_file_streaming_hybrid(huff_path)

        with open(output_path, "r", encoding="utf-8") as f:
            decompressed = f.read()

        with open(path, "r", encoding="utf-8") as f:
            original = f.read()

        print(f"[SUCCESS] Round-trip OK: {decompressed == original}")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    run_direct_tests()
    run_streaming_tests()
    print("\nAll tests completed.")
