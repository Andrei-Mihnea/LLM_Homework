# 📚 Librarian Assistant
*Empowering Smarter Learning Through AI-Driven Insights*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)  
[![Docker](https://img.shields.io/badge/docker-ready-0db7ed)](https://www.docker.com/)  

Built with the tools and technologies:  
`Python` · `Flask` · `ChromaDB` · `OpenAI` · `LangChain` · `Docker`

---

## 📑 Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [License](#license)

---

## 🔍 Overview

**Librarian Assistant** is an AI-powered toolkit for building a conversational **smart librarian assistant**.  
It combines **Retrieval-Augmented Generation (RAG)** with **custom tool completion**, enabling AI to fetch book information, provide summaries, and interact intelligently with user queries.

### ✨ Core Features
- 🧩 **Modular Architecture** – Separation of controllers, views, and services for scalable development.  
- 📖 **AI-Powered Library Assistance** – Uses OpenAI LLMs with **ChromaDB** as a vector store for semantic search.  
- 🔒 **Secure Authentication** – JWT-based login and session management (planned).  
- 🌐 **REST API** – Flask backend with modular API endpoints for assistant interaction.  
- 📦 **Containerized Deployment** – Ready-to-run with **Docker** and **Docker Compose**.  

---

## 🚀 Getting Started

### ✅ Prerequisites
Make sure you have installed:
- **Programming Language**: Python 3.10+  
- **Package Manager**: `pip`  
- **Container Runtime**: Docker (optional, for deployment)  
- **OpenAI API Key** (required for LLM functionality)  

---

### 🔧 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Andrei-Mihnea/LLM_Homework.git
cd LLM_Homework

```
If you want to run the project on your machine without the use of docker run the command:
```bash
pip install -r requirements.txt
python main.py
```

---

### 🔧Run app with docker(easiest way)

You can easily use the docker-compose command for out of the box usage.
To start the container:
```bash
docker-compose up --build
```

To stop the container user(using --remove-orphans is optional but it's good practice if redundancies remain)
```bash
docker-compose down --remove-orphans