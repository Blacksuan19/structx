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

One measurer can measure many documents and reuses a single OCR engine across
them. Measurement is synchronous, and PDF work is serialized internally because
the PDF backend is not thread-safe. Run heavy OCR workloads in separate
processes rather than threads.

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
