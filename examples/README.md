# Screenshot Scout Python examples

Install the package, set `SCREENSHOTSCOUT_ACCESS_KEY`, and run an example from the repository root:

```shell
python -m pip install -e .
python examples/binary_capture.py
```

The examples read credentials explicitly and pass them to the SDK. For signed requests or signed
capture URLs, also set `SCREENSHOTSCOUT_SECRET_KEY`.

- `binary_capture.py` saves a WebP capture as `screenshot.webp`.
- `json_capture.py` requests a JSON result and prints the screenshot URL.
- `async_client.py` uses async Python I/O and waits for the inline binary response.
- `capture_url.py` builds a sensitive capture URL without making a network request.
