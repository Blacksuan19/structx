# Document Measurement

`structx.measurement` estimates how much content a PDF holds. It exists for
integrations that need page and text-length estimates **before** extraction,
such as quoting usage or sizing a queue.

It is separate from extraction on purpose:

- Extraction never calls it, so normal runs pay no measurement cost.
- Measuring never rewrites, converts, or replaces the input file.
- OCR here is local image-to-text recognition, never a model request.

Install the optional dependencies:

```bash
pip install "structx[measurement]"        # embedded text only
pip install "structx[measurement-ocr]"    # adds local OCR for scanned pages
```

## Usage

```python
from structx.measurement import DocumentMeasurer

measurer = DocumentMeasurer(ocr_mode="auto")
measurement = measurer.measure("scripts/example_input/S0305SampleInvoice.pdf")

print(measurement.page_count)       # 1
print(measurement.character_count)  # 1321
print(measurement.status)           # complete

for page in measurement.pages:
    print(page.page_number, page.method, page.character_count, page.status)
```

One measurer can measure many documents and reuses its OCR engines across them,
so create it once and keep it. Measurement is synchronous. Reading and rendering
PDF pages is serialized internally because the PDF backend is not thread-safe,
but OCR runs outside that lock, so a slow scanned document does not block other
documents measured at the same time.

## Parallel OCR

OCR costs seconds per page, so a multi-page scan is slow when measured one page
at a time. `ocr_workers` recognizes several pages at once:

```python
measurer = DocumentMeasurer(ocr_mode="auto", ocr_workers=4)
try:
    measurement = measurer.measure("scanned.pdf")
finally:
    measurer.close()  # release worker threads; measuring again recreates them
```

Pages are still reported in source order, and only one batch of pages is
rendered at a time, so a long document does not hold every page image in memory.

The default is `1`. Raise it deliberately:

- Each worker gets its own OCR engine, because a single `RapidOCR` instance
  updates its own state per call and cannot be shared across threads.
- ONNX Runtime already spreads one recognition call across CPU cores, so extra
  workers only help when each engine is limited to one inference thread. The
  built-in reader applies that automatically for `ocr_workers > 1`; pass
  `ocr_engine_params` to override it.
- More workers is not better. On a 12-core machine measuring 8 scanned pages,
  1 worker took 20.8s, 4 workers took 14.2s, and 6 workers took 16.6s.
- Each engine loads its own models, so memory grows with worker count.

A custom `ocr_reader` is never fanned out with per-thread engines; if you supply
one and raise `ocr_workers`, it must be safe to call from several threads.

## OCR Modes

| Mode | Behavior |
| --- | --- |
| `never` (default) | Counts the embedded text layer only. Pages without one are reported as `partial` with `ocr_skipped`. |
| `auto` | Adds OCR for pages whose embedded text is missing, empty, or unreadable. |
| `always` | Reads every page with OCR instead of its embedded text, so mixed pages are not counted twice. |

Supply `ocr_reader` to use your own recognizer, for example to pin a language or
model. It receives rendered page pixels as an RGB array and returns text. When
it is omitted and OCR is needed, the built-in RapidOCR reader is created on
first use.

```python
measurer = DocumentMeasurer(ocr_mode="always", ocr_reader=my_reader)
```

Render resolution is not a useful cost lever: the OCR engine resizes pages
internally, so 72 DPI and 150 DPI cost about the same per page.

## Completeness

Counts are estimates, and the result says how they were produced rather than
implying certainty:

- A page is `complete` when its text layer was read, or when OCR ran
  successfully — including a successful OCR pass that found no text.
- A page is `partial` when measurement could not observe its content. The
  `error_code` explains why: `ocr_skipped`, `ocr_unavailable`, `ocr_failed`,
  `native_text_failed`, `page_render_failed`, or `page_load_failed`.
- A failing page never removes pages from the document. A document keeps its
  real page count and reports `partial`, so callers can decide whether to
  fall back to page-based handling.
- `estimator_revision` identifies the counting algorithm. It does not promise
  that OCR models or their versions stay fixed.

Invalid, missing, empty, encrypted, non-PDF, and oversized inputs raise
`FileError`. Invalid settings raise `ConfigurationError`.

## API

### DocumentMeasurer

::: structx.measurement.DocumentMeasurer
    options:
      show_bases: false
      heading_level: 4

### DocumentMeasurement

::: structx.measurement.DocumentMeasurement
    options:
      show_bases: false
      heading_level: 4

### PageMeasurement

::: structx.measurement.PageMeasurement
    options:
      show_bases: false
      heading_level: 4
