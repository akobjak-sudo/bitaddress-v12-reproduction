# bitaddress.org v1.2 - Independent Entropy Reproduction

End-to-end reproduction of the Randstorm-class entropy failure in
bitaddress.org v1.2 (commit `132f70cd`) under Firefox 6, verified against
a live browser capture.

**This is a reproduction, not a discovery.** Randstorm was disclosed by
Unciphered in 2023. The contribution here is a byte-exact, independently
verified model of the mechanism, plus the instrumentation methodology
that produced it.

**This repository contains no address-search tooling.** There is no
target list, no filter over third-party addresses, and no key
recovery against addresses the author does not own. See Scope below.

## Quick start

    python3 verify_composition.py

Python 3 standard library only. No GPU, no network, no dependencies.
Expected result:

    [0] Capture gate            all OK
    [1] seed48 = 1795725348970  stream 140/140 OK
    [2] T_init = 1795725350048  seedLimit 270  jitter 51 ms
    [3] pool match: 256/256
    [4] key: PASS
    [5] addr: PASS
    RESULT: COMPOSITION PASS

## What is verified

| Component | Method | Result |
|---|---|---|
| SpiderMonkey LCG-48 state recovery | 140 logged Math.random values from live FF6 | 140/140 exact |
| SecureRandom pool reconstruction | 128 calls x 2 bytes + 6 XOR fields | 256/256 bytes |
| seedLimit = 50 + floor(256 * mr[139]) | source + capture | 270, timeout 5400 ms |
| ARC4 KSA -> 33 bytes -> [1:33] -> +1 mod (N-1) | against WIF displayed by the page | exact key match |
| secp256k1 -> HASH160 -> Base58Check | against address displayed by the page | exact address match |
| Pool XOR map, offsets 0/4/8/12/16/20 | direct mask read from captured pool | confirmed |

Details: `docs/POOL_MAP.md`, `docs/FINDINGS.md`.

## What is NOT verified

Stated plainly, because overclaiming is how this class of research loses
credibility.

- **ms and P are not separable.** The stream determines only
  `seed48 = ms ^ P`. The context-creation timestamp and the pointer XOR
  cannot be recovered individually from output alone. Consequently
  `delta = T_init - ms` is bounded, not pinned.
- **Environment parameters are session properties, not model constants.**
  screenX, screenY, timer jitter and delta were measured on one machine
  (Win7, FF6). They do not transfer. Three such errors were made and
  documented in `docs/FINDINGS.md`.
- **Other browsers.** A Firefox 149 capture confirmed the pool map and
  key derivation, but FF149's Math.random is not LCG-48 - zero LCG
  candidates from the logged stream. The LCG layer is FF6-specific.
- **Other PRNG families.** MWC1616/MSVCRT and glibc LCG models exist as
  synthetic selftests only. No historical target was identified. Claims
  of multi-browser verification made in earlier correspondence are
  withdrawn pending published artifacts.
- **Bulk Wallet path.** It uses a different pool map (four XOR fields,
  not six) and a click timestamp that is not derivable from the seed.
  Out of scope here.

## Scope

In scope:

- Reproducing a known vulnerability class on a wallet the researcher
  generates themselves
- Documenting the mechanism and its parameters
- Instrumentation methodology for entropy provenance research

Out of scope, not present in this repository, and not planned:

- Searching public address space for private keys
- Recovery against addresses not owned by the researcher
- Ingestion of funded historical address sets

## Repository contents

    verify_composition.py              self-contained verification
    capture/ff6_win7_bitaddress_v12.json   raw capture, ground truth
    tools/inject.py                   passive instrumentation generator
    docs/POOL_MAP.md                  source-derived pool layout
    docs/FINDINGS.md                  measurements and limits
    docs/CAPTURE_PROTOCOL.md          how to reproduce the capture

## Test vector warning

`capture/ff6_win7_bitaddress_v12.json` contains a private key. It is a
throwaway research wallet generated in a controlled Firefox 6 session for
this experiment. It has never been funded and must never be funded. It is
published solely so the reproduction can be independently checked.

Do not send funds to `17QGPY8QNrpyNJVTT4ptKwZrVGkxD99odz`.

## Source reference

bitaddress.org v1.2, commit
`132f70cd457fe1865316a57d7bc9f5d166fc2e33`:

    seedLimit: (function () {
        var num = Crypto.util.randomBytes(12)[11];
        return 50 + Math.floor(num);
    })(),
    ...
    setTimeout(ninja.wallets.singlewallet.forceGenerate, ninja.seedLimit * 20);

`140 = 128 + 12`: 128 calls fill the 256-byte pool two bytes at a time,
12 calls feed `randomBytes(12)`.

## Related work

- Randstorm - Unciphered, 2023
- Milk Sad, CVE-2023-39910 - libbitcoin Explorer
- CVE-2026-71851 - CryptoJS WordArray.random(), Coinspect "Ill Bloom"
- Coldcard firmware 4.0.1 entropy fallback, exploited July 2026

The last two share the root cause reproduced here: silent fallback from a
CSPRNG to a weak software PRNG, with no signal to user or developer.

## License

Apache-2.0. See LICENSE.
