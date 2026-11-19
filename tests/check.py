"""코드 검사 (단순 수정 때 돌리는 1단계 검사).  python3 tests/check.py
1) 자바스크립트 문법  2) HTML 태그 짝  3) onclick 등이 부르는 함수가 있는지  4) 판 번호
"""
import re, sys, subprocess, pathlib, tempfile
from html.parser import HTMLParser
ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
RES = []
def check(n, ok, info=""): RES.append((n, bool(ok), info))
scripts = re.findall(r"<script>([\s\S]*?)</script>", HTML)
js = "\n;\n".join(scripts)
with tempfile.TemporaryDirectory() as d:
    for label, code in {"index.html 스크립트": js, "config.js": (ROOT / "config.js").read_text(encoding="utf-8")}.items():
        f = pathlib.Path(d) / "c.js"; f.write_text(code, encoding="utf-8")
        r = subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", str(f)], capture_output=True, text=True)
        e = r.stderr.strip().splitlines() or [""]
        check("문법: " + label, r.returncode == 0, next((l for l in e if "Error" in l), e[-1]))
class T(HTMLParser):
    VOID = {"br", "img", "input", "meta", "link", "hr"}
    def __init__(s): super().__init__(); s.st = []; s.bad = []
    def handle_starttag(s, t, a):
        if t not in s.VOID: s.st.append((t, s.getpos()[0]))
    def handle_endtag(s, t):
        if t in s.VOID: return
        if s.st and s.st[-1][0] == t: s.st.pop()
        else: s.bad.append(f"</{t}>({s.getpos()[0]}줄)")
static = re.sub(r"<script[\s\S]*?</script>", "<script></script>", HTML)
static = re.sub(r"<style[\s\S]*?</style>", "<style></style>", static)
t = T(); t.feed(static)
left = [f"{a}({b}줄)" for a, b in t.st if a not in {"html", "body", "head"}]
check("HTML 태그 짝", not t.bad and not left, "; ".join(t.bad + left))
defined = set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", js)) | set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", js))
called = set()
for h in re.findall(r'on(?:click|change|input|keydown)=\\?["\']([^"\']*)', HTML):
    for fn in re.findall(r"(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(", h):
        called.add(fn)
skip = {"if", "return", "event", "setTimeout", "document", "this"}
missing = sorted(c for c in called - skip if c not in defined)
check("단추가 부르는 함수", not missing, ", ".join(missing))
vs = re.findall(r'APP_VERSION\s*=\s*"([\d.]+)"', HTML)
check("판 번호", len(vs) == 1, ", ".join(vs))
bad = [r for r in RES if not r[1]]
for n, ok, info in RES: print(("통과 " if ok else "실패 ") + n + ("" if ok or not info else " :: " + info))
print("FAIL" if bad else "OK"); sys.exit(1 if bad else 0)
