import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from huffman_tool import HuffmanCoding


PAGE_WORD_COUNT = 250   # 250 words per page (book-like experience)


class ChunkedHuffmanReader:

    def __init__(self, root):
        self.root = root
        self.root.title("Lazy Huffman Book Reader (v3)")

        # Page-like frame
        self.page_frame = tk.Frame(root, bg="white", padx=30, pady=30)
        self.page_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(
            self.page_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 18),
            bg="white",
            fg="black",
            padx=20,
            pady=20,
            height=22
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill=tk.X)

        tk.Button(btn_frame, text="Open Book", command=self.load_book).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Previous Page", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Next Page", command=self.next_page).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exit", command=self.exit_app,
                  bg="red", fg="white").pack(side=tk.RIGHT, padx=10)

        # Lazy decoding state
        self.chunks = []
        self.mode = "word"
        self.freq_table = None
        self.data = None
        self.total_words = 0
        self.words_per_chunk = []
        self.chunk_word_ranges = []
        self.page_count = 0

        # Cache: chunk_index -> decoded word list
        self.decoded_cache = {}

        self.current_page = 0

    # ------------------------------------------------------------------------------------
    # LOAD BOOK (lazy decoding: do NOT decode chunks now)
    # ------------------------------------------------------------------------------------
    def load_book(self):
        file_path = filedialog.askopenfilename(filetypes=[("Huffman files", "*.huff")])
        if not file_path:
            return

        # New v3 metadata files
        global_meta = file_path + ".global.json"
        chunks_meta = file_path + ".chunks.json"

        if not os.path.exists(global_meta):
            messagebox.showerror("Error", f"Global metadata missing:\n{global_meta}")
            return
        if not os.path.exists(chunks_meta):
            messagebox.showerror("Error", f"Chunk metadata missing:\n{chunks_meta}")
            return

        # Load global metadata
        with open(global_meta, "r", encoding="utf-8") as f:
            g = json.load(f)
        self.freq_table = g["freq"]
        self.mode = g.get("mode", "word")

        # Load chunk metadata
        with open(chunks_meta, "r", encoding="utf-8") as f:
            c = json.load(f)
        self.chunks = c["chunks"]

        # Load compressed file as bytes once
        with open(file_path, "rb") as f:
            self.data = f.read()

        # Build global Huffman tree once
        self.hc = HuffmanCoding()
        root = self.hc.build_huffman_tree(self.freq_table)
        self.hc.generate_codes(root)
        self.hc.root = root

        # Count tokens per chunk (for fast indexing)
        self.words_per_chunk = []
        for chunk in self.chunks:
            self.words_per_chunk.append(int(chunk["tokens"]))

        # Build prefix sums → map page → chunk index
        self.total_words = sum(self.words_per_chunk)

        # Compute total number of pages
        self.page_count = (self.total_words + PAGE_WORD_COUNT - 1) // PAGE_WORD_COUNT

        # Build word ranges per chunk
        self.chunk_word_ranges = []
        running = 0
        for count in self.words_per_chunk:
            start = running
            end = running + count
            self.chunk_word_ranges.append((start, end))
            running = end

        self.current_page = 0
        self.show_page()

    # ------------------------------------------------------------------------------------
    # Helper: find which chunk(s) contain the requested word range
    # ------------------------------------------------------------------------------------
    def find_chunks_for_page(self, page_index):
        start_word = page_index * PAGE_WORD_COUNT
        end_word = min(self.total_words, start_word + PAGE_WORD_COUNT)

        needed_chunks = []
        for i, (cstart, cend) in enumerate(self.chunk_word_ranges):
            if not (end_word <= cstart or start_word >= cend):
                needed_chunks.append(i)

        return needed_chunks, start_word, end_word

    # ------------------------------------------------------------------------------------
    # Helper: decode one chunk (cached)
    # ------------------------------------------------------------------------------------
    def decode_chunk(self, chunk_index):
        if chunk_index in self.decoded_cache:
            return self.decoded_cache[chunk_index]

        chunk = self.chunks[chunk_index]
        offset = chunk["offset"]
        length = chunk["length"]
        padding = chunk["padding"]

        chunk_bytes = self.data[offset: offset + length]
        bitstring = self.hc.unpack_bits(chunk_bytes, padding)
        decoded_text = self.hc.decode_with_tree(bitstring, mode=self.mode)

        words = decoded_text.split()

        self.decoded_cache[chunk_index] = words
        return words

    # ------------------------------------------------------------------------------------
    # SHOW PAGE (LAZY DECODE)
    # ------------------------------------------------------------------------------------
    def show_page(self):
        self.text_area.delete(1.0, tk.END)

        if self.page_count == 0:
            self.text_area.insert(tk.END, "[No content loaded]")
            return

        # Clamp page number
        self.current_page = max(0, min(self.current_page, self.page_count - 1))

        needed_chunks, start_word, end_word = self.find_chunks_for_page(self.current_page)

        all_words = []
        for ci in needed_chunks:
            all_words.extend(self.decode_chunk(ci))

        # Slice out only the words needed for this page
        words_on_page = all_words[start_word - self.chunk_word_ranges[needed_chunks[0]][0]:
                                 end_word - self.chunk_word_ranges[needed_chunks[0]][0]]

        header = f"Page {self.current_page + 1} / {self.page_count}\n\n"
        body = " ".join(words_on_page)

        self.text_area.insert(tk.END, header)
        self.text_area.insert(tk.END, body)

    # ------------------------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------------------------
    def next_page(self):
        self.current_page += 1
        self.show_page()

    def prev_page(self):
        self.current_page -= 1        # safe because show_page clamps bounds
        self.show_page()

    def exit_app(self):
        self.root.destroy()


# ----------------------------------------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ChunkedHuffmanReader(root)
    root.mainloop()
