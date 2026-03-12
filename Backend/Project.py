from sentence_transformers import SentenceTransformer
import faiss, fitz, os, pickle, re, polars as pl
from pathlib import Path

class ProjectContext():
    model_name: str = "all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    INDEX_FILE = "index.faiss"
    
    #Añadir creación de folders (DIR)
    def __init__(self, NAME: str = "Proyect1"):
        self.NAME = NAME

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200):
        """Divide un texto en chunks con overlap"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def GENERATE_RAG(self) -> None:
        print("Generando embeddings y creando índice FAISS...")
        texts = []
        file_names = []

        directory = Path(".", self.NAME, "plaintext")
        index_file = Path(".", self.NAME, ProjectContext.INDEX_FILE)
        filenames_file = Path(".", self.NAME, "file_names.pkl")
        texts_file = Path(".", self.NAME, "texts.pkl")

        # Leer archivos Markdown y crear chunks
        for file in directory.glob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = self._chunk_text(content, chunk_size=1000, overlap=200)
            texts.extend(chunks)
            file_names.extend([file.name] * len(chunks))  # Asociar cada chunk al archivo original

        # Crear embeddings
        embeddings = ProjectContext.model.encode(texts, show_progress_bar=True)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        faiss.write_index(index, str(index_file))  # FAISS necesita str

        # Guardar textos y nombres
        with open(filenames_file, "wb") as f:
            pickle.dump(file_names, f)
        with open(texts_file, "wb") as f:
            pickle.dump(texts, f)

        print(f"RAG generado con {len(texts)} chunks.")
        
    
    #region Ingest PDF
    @staticmethod
    def __pdf_to_markdown(pdf_path: Path) -> None:
        def limpiar_texto(texto):
            texto = texto.replace("", "")
            texto = re.sub(r'^\d+/\d+\s*$', '', texto, flags=re.MULTILINE)
            texto = re.sub(r'(?<![.:])\n', ' ', texto)
            texto = re.sub(r'[ ]{2,}', ' ', texto)
            return texto.strip()

        if not os.path.exists(pdf_path):
            print(f"Error: El archivo '{pdf_path}' no existe.")
            return

        try:
            doc = fitz.open(pdf_path)
            markdown_content = []

            for page in doc:
                text = page.get_text("text")
                text = limpiar_texto(text)
                markdown_content.append(text)

            doc.close()

            with open(pdf_path.with_suffix(".md"), "w", encoding="utf-8") as f:
                f.write("\n".join(markdown_content))

            if os.path.exists(pdf_path.with_suffix(".md")):
                os.remove(pdf_path)
                #print(f"PDF original eliminado: {pdf_path}")

        except Exception as e:
            print(e)
            
        pass

    def Ingest_PDF(self, doc_name: str) -> None:
        self.__pdf_to_markdown(Path(".", self.NAME, "plaintext", doc_name))
        
    #endregion
    
    #region Ingest Excel
    @staticmethod
    def __excel_to_markdown(path: Path) -> None:
        """Convert an Excel file to markdown tables using Polars."""
        
        def df_to_md(df: pl.DataFrame) -> str:
            """Convert a Polars DataFrame to a markdown table."""
            cols = df.columns
            header = "| " + " | ".join(cols) + " |"
            sep = "| " + " | ".join(["---"] * len(cols)) + " |"

            rows = []
            for row in df.iter_rows():
                rows.append("| " + " | ".join([str(x) if x is not None else "" for x in row]) + " |")

            return "\n".join([header, sep] + rows)

        sheets = pl.read_excel(path, sheet_id=0, engine="xlsx2csv", sheet_name=None)
        out = [f"# {os.path.basename(path)}\n"]
        for name, df in sheets.items():
            out.append(f"## Sheet: {name}\n")
            out.append(df_to_md(df.fill_null("")))
        text = "\n\n".join(out)
        new_path = ".".join(path.split(".")[:-1]) + ".md"
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(text)
        pass
    
    def Ingest_Excel(self, doc_name: str) -> None:
        self.__excel_to_markdown(Path(".", self.NAME, "plaintext", doc_name))
        
    #endregion
