# IntGathering x RAG: BlazingDocs

**BlazingDocs** is a FastAPI-based project designed to streamline **document-driven intelligence gathering** using a **Retrieval-Augmented Generation (RAG)** pipeline. It enables users to upload documents, index them into a knowledge base, and define **collections of queries** that can automatically extract relevant information on demand.

The goal of the project is to provide a fast and flexible system for **structured information extraction from large document sets**, making it useful for research, intelligence analysis, knowledge management, and automated reporting workflows.

---

## Features

- **Document Upload & Indexing**
  - Upload documents to the system through the API.
  - Automatically process and embed documents into the RAG knowledge base.

- **RAG-Based Retrieval**
  - Retrieve relevant document fragments using semantic search.
  - Combine retrieval with LLM reasoning to generate contextual answers.

- **Query Collections**
  - Create **collections**, which are predefined sets of queries.
  - Collections act as reusable intelligence-gathering templates.

- **On-Demand Information Gathering**
  - Execute a collection to automatically run all its queries against the document base.
  - Aggregate the results into structured outputs.

- **FastAPI Backend**
  - Fully asynchronous API.
  - Built-in OpenAPI documentation via Swagger UI.

---

## Architecture Overview

The system follows a **Retrieval-Augmented Generation (RAG)** workflow:

1. **Document Ingestion**
   - Users upload documents to the system.
   - Documents are parsed, chunked, and embedded.

2. **Vector Storage**
   - Embeddings are stored in a vector database for semantic retrieval.

3. **Query Collections**
   - Users define collections containing multiple queries.

4. **Execution**
   - When a collection is executed, each query retrieves relevant document chunks and a yes/no answer based on a criterion (confidence).



---

## Example Workflow
1. Upload Documents

Upload one or more documents to populate the knowledge base.

2. Create a Collection

Define a collection containing queries such as:
* "What are the key findings in this report?"
* "List the organizations mentioned."
* "Summarize the main risks discussed."

3. Execute the Collection

Run the collection to automatically extract the requested information from the document set.

## Use Cases

* Intelligence and OSINT workflows
* Research document analysis
* Knowledge base querying
* Automated report generation
* Compliance and risk review

## Future Improvements
In order planned releases, the features I'm working on are: 

* Telegram integration through custom bot for accessing information through mobile devices.
* Web interface for document management (electron or other front-end framework)
* Update on documentation and consolidate version 1.0
* Scheduling collections for periodic execution
* Advanced document parsing pipelines


## Contributing

Contributions are welcome. Feel free to open issues, suggest improvements, or submit pull requests.

## License

This project is licensed under the MIT License.

