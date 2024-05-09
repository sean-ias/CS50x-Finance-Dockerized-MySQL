# Use the official Python image as the base image
FROM python:3.9-slim

ENV DB_USER=root
ENV DB_PASSWORD=4009mySql_
ENV DB_HOST=mywebappdb.cpgw8i4cyt6h.us-east-1.rds.amazonaws.com
ENV DB_NAME=cs50_finance
ENV TZ=Asia/Tashkent

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install Python dependencies
RUN apt update && apt install -y gcc

RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container
COPY . .

# Define the command to run the Flask app
CMD ["uwsgi","--ini","app.ini"]
EXPOSE 90