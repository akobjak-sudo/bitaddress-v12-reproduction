#!/usr/bin/env python3
"""
Instrument bitaddress.org v1.2 with passive entropy hooks.

Input : ba12.html   (upstream source, commit 132f70cd)
Output: ba12_inst.html

Three hooks are inserted. None consumes additional Math.random calls,
so the captured stream is exactly what the page itself would have used.

Usage:
    python3 tools/inject.py <path-to-ba12.html> <output-dir>

Upstream source:
https://raw.githubusercontent.com/pointbiz/bitaddress.org/132f70cd457fe1865316a57d7bc9f5d166fc2e33/bitaddress.org.html
"""
import io, os, re, sys

HOOK = """<script>
window.__L={mr:[],st:[],si:[],ua:navigator.userAgent,av:navigator.appVersion};
(function(){var o=Math.random;Math.random=function(){var v=o();
 if(window.__L.mr.length<200)window.__L.mr.push(v);return v;};})();
window.__L.t_head=Date.now();
</script>"""

POST = """<script>
window.__L.t_after_sr=Date.now();
window.__L.sx=window.screenX; window.__L.sy=window.screenY;
window.__L.hasCrypto=!!(window.crypto&&window.crypto.getRandomValues);
(function(){
 var t=SecureRandom.seedTime;
 SecureRandom.seedTime=function(){window.__L.st.push(Date.now());return t();};
 var i=SecureRandom.seedInt;
 SecureRandom.seedInt=function(x){window.__L.si.push(x);return i(x);};
 var af=SecureRandom.ArcFour;
 SecureRandom.ArcFour=function(){
   var o=af(); var oi=o.init;
   o.init=function(k){ if(!window.__L.pool) window.__L.pool=k.slice(0); return oi.call(this,k); };
   return o;
 };
})();
</script>"""

DUMP = """<script>
setTimeout(function(){
 var L=window.__L; L.t_dump=Date.now();
 L.addr=(document.getElementById('btcaddress')||{}).innerHTML||"";
 var pk=document.getElementById('btcprivwif')||document.getElementById('privkey');
 L.priv=pk?(pk.innerHTML||pk.value||""):"";
 var ta=document.createElement('textarea'); ta.rows=26; ta.cols=110;
 ta.value=JSON.stringify(L);
 document.body.insertBefore(ta,document.body.firstChild);
},15000);
</script>"""


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, outdir = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        print(f"ERROR: source not found: {src}")
        return 1
    s = io.open(src, encoding="utf-8", errors="ignore").read()

    # HOOK before the first <script>, so Math.random is wrapped before any use.
    i = s.find("<script")
    if i < 0:
        print("ERROR: no <script> in source")
        return 1
    s = s[:i] + HOOK + s[i:]

    # POST after the block that DEFINES SecureRandom.
    # Anchor on the definition, not on the first mention of the name:
    # the first occurrence is inside a licence comment in <head>.
    m = re.search(r"var\s+sr\s*=\s*window\.SecureRandom", s)
    if not m:
        print("ERROR: SecureRandom definition not found")
        return 1
    j = s.find("</script>", m.end())
    if j < 0:
        print("ERROR: unterminated script block")
        return 1
    j += len("</script>")
    s = s[:j] + POST + s[j:]

    if "</body>" not in s:
        print("ERROR: no </body>")
        return 1
    s = s.replace("</body>", DUMP + "</body>")

    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "ba12_inst.html")
    io.open(out, "w", encoding="utf-8").write(s)
    print(f"OK -> {out}")
    print("Launch with the FF6 binary directly, file path as its argument:")
    print('  "<ff6>\\firefox.exe" -no-remote -profile "<prof>" "file:///<out>"')
    print("Do not double-click the HTML: it opens in the default browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())