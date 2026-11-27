# Capture protocol

How to reproduce the capture independently.

## Requirements

- Firefox 6.0 portable, win32 en-US
- bitaddress.org v1.2 source, commit 132f70cd
- Python 3 to run the injector

Firefox 6 archive:

    https://ftp.mozilla.org/pub/firefox/releases/6.0/win32/en-US/

The installer is a 7-Zip self-extracting archive. Extract it and take the
`core` directory. No installation needed.

Upstream page source:

    https://raw.githubusercontent.com/pointbiz/bitaddress.org/132f70cd457fe1865316a57d7bc9f5d166fc2e33/bitaddress.org.html

Save it as `ba12.html` outside this repository.

## Generate the instrumented page

    python3 tools/inject.py <path>/ba12.html <output-dir>

Three passive hooks are inserted into the real source:

| Hook | Captures |
|---|---|
| `Math.random` wrapper | first 200 return values |
| `SecureRandom.seedTime` / `seedInt` wrappers | call timestamps |
| `SecureRandom.ArcFour().init` wrapper | the 256-byte pool |

None of the hooks consumes additional `Math.random` calls, so the logged
stream is exactly what the page itself would have used.

### Anchor correctness

The POST hook must be placed after the block that **defines**
SecureRandom. The injector anchors on:

    var\s+sr\s*=\s*window\.SecureRandom

Anchoring on the first occurrence of the string `window.SecureRandom` is
wrong: that one is inside a licence comment in `<head>`. Placing the hook
there puts it before SecureRandom exists, it throws TypeError, and
`st` / `si` come back empty. This failure was observed.

Verify placement after generation:

    python3 -c "s=open('<out>/ba12_inst.html',encoding='utf-8').read(); i=s.find('var sr = window.SecureRandom'); j=s.find('t_after_sr'); print(j>i>0)"

Must print `True`.

## Launch

    "<ff6>/firefox.exe" -no-remote -profile "<prof>" "file:///<out>/ba12_inst.html"

The HTML path must be an argument to the same `firefox.exe`. Do not
double-click the file: it opens in the default browser.

Two captures were lost this way. Both returned `rv:149.0` and
`hasCrypto: true`. Firefox 149 does not use LCG-48, so the composition
cannot be checked on them at all.

`-no-remote` is required, otherwise the request is handed to an already
running Firefox instance.

Do not move the mouse during the session. Wait 15 seconds. Copy the JSON
from the textarea at the top of the page.

## Gate checks

Before any analysis, confirm:

| Field | Expected |
|---|---|
| `ua` | contains `rv:6.0` |
| `hasCrypto` | `false` |
| `mr` | 140 values |
| `pool` | 256 values |
| `st` | 3 timestamps |

If `ua` shows anything other than 6.0, stop. Nothing downstream is
meaningful. `verify_composition.py` enforces these checks and exits
non-zero on failure.

## Note on P

`P = cx ^ cx->link.next` depends on heap layout. The band observed in the
published capture (`0x1000`-`0x10D6`) was measured on Windows 7 32-bit.
It is not a constant and does not transfer to other machines or builds.

The verification script measures `seed48 = ms ^ P` directly from the
output stream and never assumes a value for `P`.

## Test vector handling

The capture contains a private key for a wallet generated in this
controlled session. It has never been funded and must never be funded.
It is published only so the reproduction can be checked independently.
