# MediLens-AI

### AI-Powered Medical Report Understanding System

MediLens-AI is an AI-powered medical report understanding system designed to convert unstructured medical reports into structured information and explain the extracted results in clear, accessible language.

The system combines document processing, OCR, table parsing, Retrieval-Augmented Generation (RAG), Large Language Models (LLMs), and a three-agent workflow to help users understand their medical reports.

> **Important:** MediLens-AI is an educational project. It does not diagnose diseases, prescribe medication, or replace professional medical advice. All extracted values and AI-generated explanations must be verified by a qualified healthcare professional.

---

## Features

- **Medical Report Upload:** Upload PDF, PNG, JPG, or JPEG medical reports through the web interface.
- **Document Extraction:** Uses Docling to extract text and reconstruct tables from medical reports.
- **OCR Fallback:** Uses PyMuPDF and Tesseract when the primary extraction process cannot produce usable structured results.
- **Dynamic Table Parsing:** Identifies test names, reported values, units, reference ranges, and alternate measurements across different report layouts.
- **Unit and Range Handling:** Normalizes recognized units, processes reference intervals, and identifies values that fall below or above the reported ranges.
- **Uncertainty Detection:** Preserves raw OCR information and flags ambiguous values or uncertain corrections for verification.
- **RAG-Based Knowledge Retrieval:** Retrieves relevant medical reference information from a local ChromaDB knowledge base.
- **AI-Powered Explanation:** Generates summaries, explanations, observations, and general guidance.
- **Safety Review:** Performs rule-based checks to identify potentially unsafe wording, missing information, and outputs requiring further review.

## System Architecture

MediLens-AI uses three specialized agents.

### Agent 1 — Document Reader

Responsible for extracting and structuring information from uploaded medical reports.

Responsibilities:
- Extract report content using Docling.
- Reconstruct and process report tables.
- Use PyMuPDF and Tesseract as a fallback extraction method.
- Identify test names, values, units, and reference ranges.
- Preserve original extracted information.
- Flag uncertain values and units for verification.

### Agent 2 — Medical Analysis

Responsible for explaining the extracted report information.

Responsibilities:
- Retrieve relevant medical knowledge using RAG.
- Generate a plain-language report summary.
- Explain the purpose and general meaning of extracted tests.
- Provide general guidance and precautions