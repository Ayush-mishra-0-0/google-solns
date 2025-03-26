FROM python:3.10-slim

# Install system dependencies including TeX Live
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    texlive texlive-latex-extra texlive-fonts-extra \
    texlive-latex-recommended texlive-science \
    tipa libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy your application code
WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "app:app"]
