# 📚 Librarian Assistant
*Empowering Smarter Learning Through AI-Driven Insights*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)  
[![Docker](https://img.shields.io/badge/docker-ready-0db7ed)](https://www.docker.com/)  

Built with the tools and technologies:  
`Python` · `Flask` · `ChromaDB` · `OpenAI` · `LangChain` · `Docker`

---

## 📑 Table of Contents
- [Overview](#overview)
- [Screenshots](#screenshots)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running with Docker](#-running-with-docker-recommended)
- [Usage](#usage)
- [Testing](#testing)
- [License](#license)

---

## 🔍 Overview

**Librarian Assistant** is an AI-powered conversational system that acts as a **smart book buddy**.  
It provides **book recommendations, summaries, and thematic exploration** using **Retrieval-Augmented Generation (RAG)** combined with **tool completion**.  

---

## 📸 Screenshots

### 🔑 Login & Registration
![Login](/mnt/data/4db82df1-1e31-408e-a0bc-6a2e6b877152.png)

### 💬 Conversational Interface
![Chat](/mnt/data/39b7920c-79b1-4c21-a20a-ed74ed42e74f.png)

### ⚙️ Options Menu
![Options](/mnt/data/bb8a8501-3d0c-44fc-9bdd-6d922dd98127.png)

### 🖼️ Book Cover Generation
![Image Generation](/mnt/data/e12639a3-11f3-4a57-be6c-c39e94cd14ba.png)

### 🎤 Voice Interaction
![Voice Input](/mnt/data/8b80c716-3430-4abe-8d08-d015a5b389fe.png)

### 🚫 Moderation
![Moderation](/mnt/data/88c90cd0-07a0-4758-9b12-fb401daed01f.png)

### 🖼️ AI Responses with Images & Audio
![Response](/mnt/data/55a5b333-6bba-4fe9-9a80-ef17e24eb07c.png)

---

## 🚀 Getting Started

### ✅ Prerequisites
- **Python** 3.10+  
- **pip**  
- **Docker** (optional)  
- **OpenAI API Key** (required)  

---

### 🔧 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Andrei-Mihnea/LLM_Homework.git
cd LLM_Homework
pip install -r requirements.txt
python main.py
```

---

### 🐳 Running with Docker (recommended)

Start the container:
```bash
docker-compose up --build
```

Stop the container:
```bash
docker-compose down --remove-orphans
```

---

## ▶️ Usage

1. Open the app at 👉 [http://localhost:5000](http://localhost:5000)  
2. Create an account or log in  
3. Ask for book recommendations, summaries, or thematic explorations  
4. Try advanced options like **image generation** and **audio replies**  

Example API call:
```bash
curl -X POST http://localhost:5000/api/assistant   -H "Content-Type: application/json"   -d '{"query": "Suggest a book about magic and friendship"}'
```

---

## 🧪 Testing

```bash
pytest
```

With Docker:
```bash
docker-compose run --rm app pytest
```

---

## 📜 License
This project is licensed under the MIT License – see the [LICENSE](./LICENSE) file for details.
