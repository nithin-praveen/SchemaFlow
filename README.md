# SchemaFlow ⚡

> **Visual ASCII Relational Learning Engine for MySQL & Physical Query Pipeline Simulator**  
> *100% Deterministic • Zero AI/ML Hallucinations • Offline-First • Screen-Reader Accessible*

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-36%20passed-brightgreen.svg)]()
[![Determinism](https://img.shields.io/badge/determinism-100%25%20Zero--AI-brightgreen.svg)]()
[![Accessibility](https://img.shields.io/badge/accessibility-WCAG%202.1%20Compliant-blueviolet.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Table of Contents
- [Overview & Societal Mission](#-overview--societal-mission)
- [Key Features](#-key-features)
  - [1. Peter Chen Conceptual ER Model (Diamonds & Rectangles)](#1-peter-chen-conceptual-er-model-diamonds--rectangles)
  - [2. Physical Relational & UML Class Renderers](#2-physical-relational--uml-class-renderers)
  - [3. Screen-Reader Natural Language Describer](#3-screen-reader-natural-language-describer)
  - [4. Physical SQL Query Pipeline Visualizer (Interactive Flow)](#4-physical-sql-query-pipeline-visualizer-interactive-flow)
- [How It Works Under the Hood](#-how-it-works-under-the-hood)
- [Public Service Schemas & Benchmark Datasets](#-public-service-schemas--benchmark-datasets)
- [Tech Stack](#-tech-stack)
- [Installation & Quick Start](#-installation--quick-start)
- [Running Automated Tests](#-running-automated-tests)
- [CLI Live Demo](#-cli-live-demo)
- [Academic Context](#-academic-context)

---

## 🌍 Overview & Societal Mission

Traditional database visualizers (e.g., MySQL Workbench, pgAdmin, draw.io) rely on heavy raster/vector graphics that are **completely invisible to blind and visually impaired students using screen readers**, require high-performance GPUs, and break in low-resource or terminal-only environments. Furthermore, generative AI tools frequently hallucinate constraints, misidentify composite keys, and misclassify cardinalities.

**SchemaFlow** solves this through a pure, lightweight, **100% mathematical and deterministic engine**:
- **Dual Visual & Auditory Accessibility**: Produces monospace ASCII character-matrix diagrams for sighted learners alongside structured plain-English narratives for screen readers.
- **Textbook Pedagogical Standards**: Renders classic academic **Peter Chen ER diagrams** (Rectangles for Entities, Diamonds for Relationships, Ellipses for Attributes).
- **Physical Query Execution Order**: Visually demonstrates how the database engine actually executes SQL queries step-by-step (`FROM` ➔ `WHERE` ➔ `GROUP BY` ➔ `HAVING` ➔ `SELECT` ➔ `ORDER BY` ➔ `LIMIT`).
- **Zero Cloud / AI Dependencies**: Completely air-gapped, zero-cost, and runs anywhere from a basic laptop to a low-power lab terminal.

---

## ✨ Key Features

### 1. Peter Chen Conceptual ER Model (Diamonds & Rectangles)
Renders classic database textbook conceptual models using monospace Unicode characters:
- **Rectangles (`┌───┐`)**: Entity sets.
- **Double-Line Rectangles (`╔═══╗`)**: Weak entity sets.
- **Diamonds (`/\ <...> \/`)**: Relationship sets with automated verb derivation (`ENROLS`, `BOOKS`, `TREATS`, `SERVES`).
- **Ellipses (`( ... )`)**: Key attributes marked with `* [PK]` and unique attributes marked with `[UQ]`.
- **Cardinality Ratios (`1`, `N`, `M`)**: Connected using cost-penalized orthogonal Breadth-First Search (BFS) routing.

```text
                                        /\
    ┌────────────────┐                 /  \                 ┌────────────────┐
    │    students    │M───────────< ENROLMENTS >───────────N│    classes     │
    └────────────────┘                 \  /                 └────────────────┘
                                        \/

════════════════════════════════════════════════════════════════════════════════════
                     ENTITY & RELATIONSHIP ATTRIBUTES (ELLIPSES)                    
════════════════════════════════════════════════════════════════════════════════════
┌── [ENTITY] students
│   ( student_id* [PK] )  ( roll_number [UQ] )  ( student_name )  ( standard )  
┌── [ENTITY] classes
│   ( class_id* [PK] )  ( subject_code )  ( subject_title )  ( teacher_name )  
┌── [RELATIONSHIP ATTRIBUTES] <ENROLMENTS>
│   ( enrolled_date )  ( grade_letter )  
```

---

### 2. Physical Relational & UML Class Renderers
- **Relational Tables**: Double-line boxes (`╔═══╗`) showing exact column types, inline `[PK]`, `[FK]`, and `[UQ]` indicators.
- **UML Class Diagrams**: Class notation formatted as `+ attribute : TYPE <<PK>> <<FK>>` with association multiplicity (`1`, `0..1`, `0..*`).

---

### 3. Screen-Reader Natural Language Describer
Generates structured, grammatically correct English audio-ready summaries:
> *"Table 'students' is an entity set with primary key 'student_id'. Table 'classes' has primary key 'class_id'. They are connected in a many-to-many relationship via associative junction table 'enrolments'."*

---

### 4. Physical SQL Query Pipeline Visualizer (Interactive Flow)
Tab 4 demonstrates how the database engine executes SQL queries under the hood:
- **Interactive Flowtrack Roadmap**: Visual breadcrumbs with arrows connecting `[FROM] ➔ [WHERE] ➔ [GROUP BY] ➔ [HAVING] ➔ [SELECT] ➔ [ORDER BY] ➔ [LIMIT]`.
- **Live Query Clause Highlighter**: The currently executing clause lights up in glowing neon on your actual SQL code.
- **Physical Department Buckets**: Visually clusters rows into actual department containers for `GROUP BY`, stamped with `[✔ APPROVED]` or `[✖ DISCARDED]` for `HAVING`.
- **Tuple Filter Cards**: Renders cards with live boolean condition checks (`$75,000 >= $45,000 ➔ KEEP [✔]`).
- **Written vs Physical Order Contrast**: Highlights the counter-intuitive DBMS reality (e.g. *"Written as #1 in SQL (SELECT), but actually executes FIFTH under the hood!"*).
- **Auto-Play & Stepper Controls**: Step forward/backward manually or hit `▶ AUTO-PLAY` to animate the engine execution.

---

## 🧠 How It Works Under the Hood

```
               ┌────────────────────────────────────────────────────────┐
               │                SQL DDL / SELECT Input                  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         sqlglot AST Lexer & Grammar Parser             │
               │  Extracts tables, columns, constraints & query clauses │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         Deterministic Relational Classifier            │
               │   • 1:N ➔ Standard Foreign Key                         │
               │   • 1:1 ➔ UNIQUE column or FK as Whole Primary Key     │
               │   • M:N ➔ Composite PK consisting of >= 2 FKs          │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │             2D Grid Canvas & BFS Router                │
               │   • Collision detection avoidance around box borders   │
               │   • Dijkstra / BFS routing with turn-bend penalties    │
               └───────────────────────────┬────────────────────────────┘
                                           │
                ┌──────────────────────────┴──────────────────────────┐
                ▼                                                     ▼
┌──────────────────────────────┐                      ┌──────────────────────────────┐
│  Monospace Character Canvas  │                      │    Screen-Reader Describer   │
│  Chen ER, UML, Query Buckets │                      │ Accessible English Audio Text│
└──────────────────────────────┘                      └──────────────────────────────┘
```

---

## 📊 Public Service Schemas & Benchmark Datasets

SchemaFlow ships with four realistic public service schemas in `samples/`:
1. **`school.sql`**: Academic management system with an associative composite junction table (`enrolments` connecting `students` and `classes`).
2. **`hospital.sql`**: Public health hospital tracking patients, doctors, appointments (`1:N`), and medical records (`1:1`).
3. **`blood_bank.sql`**: District blood bank managing donor donations and transfusion matching.
4. **`ration_shop.sql`**: Civic public distribution system managing subsidized household quota entries.

For the **Query Pipeline Simulator**, SchemaFlow uses the canonical 8-row benchmark `emp` dataset to demonstrate filtering, partitioning, aggregate math, and sorting.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10+, Flask | REST API endpoints (`/api/er`, `/api/chen`, `/api/uml`, `/api/describe`, `/api/query-pipeline`) |
| **SQL Parser & AST** | `sqlglot` | Fast, deterministic dialect parsing of MySQL DDL and DML queries |
| **Pathfinding Algorithms** | Python standard library (`heapq`, BFS) | Collision-free orthogonal grid line routing |
| **Frontend UI** | HTML5, CSS3, Vanilla JS (ES6+ IIFE) | Zero-framework, responsive Metropolis cyber-terminal theme |
| **Accessibility** | ARIA Live Regions, WCAG 2.1 | Accessible screen-reader support & high-contrast styling |
| **Testing** | `pytest` | 36 unit, integration, and renderer tests |

---

## 🚀 Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/nithin-praveen/SchemaFlow.git
cd SchemaFlow
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Web Application
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Running Automated Tests

Run the full 36-test suite:
```bash
pytest
```
*All tests pass in `< 1.0s` with zero external network or database dependencies.*

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\LENOVO\SchemaFlow
collected 36 items

tests\test_api.py ...........                                            [ 30%]
tests\test_classifier.py .....                                           [ 44%]
tests\test_describer.py ...                                              [ 52%]
tests\test_parser.py ......                                              [ 69%]
tests\test_query_pipeline.py .....                                       [ 83%]
tests\test_renderers.py ......                                           [100%]

============================= 36 passed in 0.69s ==============================
```

---

## 💻 CLI Live Demo

For quick offline terminal demonstrations or grading without opening a browser:
```bash
python demo.py
```
Select any public service schema (e.g. `4` for `school.sql`), and SchemaFlow will parse the tables, classify constraints, and render the visual Chen ER diagram directly in your console.

---

## 🎓 Academic Context

* **Course**: 24CSE57 – Societal Based Mini Project
* **Department**: Department of Computer Science and Engineering, NHCE
* **Academic Year**: 2026–2027
* **Core Philosophy**: Building assistive, offline educational tools for equal access to computer science education.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
