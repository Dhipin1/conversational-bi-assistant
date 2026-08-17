FROM python:3.11-slim

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tell Kaleido/Plotly where Chromium is installed
ENV BROWSER_PATH=/usr/bin/chromium

WORKDIR /app

# Install Chromium for Plotly/Kaleido image export.
# Chromium is required for: fig.to_image(format="png")
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for Docker build caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the project source code
COPY . /app

# Default Streamlit port; Render overrides it with $PORT
EXPOSE 8501

# Start Streamlit.
# Render automatically provides PORT, so do not create a PORT env variable in Render.
CMD ["sh", "-c", "python -m streamlit run app/Home.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.headless true"]