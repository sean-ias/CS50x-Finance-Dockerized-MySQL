# Use the official Python image as the base image
FROM python:3.9-slim

ENV DB_USER=root
ENV DB_PASSWORD=4009mySql_
ENV DB_HOST=localhost
ENV DB_NAME=cs50_finance
ENV TZ=Asia/Tashkent

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container
COPY . .

# Expose the Flask app port
EXPOSE 5000

# Define the command to run the Flask app
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]