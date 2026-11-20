# Screenshot Scout Python examples

Install the package, set `SCREENSHOTSCOUT_ACCESS_KEY`, and run an example from the repository root:

```shell
python -m pip install -e .
python examples/binary_capture.py
```

If `SCREENSHOTSCOUT_SECRET_KEY` is also set, the client signs its requests and the URL that
`capture_url.py` prints. `capture_from_html.py` sends the HTML in a POST request, which can't be
signed, so run it without `SCREENSHOTSCOUT_SECRET_KEY`.

- `binary_capture.py` saves a WebP capture as `screenshot.webp`.
- `json_capture.py` requests a JSON result and prints the screenshot URL.
- `async_client.py` uses async Python I/O and waits for the inline binary response.
- `capture_url.py` builds a sensitive capture URL without making a network request.
- `capture_from_html.py` renders an invoice to PDF and saves it as `invoice.pdf`.
