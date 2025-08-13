# === Use Python Slim Image ===
FROM python:3.11-slim

# === Set working directory inside the container ===
WORKDIR /app

# === Install Python dependencies ===
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Copy full project files ===
COPY . .

# === Ensure Python can find your packages (e.g., smart_librarian/) ===
ENV PYTHONPATH=/app

# === Expose the Flask port ===
EXPOSE 5000

# === Run the app ===
CMD ["python", "main.py"]
