# Existing Dockerfile content

# (Ensure to include all existing content of the Dockerfile and add the new lines as specified)

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# ...

RUN pip install --no-cache-dir --upgrade pip
