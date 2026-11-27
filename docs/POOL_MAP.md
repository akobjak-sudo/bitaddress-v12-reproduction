# Pool map - bitaddress.org v1.2

Source: commit `132f70cd457fe1865316a57d7bc9f5d166fc2e33`, file
`bitaddress.org.html`. All constants below are read from that source and
confirmed against a live Firefox 6 capture.

## Call sequence

`SecureRandom` is defined in `<head>`. Its closure executes on load:

    while (sr.pptr < sr.poolSize) {          // poolSize = 256
        t = Math.floor(65536 * Math.random());
        sr.pool[sr.pptr++] = t >>> 8;
        sr.pool[sr.pptr++] = t & 255;
    }

256 bytes, two per call -> **128 calls**.

Then, in the final `<script>` before `</body>`:

    seedLimit: (function () {
        var num = Crypto.util.randomBytes(12)[11];
        return 50 + Math.floor(num);
    })(),

`Crypto.util.randomBytes(n)` performs `n` calls of
`Math.floor(Math.random() * 256)` -> **12 calls**.

Total to this point: `128 + 12 = 140`. Index 139 is
`randomBytes(12)[11]`, the byte that determines `seedLimit`.

Last line of the file:

    setTimeout(ninja.wallets.singlewallet.forceGenerate, ninja.seedLimit * 20);

Hence `timeout = seedLimit * 20` milliseconds.

## XOR fields

`forceGenerate` mixes six values into the pool, each as little-endian
low 32 bits:

| Offset | Field | Origin |
|---|---|---|
| 0-3 | `T_init` | `seedTime()` during pool initialisation |
| 4-7 | `screenX` | `window.screenX` |
| 8-11 | `screenY` | `window.screenY` |
| 12-15 | `T_fg` | `seedTime()` in `forceGenerate` |
| 16-19 | `T_seed` | `seedTime()` in `seed()` |
| 20-23 | `T_gen` | `seedTime()` in `getByte()` |

Bytes 24-255 receive no further mixing. In the capture, all 232 trailing
mask bytes are zero - confirming no additional entropy source.

## Reading the map from a capture

The map can be recovered without knowing any timestamp. Reconstruct the
pre-XOR base from the logged `Math.random` values, then XOR against the
captured pool:

    base = bytearray(256)
    for i in range(128):
        t = int(65536.0 * mr[i]) & 0xFFFF
        base[2*i]   = (t >> 8) & 0xFF
        base[2*i+1] = t & 0xFF
    mask = bytes(pool[i] ^ base[i] for i in range(256))

Non-zero byte positions in `mask` give the field layout directly. In the
published capture:

    non-zero indices: 0,1,2,3, 4, 8, 12..23   (18 bytes)
    [0..3]   = 0x199254a0   T_init low32
    [4..7]   = 0x00000004   screenX = 4
    [8..11]  = 0x00000004   screenY = 4
    [12..15] = 0x199269eb   T_fg low32
    [16..19] = 0x199269eb   T_seed
    [20..23] = 0x199269eb   T_gen
    [24..255] all zero

Only 18 non-zero bytes rather than 24 because `screenX = screenY = 4`
occupies one byte each; the upper three bytes of each are zero.

This reading is independent of the LCG model: `base` comes from logged
outputs, not from a reconstructed stream. It therefore verifies the map
even when the generator family is unknown.

## Key extraction

After mixing, the pool keys ARC4:

    sr.init(sr.pool);           // KSA over all 256 bytes
    for (i = 0; i < 33; ++i)    // PRGA, 33 bytes
        ...

The private key is bytes `[1:33]` of that output, interpreted big-endian,
then mapped into the valid scalar range:

    key = (raw mod (N - 1)) + 1

where `N` is the secp256k1 group order. Byte 0 is discarded.

Confirmed against the WIF displayed by the page:
`5K43wan1bVeTyZCrAqBeztJfqD2otiGJR5QAohYy6iuRBjeRQRd`
-> `a2f369efbebdf8d21e1f5eb89fc84fd312bef406cec9bb31de741dbc32c7331b`.

## Bulk Wallet uses a different map

`buildCSV` generates on tab click and does **not** wait for `seedLimit`.
Its pool receives four XOR fields, not six:

    Single Wallet + forceGenerate : T_init, screenX, screenY, T_fg, T_seed, T_gen
    Bulk Wallet                   : T_init, screenX, screenY, T_gen

`T_gen` there is the click timestamp - a free parameter not derivable
from the seed. The published capture and verification cover the Single
Wallet path only. A model of the Bulk path would require an additional
unknown and is out of scope here.

## Firefox 6 Math.random

SpiderMonkey, 48-bit LCG:

    state = (state * 0x5DEECE66D + 0xB) mod 2^48
    next(bits): advance state, return state >> (48 - bits)
    nextDouble: (next(26) << 27) + next(27), divided by 2^53

Initial state is `(seed ^ 0x5DEECE66D) & (2^48 - 1)`, where
`seed = ms ^ P`:

- `ms` - `PRMJ_Now() / 1000` at JS context creation
- `P` - `cx ^ cx->link.next`, a pointer XOR

Two LCG steps per output. Verified across all 140 logged values.

**`ms` and `P` are not separable from output alone.** Only their XOR is
determined. This bounds `delta = T_init - ms` but does not fix it. See
`FINDINGS.md`.
