FROM python:3.13-slim

WORKDIR /app

# Dependencies copied and installed BEFORE the rest of the source code, so
# Docker's layer cache only invalidates this (slow) step when requirements.txt
# itself changes — not on every ordinary code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Everything above (pip install, copying source) runs as root — fine, since
# the build happens in an isolated, disposable environment, not a real
# machine. What actually matters is the RUNTIME process — switch to a
# dedicated non-root user before anything actually starts serving traffic,
# so a compromised app doesn't hand an attacker root inside the container.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --host 0.0.0.0, not uvicorn's default 127.0.0.1 — the default means "only
# accept connections from inside this exact container," which is unreachable
# from anywhere else, including Docker's own port mapping.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
