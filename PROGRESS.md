# PROGRESS.md
Last Updated: 2026-05-28 05:20
Current Step: COMPLETE ✅

## Files
✅ requirements.txt
✅ .env (template)
✅ rules/microba_rules.json
✅ rules/logam_berat_rules.json
✅ rules/cppob_rules.json
✅ prompts/classify_prompt.txt
✅ prompts/compliance_llm_prompt.txt
✅ prompts/report_prompt.txt
✅ data/regulations/ — 10 PDFs distributed across 4 category folders
✅ src/__init__.py
✅ src/ingest.py
✅ src/extractor.py — FIXED: dot separator, multiline, TPC/Kapang dan Khamir
✅ src/classifier.py — FIXED: DAIRY keywords, import re, gemini-2.0-flash
✅ src/rule_engine.py
✅ src/rag_query.py
✅ src/llm_narrator.py — FIXED: project-root paths, gemini-2.0-flash
✅ src/report_generator.py
✅ src/app.py — FIXED: full dasar hukum display, MISSING handling, file_path
✅ README.md

## Test Results
- [x] Ingest test: ChromaDB populated (923 chunks: 131+186+389+217)
- [x] Extractor test: BOTH colon format AND dot separator format pass ✅
- [x] Classifier test: 4/4 categories correct ✅
- [x] Rule engine test: 2 violations detected (ALT, Timbal_Pb) ✅
- [x] RAG query test: semantic search returns relevant results ✅
- [x] LLM narrator test: fallback narration works ✅
- [x] Report generator test: PDF generated ✅
- [x] App test: Gradio boots on http://127.0.0.1:7860 ✅

## Bug Fixes Applied (2026-05-28)
1. Extractor: Added flexible _SEP pattern for dot/colon/dash separators
2. Extractor: Added "Total Plate Count"/"TPC" aliases for ALT
3. Extractor: Handle "Kapang dan Khamir" combined format
4. Extractor: Handle "Kadar Timbal (Pb)" with dot separator
5. Extractor: Added _preprocess_text for multiline Key:\nValue format
6. Extractor: Added _extract_section for === SECTION === format
7. Extractor: Added "Tanggal Pengujian", "Produsen" to metadata patterns
8. Classifier: Added 'pasteurisasi', 'sapi', 'uht' keywords for DAIRY
9. Classifier: Moved 'import re' to top of file
10. Classifier: Fixed prompt path to use project root
11. App: Table column "Pasal" → "Dasar Hukum" with full regulation+pasal
12. App: Handle all-MISSING case (warns instead of "semua memenuhi")
13. App: Robust PROJECT_ROOT via __file__
14. LLM Narrator: Fixed prompt paths to use project root
15. Gemini model: Updated from gemini-1.5-flash to gemini-2.0-flash

## Notes
- Python 3.10 required
- numpy<2.0 for torch 2.2.2 compatibility
- sentence-transformers 2.7.0 + transformers 4.40.0
- google-generativeai deprecated → consider migrating to google.genai
