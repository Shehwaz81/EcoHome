# Use Python 3.12 (compatible with your Pandas/NumPy versions)
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy your requirements file into the container
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your code into the container
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Start the Flask app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]