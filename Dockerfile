# Use official Python base image
FROM python:3.10-slim

# Set up working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Start Streamlit app
CMD ["streamlit", "run", "web_app.py", "--server.port=8501", "--server.headless=true"]
