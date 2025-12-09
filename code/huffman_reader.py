import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from huffman_tool import HuffmanCoding


PAGE_WORD_COUNT = 250   # 250 words per page for book-like experience


class ChunkedHuffmanReader:

    def __init__(self, root):
        self.root = root
        self.root.title("Chunk-Based Huffman Book Reader")

        # Page-like frame
        self.page_frame = tk.Frame(root, bg="white", padx=30, pady=30)
        self.page_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget with big font
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

        self.pages = []
        self.current_page = 0


    def load_book(self):
        file_path = filedialog.askopenfilename(filetypes=[("Huffman files", "*.huff")])
        if not file_path:
            return

        index_file = file_path + ".freq.json"
        if not os.path.exists(index_file):
            messagebox.showerror("Error", ".freq.json not found")
            return

        with open(index_file, "r", encoding="utf-8") as jf:
            metadata = json.load(jf)

        # Validate chunk metadata
        if "chunks" not in metadata:
            messagebox.showerror("Error", "This .freq.json does not contain chunk metadata.")
            return

        with open(file_path, "rb") as f:
            data = f.read()

        hc = HuffmanCoding()
        all_words = []

        # Decode each chunk
        for chunk in metadata["chunks"]:
            offset = chunk["offset"]
            length = chunk["length"]
            padding = chunk["padding"]
            freq = chunk["freq"]

            chunk_bytes = data[offset: offset + length]

            bitstring = hc.unpack_bits(chunk_bytes, padding)
            decoded_text = hc.decode(bitstring, freq, mode="word")

            all_words.extend(decoded_text.split())

        # Split into smaller book pages
        self.pages = [
            all_words[i:i + PAGE_WORD_COUNT]
            for i in range(0, len(all_words), PAGE_WORD_COUNT)
        ]

        self.current_page = 0
        self.show_page()


    def show_page(self):
        self.text_area.delete(1.0, tk.END)

        total = len(self.pages)
        if total == 0:
            self.text_area.insert(tk.END, "[No content]")
            return

        # Clamp page index
        self.current_page = max(0, min(self.current_page, total - 1))

        header = f"Page {self.current_page + 1} / {total}\n\n"
        body = " ".join(self.pages[self.current_page])

        self.text_area.insert(tk.END, header)
        self.text_area.insert(tk.END, body)


    def next_page(self):
        self.current_page += 1
        self.show_page()


    def prev_page(self):
        self.current_page -= 1
        self.show_page()


    def exit_app(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChunkedHuffmanReader(root)
    root.mainloop()
