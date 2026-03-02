
---

# PITA – Pharmaceutical Inventory & Tracking Analysis System

PITA is an enterprise-style pharmaceutical inventory management system with integrated AI-powered business intelligence.

It provides structured inventory tracking, role-based access control, transaction logging, and AI-driven executive reporting.

---

## Features

### Core Inventory Management

* Master inventory dashboard
* Real-time stock tracking
* Low-stock alert system
* Expiry and supplier tracking
* Transaction history logging

### Transaction Processing

* Sale recording (Strategy Pattern)
* Restock processing
* New SKU creation (Manager only)
* Role-based transaction permissions

### Role-Based Access Control

* Manager
* Pharmacist
* Inventory Clerk
* Administrator

Each role has defined system permissions.

### AI Business Intelligence

* Executive sales trend summary
* Top-selling drug analysis
* Low-stock prioritization insights
* Cloud (Gemini) or local LLM backend
* Facade Pattern abstraction for AI complexity

---

## Design Patterns Implemented

### Strategy Pattern

Used for transaction execution:

* `SaleStrategy`
* `RestockStrategy`

Encapsulates transaction behavior independently from UI logic.

### Facade Pattern

`TrendAnalysisFacade` abstracts:

* LLM initialization
* API handling
* Prompt engineering
* Response handling

---

## Tech Stack

* Python
* CustomTkinter
* Pandas
* Pydantic
* LangChain
* Google Gemini API
* Ollama (local LLM option)
* CSV-based storage

---

## Project Structure

```text
.
├── app.py            # Main GUI system
├── ai.py             # AI Facade + Trend analysis
├── inventory.csv     # Inventory database
├── transactions.csv  # Transaction log
├── users.csv         # Role management
├── .env              # API key configuration
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/Ahmaddd-y/PITA-System.git
cd PITA-System
```

### 2. Install Dependencies

```bash
pip install customtkinter pandas python-dotenv langchain langchain-google-genai langchain-ollama pydantic
```

### 3. Configure AI Key (Optional – for Cloud Model)

Create `.env` file:

```bash
GEMINI_API_KEY=your_api_key_here
```

---

## Run the System

```bash
python app.py
```

---

## System Architecture Overview

* GUI Layer: CustomTkinter
* Business Logic Layer: Strategy-based transaction engine
* Persistence Layer: CSV storage
* AI Layer: Facade-based LLM integration
* Security Layer: Role-based access control

---

## Academic Context

Demonstrates applied software engineering principles:

* Object-Oriented Design
* Design Patterns (Strategy & Facade)
* Role-Based Authorization
* Threaded AI execution
* Enterprise UI structuring

---
