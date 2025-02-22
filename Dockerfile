FROM python:3.10

# Set working directory
WORKDIR /app

# Install system dependencies for Oracle client
RUN apt-get update && apt-get install -y libaio1 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot files
COPY . .

# Run the bot
CMD ["python", "bot.py"]

