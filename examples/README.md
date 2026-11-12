# Screenshot Scout Python examples

Install the package, set `SCREENSHOTSCOUT_ACCESS_KEY`, and run an example from the repository root:

```shell
python -m pip install -e .
python examples/binary_capture.py
```

If `SCREENSHOTSCOUT_SECRET_KEY` is also set, the client signs its requests and the URL that
`capture_url.py` prints.

- `binary_capture.py` saves a WebP capture as `screenshot.webp`.
- `json_capture.py` requests a JSON result and prints the screenshot URL.
- `async_client.py` uses async Python I/O and waits for the inline binary response.
- `capture_url.py` builds a sensitive capture URL without making a network request.
