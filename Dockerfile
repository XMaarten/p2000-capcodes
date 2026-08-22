FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[scrape]' \
    && python -m playwright install --with-deps chromium

COPY overrides ./overrides
ENTRYPOINT ["p2000-capcodes"]
CMD ["--help"]
