# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Install pipenv and any other dependencies
RUN pip install pipenv

# Set the working directory in the container
WORKDIR /workspace

# Copy requirements.txt to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Switch back to the "vscode" user
USER vscode