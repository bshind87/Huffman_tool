import os
from huffman_tool import HuffmanCoding

# Create output directory
OUTPUT_DIR = "test_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample test cases for different data distributions
texts = {
    "best_case": "aaaaaaaaaaaaaaaabbbbbbbbccccccdddddd",
    "average_case": "Huffman coding is a data compression algorithm. It assigns shorter codes to more frequent characters.",
    "worst_case": "abcdefghiJKLMNO123456789!@#$%^&"
}

# Modes to test — character-level and word-level
modes = ["char", "word"]

for mode in modes:
    if mode == 'word':
        texts = {
                    "best_case": "hello how are you hello how are you hello how are you hello how are you hello how are you",
                    "average_case": "Huffman coding is a data compression algorithm. Huffman coding assigns shorter codes to more frequent data.",
                    "worst_case": "this is a worst case example for huffman coding algorithm where no any word being repeated, its used only ones"
}
    print(f"\n{'#' * 80}")
    print(f"RUNNING TESTS IN {mode.upper()}-LEVEL MODE")
    print(f"{'#' * 80}\n")

    for label, text in texts.items():
        print("\n" + "=" * 70)
        print(f"TEST CASE: {label.replace('_', ' ').title()}")
        print("=" * 70)

        hc = HuffmanCoding()

        # Define output files
        code_file = os.path.join(OUTPUT_DIR, f"huffman_codes_{label}_{mode}.txt")
        tree_file = os.path.join(OUTPUT_DIR, f"huffman_tree_{label}_{mode}.png")

        # Encode text
        encoded, freq_table = hc.encode(text, code_output_path=code_file, mode=mode)
        ratio = hc.calculate_compression_ratio(
            original_size_bits=len(text) * (8 if mode == "char" else 16),
            compressed_size_bits=len(encoded)
        )

        # Summary
        if mode == 'word':
            print(f"Original text length: {len(text.split())} symbols")
        else:
            print(f"Original text length: {len(text)} symbols")
        print(f"Original size: {len(text) * (8 if mode == 'char' else 16)} bits")
        print(f"Encoded size: {len(encoded)} bits")
        print(f"Compression ratio: {ratio:.2f}%")

        print("\nSymbol Frequencies:")
        for sym, freq in sorted(freq_table.items()):
            repr_sym = sym if sym not in ['\n', '\t', ' '] else repr(sym)
            print(f"  {repr_sym} : {freq}")

        print("\nHuffman Codes:")
        for sym, code in sorted(hc.codes.items()):
            repr_sym = sym if sym not in ['\n', '\t', ' '] else repr(sym)
            print(f"  {repr_sym} : {code}")

        # Decode and verify correctness
        decoded = hc.decode(encoded, freq_table, mode=mode)
        print(f"\nDecoding successful: {decoded == text}")

        # Visualize Huffman tree (Graphviz)
        try:
            hc.visualize_tree(hc.root, filename=tree_file)
            print(f"[INFO] Huffman tree saved to {tree_file}")
        except Exception as e:
            print(f"[WARNING] Tree visualization skipped: {e}")

        print(f"[INFO] Codes saved to: {code_file}")

print("\nAll Huffman test cases completed successfully!")
