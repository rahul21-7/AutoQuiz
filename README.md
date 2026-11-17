# AutoQuiz: Smart Exam Quizzer System Using Retrieval-Augmented Generation (RAG)

**National Institute of Technology, Warangal**  
**Department of Computer Science and Engineering**  
**Group No. 4:**
* **Dasari Rahul** (Roll No: `24CSB1A12`)
* **Devarapaga Surya Teja** (Roll No: `24CSB1A13`)
* **Dhruv Garg** (Roll No: `24CSB1A14`)

---

## Quick Start: How to Run

### Step 1. Launch the Application Server
Run the unified launcher using the pre-configured Python virtual environment:

On Windows (PowerShell):
```powershell
.\.venv\Scripts\python.exe run.py --port 8000
```

On Windows (Command Prompt):
```cmd
.\.venv\Scripts\python.exe run.py --port 8000
```

Alternatively, activate the virtual environment first:
```powershell
.\.venv\Scripts\Activate.ps1
python run.py --port 8000
```

### Step 2. Open in Your Browser
Navigate to:
```
http://localhost:8000
```

### Step 3. Using the Web Application
1. **Upload Study Material**: Click **Attach File** or drag & drop lecture notes or presentation slides (`.pdf`, `.pptx`, `.md`, or `.txt`), e.g., `Maximum Subarray Sum Problem.pptx` or sample materials from `sample_data/`.
2. **Interactive Question Loop**: AutoQuiz extracts key concepts, mathematical formulas (LaTeX), and code blocks, generating a grounded 3-to-5 question quiz loop.
3. **Keyboard & Click Input**:
   - Select answers with `1`-`4` or `A`-`D` (or click the options).
   - Tag mandatory confidence: `H` (High), `M` (Medium), `L` (Low).
   - Press `Enter` to submit each question instantly.
4. **Adaptive Remediation**:
   - Scoring **100%** with High/Medium confidence verifies mastery and displays the 3D Mastery Trophy.
   - Any incorrect answers or low-confidence guesses trigger a targeted remediation loop with brand-new grounded questions (BR-2, BR-3).
5. **Session Continuity & Progress**:
   - View and resume previous chat sessions at any time from the left sidebar (**Recent Practice Chats**).
   - Review your weakness heatmap, first-attempt vs looped pass rates, and Ebbinghaus retention decay alerts in the **Progress & Heatmap** view.

---

## Running the Automated Test Suite (TC-01 through TC-77)

The repository includes an automated test suite covering all 77 software test cases specified in the IEEE 830-1998 SRS report.

To execute the test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_suite_tc01_tc77.py
```
or via the launcher:
```powershell
.\.venv\Scripts\python.exe run.py --test
```

### Test Suite Highlights:
* **Security & Isolation (TC-01 to TC-06)**: Salted PBKDF2 hashing, login controls, student data isolation, and admin authorization.
* **Document Ingestion (TC-07 to TC-25)**: Multi-format parsing (`.pdf`, `.pptx`, `.txt`, `.md`), executable header rejection, duplicate versioning/overwrite, LaTeX and AST code preservation.
* **Question Synthesis & RAG (TC-26 to TC-34)**: Grounded question generation, zero cross-loop repetition (BR-3), JSON formatting retry, and insufficient context handling.
* **Remediation & Confidence Guard (TC-35 to TC-54)**: Strict 100% threshold, low-confidence penalty, unverified concept re-testing, and session state recovery.
* **Spaced Repetition & Decay (TC-55 to TC-62, TC-68)**: Ebbinghaus forgetting curve, dynamic stability intervals, micro-verification loops, and decay alerts.
* **Analytics & Performance (TC-63 to TC-67)**: Sub-second dashboard rendering (PERF-3), first-attempt vs remediated breakdown (BR-4), and weakness heatmap reactivity.
* **Admin Portal & API (TC-70 to TC-77)**: Three-click workflow, WCAG AA compliance, taxonomy CRUD, vector collection wiping, and student history resets.

---

## Executive Summary & Architecture Overview

AutoQuiz is an autonomous, Retrieval-Augmented Generation (RAG) powered quizzing web application engineered to evaluate academic exam readiness. The platform ingests user-uploaded course documents (lecture slides, PDFs, Markdown notes, LaTeX equations, and source code), vectorizes text locally, and dynamically generates targeted, grounded mock quizzes.

### Core Architectural Features:
1. **Local RAG Vector Ingestion (BR-1)**:
   - Ingests PDF, PPTX, TXT, and Markdown (`.md`) files locally with zero network leakage of sensitive student documents.
   - Detects and rejects renamed executables, encrypted PDFs, and scanned image-only files.
   - Identifies duplicate titles with prompt for **Overwrite** or **Versioning** (`v2`, `v3`).
2. **Multi-Modal AST & LaTeX Math Parsing (REQ_02, UC-6)**:
   - Preserves Python nested indentation and class/function structures via Abstract Syntax Trees.
   - Preserves LaTeX formulas ($\sum, \int, \frac{a}{b}$) and special characters (`< > & \ { }`).
3. **Adaptive 100% Remediation Loop (BR-2, REQ_12)**:
   - Sequential module unlocking: students must score 100% on the current topic before unlocking subsequent modules.
4. **Anti-Guessing Confidence Verification Guard (BR-6, REQ_10, REQ_11)**:
   - 1-click mandatory confidence rating (**High**, **Medium**, **Low**).
   - Correct answers marked with **Low confidence** are flagged as *Unverified*, earn **0 mastery credit**, and the underlying concept is re-introduced in subsequent loop iterations.
5. **Zero Repetition Rule (BR-3, REQ_08)**:
   - Duplicate question stems and identical answer sets are strictly forbidden across consecutive attempt iterations on the same topic.
6. **Automated Spaced Repetition Mastery Decay (BR-5, REQ_14, REQ_15)**:
   - Ebbinghaus retention curve scheduler automatically transitions mastered topics to **Review Due** after retention periods (scaling dynamically based on attempt frequency and score stability).
   - Prompts a 2-question micro-verification loop upon login: scoring 100% restores mastery; failure revokes mastery and initiates full re-testing.
7. **Progress Analytics & Weakness Heatmap (BR-4, REQ_16, REQ_17)**:
   - Real-time dashboard rendering in under 1 second (PERF-3).
   - Explicitly differentiates **First-Attempt Pass Rate** from **Looped/Remediated Mastery**.
   - Color-coded concept weakness heatmap highlighting high-failure topics.
8. **Admin / Instructor Portal (UC-10, UC-11)**:
   - Syllabus taxonomy management (CRUD).
   - Document vector store wipe tool.
   - Student performance history reset.

---

## User Accounts and Authentication

The platform provides role-based student and instructor accounts for testing data isolation:

| Role | User ID | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Student A** | `24CSB1A12` | `secret_pass` | Upload notes, adaptive practice loops, confidence tagging, analytics heatmap |
| **Student B** | `24CSB1A13` | `student_pass_13` | Secondary student account for cross-student retrieval isolation testing |
| **Admin / Instructor** | `admin` | `admin_pass_2026` | Syllabus taxonomy CRUD, vector collection wipe, student history reset |

---

## Use Case Point (UCP) Estimation Summary

As documented on Report pages 75-82:
- **Unadjusted Use Case Weight (UUCW)**: $185$ (8 Simple + 7 Average + 5 Complex use cases)
- **Unadjusted Actor Weight (UAW)**: $9$ (4 Simple + 1 Average + 1 Complex actors)
- **UUCP**: $185 + 9 = 194$
- **Technical Complexity Factor (TCF)**: $1.01500$
- **Environmental Complexity Factor (ECF)**: $0.71000$
- **Adjusted Use Case Points (UCP)**: $194 \times 1.015 \times 0.71 = 139.806$
- **Total Development Effort**: $139.806 \times 8 \text{ hours} \approx 1,118.45 \text{ person-hours}$

To run the standalone UCP calculator:
```powershell
.\.venv\Scripts\python.exe run.py --ucp
```

---

## Repository Directory Structure

```
AutoQuiz/
├── app/
│   ├── config.py                 # Configuration settings and algorithm constants
│   ├── database.py               # SQLite relational schema, indexing, and retry queue
│   ├── security.py               # Salted PBKDF2 hashing and session management
│   ├── legacy_source_code.py     # Transcribed source code from report pages 51-56 & 98-99
│   ├── main.py                   # Flask REST API server and SPA routing
│   ├── routes/
│   │   ├── auth_routes.py        # Authentication and session endpoints
│   │   ├── doc_routes.py         # Document ingestion, duplicate resolution, list
│   │   ├── quiz_routes.py        # Adaptive remediation loop, confidence guard, micro-verification
│   │   ├── analytics_routes.py   # Readiness metrics, first-try vs looped, weakness heatmap
│   │   └── admin_routes.py       # Syllabus taxonomy CRUD, vector wipe, student reset
│   └── services/
│       ├── ast_parser.py         # Multi-Modal Code & LaTeX AST extraction
│       ├── document_service.py   # File validation, integrity check, semantic chunking
│       ├── vector_store.py       # Local Chroma DB compatible vector engine
│       ├── rag_engine.py         # Context retrieval, question generator, anti-hallucination
│       ├── remediation.py        # 100% strict mastery loop, sequential locks, session recovery
│       ├── spaced_repetition.py  # Ebbinghaus retention decay audit and micro-verification
│       ├── analytics_service.py  # Performance analytics, retry trends, weakness heatmap
│       └── admin_service.py      # Taxonomy management, vector wipes, student resets
├── static/
│   ├── index.html                # Single-Page Application with KaTeX CDN and tab views
│   ├── css/styles.css            # WCAG AA compliant high-contrast stylesheet (>= 4.5:1)
│   ├── js/app.js                 # Frontend application state, 3-click submission, reactive UI
│   ├── js/three_elements.js      # 3D technical wireframe polyhedron and mastery trophy gem
│   └── js/three.min.js           # Three.js 3D rendering library
├── sample_data/
│   ├── ml_overfitting.pdf        # Valid sample PDF on ML overfitting & evaluation
│   ├── python_algorithms.md      # Sample Markdown with 10-line Python code & LaTeX
│   ├── business_essentials.txt   # Sample Plain Text notes on financial structures
│   ├── one_sentence.txt          # Minimal note for testing insufficient context (TC-32)
│   ├── scanned_empty.pdf         # Empty PDF for testing unreadable file rejection (TC-12)
│   └── generate_samples.py       # Dataset generator script
├── tests/
│   ├── test_suite_tc01_tc77.py   # Complete test suite covering TC-01 to TC-77
│   └── conftest.py
├── tools/
│   ├── ucp_calculator.cpp        # Exact C++ UCP calculator from report pages 75-78
│   └── ucp_calculator.py         # Python mirror of UCP calculator
├── run.py                        # Unified launcher script (Server, Tests, UCP, Samples)
├── pytest.ini                    # Pytest test discovery configuration
├── requirements.txt              # Production and testing Python requirements
└── README.md                     # Comprehensive documentation and verification manual
```

---

## Business Rules & Non-Functional Verification Reference

| Rule ID | Name | Description | Verification Test |
| :--- | :--- | :--- | :--- |
| **BR-1** | Local Vector Ingestion | All file parsing, semantic chunking, and vector storage occur locally on device. | `TC-20` |
| **BR-2** | Strict 100% Mastery | Advancement to sequential curriculum modules strictly requires a 100% score on the current loop. | `TC-40`, `TC-41`, `TC-42` |
| **BR-3** | Zero Repetition | Duplicate question stems and identical answer sets are forbidden across consecutive attempt iterations. | `TC-28`, `TC-43` |
| **BR-4** | Success Metric Separation | Dashboard explicitly differentiates first-try success from looped/remediated mastery success. | `TC-64` |
| **BR-5** | Dynamic Decay Scaling | Spaced repetition decay intervals dynamically adjust based on historical attempts and score stability. | `TC-57` |
| **BR-6** | Anti-Guessing Confidence | Achieving 100% topic mastery requires all correct answers to be marked with Medium or High confidence. | `TC-51`, `TC-52`, `TC-53` |
| **PERF-1** | Fast Ingestion | 100-page document parsing and vector embedding complete in under 10 seconds. | `TC-19` |
| **PERF-2** | Loop Transition | Question generation and feedback rendering complete within 3 seconds. | `TC-29`, `TC-62` |
| **PERF-3** | Dashboard Latency | Dashboard analytics and weakness heatmaps render in under 1 second. | `TC-63` |
| **PERF-4** | Database Latency | Score logging and evaluation writes complete in under 100 milliseconds. | `TC-36`, `TC-37` |
