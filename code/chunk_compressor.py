import json
import os
from huffman_tool import HuffmanCoding  # use your existing class

PAGE_SIZE = 2000   # number of WORDS per chunk (not characters)

def chunk_book(file_path):
    # read text
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # tokenize into words for word-level Huffman
    words = text.split()

    # create chunks
    chunks = [words[i:i+PAGE_SIZE] for i in range(0, len(words), PAGE_SIZE)]

    compressed_file = file_path + ".huff"
    index_file = file_path + ".huff.freq.json"

    hc = HuffmanCoding()

    metadata = {
        "mode": "word",
        "page_size": PAGE_SIZE,
        "total_chunks": len(chunks),
        "chunks": []
    }

    with open(compressed_file, "wb") as out:
        offset = 0
        for i, chunk in enumerate(chunks):
            chunk_text = " ".join(chunk)

            encoded_bits, freq_table = hc.encode(chunk_text, mode="word")

            packed_bytes, padding = hc.pack_bits(encoded_bits)

            # write chunk bytes
            out.write(packed_bytes)

            metadata["chunks"].append({
                "offset": offset,
                "length": len(packed_bytes),
                "padding": padding,
                "freq": freq_table
            })

            offset += len(packed_bytes)

    # write index metadata
    with open(index_file, "w", encoding="utf-8") as jf:
        json.dump(metadata, jf, indent=2)

    print("Compression Done!")
    print("Generated:", compressed_file)
    print("Generated:", index_file)
