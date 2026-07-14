# Screenshot Scout Python examples

Install the package, set `SCREENSHOTSCOUT_ACCESS_KEY`, and run an example from the repository root:

```shell
python -m pip install -e .
python examples/binary_capture.py
```

The examples read credentials explicitly and pass them to the SDK. For signed requests or signed
capture URLs, also set `SCREENSHOTSCOUT_SECRET_KEY`.

- `binary_capture.py` saves a PNG capture as `screenshot.png`.
- `json_capture.py` requests and prints a managed JSON result.
- `async_client.py` uses async Python I/O and waits for the inline binary response.
- `capture_url.py` builds a sensitive capture URL without making a network request.
