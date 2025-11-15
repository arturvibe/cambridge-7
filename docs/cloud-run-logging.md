# Cloud Run Logging Best Practices

## Single-Line Log Entries

**Important:** Cloud Run logs split output by newlines. Each line becomes a separate log entry.

### Problem

When logging JSON with indentation (pretty-printing):
```python
logger.info(json.dumps(data, indent=2))
```

This creates multiple log entries, one for each line of the formatted JSON, making it difficult to read and filter in Cloud Run logs.

### Solution

Always log JSON as a single line:
```python
logger.info(f"HEADERS: {json.dumps(headers, default=str)}")
logger.info(f"FULL PAYLOAD: {json.dumps(payload, default=str)}")
```

### Benefits

1. **Single log entry per data structure** - Headers and payload each appear as one log entry
2. **Easier filtering** - Can search and filter complete JSON objects
3. **Better log readability** - Each entry is self-contained
4. **Proper log parsing** - Cloud Run can parse structured JSON from single-line logs

### Implementation

The webhook endpoint in `app/main.py` logs:
- Headers as single-line JSON: `HEADERS: {...}`
- Full payload as single-line JSON: `FULL PAYLOAD: {...}`

This ensures each piece of data appears as a single, complete log entry in Cloud Run logs.
