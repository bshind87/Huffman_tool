# Huffman Coding Compression & Book Reader

This project implements a complete Huffman‑coding‑based compression and decompression tool, with both **character‑level** and **word‑level** encoding.  It also provides a simple GUI reader for viewing compressed books page‑by‑page.

## Directory Structure
project_root/
├── code/ # Python source files (huffman_tool.py, chunk_compressor.py, readers, etc.)
├── data/ # Raw input files (e.g. .txt books to compress)
├── output/ # Compressed files (.huff), metadata JSON, tree PNGs
└── notebook/ # Jupyter notebooks (analysis, testing)

- **code/** holds all Python scripts.
- **data/** is the default location for uncompressed input files.
- **output/** is where compressed `.huff` files, their accompanying metadata, and tree visualisations are written.  
- **notebook/** contains any exploratory notebooks.

## Features

- ✅ **Lossless Huffman compression**: supports both character‑level and word‑level encoding.
- ✅ **Chunked compression**: splits large texts into chunks and compresses each chunk separately, enabling random‑access reading.
- ✅ **Huffman tree visualisation**: optional tree output as a PNG via Graphviz.
- ✅ **GUI book reader**: a Tkinter‑based reader that loads a compressed book and displays it page by page with adjustable page length and large fonts.
- ✅ **Command‑line interface**: simple CLI to compress and decompress files, or to create chunked files.

## Installation

1. **Clone the repository** and navigate into the project folder.
2. Ensure you have Python 3.7+ installed.
3. Install required Python packages:

   ```bash
   pip install -r requirements.txt

Usage

All commands below assume you are in the code/ directory or provide full paths. The script uses the parent directory as a base, so compressed output is always written to ../output.

1. Compress a text file
python huffman_tool.py data/book.txt compress char


Modes:

char → character‑level encoding

word → word‑level encoding (often yields better compression)

This creates:

output/book.txt.huff – the packed binary data

output/book.txt.huff.freq.json – metadata & frequencies

output/book.txt_tree.png (optional) – tree visualisation

A book.txt_codes.txt file is also generated alongside the input, containing the code table and final compression ratio calculated using the actual file sizes.

2. Decompress a .huff file
python huffman_tool.py output/book.txt.huff decompress char


This recreates the original text as output/uncompressed_book.txt.

3. Chunk‑based compression

For large books, compress in chunks (word‑level by default):

python chunk_compressor.py data/book.txt


This produces a single .huff file plus a JSON index that records offsets, paddings and frequency tables for each chunk. The corresponding reader will decode pages on demand.

4. Open the book reader

There are two readers included:

huffman_reader_simple.py – loads a .huff + simple frequency table, then paginates in memory.

chunked_huffman_reader.py – loads chunk‑based .huff + JSON index and decodes only the pages requested.

Example:

python huffman_reader_simple.py


then choose a compressed file (e.g. output/book.txt.huff) and browse using Next/Previous buttons. The page size and font size can be adjusted in the script.

Notes on Paths

huffman_tool.py uses os.path.abspath(__file__) to find its own directory and resolves ../data and ../output relative to it. When running from the code directory, you do not need to change directories manually; the script automatically writes into output/.

The compressed file sizes reported in _codes.txt are based on actual file sizes using os.path.getsize(); this yields a true compression ratio rather than an estimate (e.g. characters × 8).

Contributing / Future Work

Suggestions for improvement include:

Adding dark mode and font size controls to the reader.

Integrating chapter detection and search functionality.

Combining Huffman coding with other algorithms (e.g. run‑length encoding) for improved compression.

Packaging the GUI as an executable (e.g. using PyInstaller).
