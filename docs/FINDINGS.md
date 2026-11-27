# Findings

Capture: Firefox 6.0, Windows NT 6.1 (32-bit), `hasCrypto: false`
Target: bitaddress.org v1.2, commit `132f70cd`
Path: Single Wallet, `forceGenerate`, mouse not moved

## Measured values

| Quantity | Value |
|---|---|
| `seed48 = ms ^ P` | 1795725348970 (`0x1a21992506a`) |
| `T_init` | 1795725350048 |
| `T_fg` = `T_seed` = `T_gen` | 1795725355499 |
| `screenX`, `screenY` | 4, 4 |
| `seedLimit` | 270 |
| timeout (`seedLimit * 20`) | 5400 ms |
| timer jitter | 51 ms |
| `T_init - seed48` | 1078 ms |
| `t_head` | 1795725350043 |
| `t_after_sr` | 1795725350049 |

All three `seedTime()` calls landed in the same millisecond on this
machine. That is a property of this session, not a guarantee.

## Finding 1 - T_init is not the hook timestamp

`t_after_sr` is recorded immediately after the SecureRandom block.
`T_init` is the value `seedTime()` returned during pool initialisation.
They differ:

    t_after_sr = 1795725350049
    T_init     = 1795725350048      (-1 ms)

Using `t_after_sr` as `T_init` yields a **255/256** pool match and a
completely different key. One byte wrong in the XOR is enough.

`T_init` must be read from the mask at offset 0, never inferred from a
hook timestamp. `verify_composition.py` derives it that way.

## Finding 2 - ms and P are not separable

The output stream determines `seed48 = ms ^ P` and nothing more. With
`P < 2^13`, `ms` lies somewhere in the 8192-ms block containing `seed48`.
Combined with the constraint `ms <= T_init`:

    delta = T_init - ms, in [0, 5280] ms

For `P` in the band observed on this platform (`0x1000`-`0x10D6`),
delta is approximately 5.1-5.3 s.

**Consequence.** Delta is bounded but not fixed by any amount of captured
output. A search that assumes a single delta value covers one slice of a
range thousands of milliseconds wide.

## Finding 3 - environment parameters do not transfer

Values measured in one session were initially assumed to hold in
another. They did not:

| Parameter | Assumed (Win10 / FF149 session) | Measured (Win7 / FF6) |
|---|---|---|
| `screenX`, `screenY` | -8, -8 | +4, +4 |
| timer jitter | 0-25 ms | 51 ms |
| delta | 30 ms | seconds |

Three independent errors. Each alone is sufficient to produce zero
matches.

**A null result obtained under incorrect environment parameters carries
no information about whether the model is correct.** This is the main
methodological finding of this work.

## Finding 4 - P depends on heap layout

`P = cx ^ cx->link.next` is a pointer XOR inside SpiderMonkey. The band
`0x1000`-`0x10D6` was observed on Win7 32-bit. It is not a constant of
the algorithm and does not transfer across machines, builds, or
allocator states.

The verification script measures `seed48` directly and never assumes a
value for `P`.

## Finding 5 - the generator family is browser-specific

A second capture, taken in Firefox 149 against the same bitaddress v1.2
source, confirmed the pool map and the key derivation. But its
`Math.random` output yielded **zero** LCG-48 candidates: modern
SpiderMonkey does not use this generator.

The LCG layer of this model is specific to Firefox 6-era SpiderMonkey.
The pool map and ARC4 extraction are properties of bitaddress and hold
independently of the browser.

## What this reproduction does not establish

- No private key of any third party was recovered or sought.
- No claim is made about which historical wallets used which parameters.
- MWC1616/MSVCRT and glibc LCG models exist as synthetic selftests only;
  no historical target was identified for either.
- Earlier correspondence claimed multi-browser verification
  (Chrome 27, Firefox 22, IE 8, Opera 12.15). Those artifacts are not
  published here and the claim is withdrawn.

## Why this class still matters

The mechanism reproduced here - a CSPRNG path silently degrading to a
weak software PRNG, with no signal to user or developer - is not
historical:

- **CVE-2026-71851**, CryptoJS `WordArray.random()`: an MWC variant
  seeded from `Math.random()`, present across the 3.x line. Nominal
  128/256-bit requests produced ~2^39/~2^47 effective spaces.
- **Coldcard firmware 4.0.1**: a build-configuration error routed seed
  generation away from hardware entropy. Effective strength fell from
  128 bits to as low as 40 on older devices.

Both shipped undetected for years. Neither required a cryptanalytic
break - only an unverified assumption about which entropy source was
actually reached.
