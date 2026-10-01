"""Shared helpers for the context_*.py scripts (value-context data).

- fetch(): download a URL once into raw/context/ (gitignored) and reuse it.
- pdf_text(): PDF -> text with pypdf, cached next to the PDF.
- norm(): collapse whitespace so quotes can be matched across line breaks.
- socrata(): small Socrata SODA query helper with a hard timeout.
"""
import html
import json
import os
import re
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "raw", "context")
DATA = os.path.join(ROOT, "data")
UA = "Mozilla/5.0 (chicagoBudget research script)"

os.makedirs(RAW, exist_ok=True)
os.makedirs(DATA, exist_ok=True)


def raw_path(name):
    return os.path.join(RAW, name)


def fetch(url, name, timeout=120, force=False):
    """Download url to raw/context/<name> unless already cached. Returns path."""
    path = raw_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if force or not os.path.exists(path) or os.path.getsize(path) == 0:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        with open(path, "wb") as f:
            f.write(body)
    return path


def read_text(path):
    with open(path, "r", errors="ignore") as f:
        return f.read()


def html_text(path):
    t = read_text(path)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return norm(html.unescape(t))


def pdf_text(pdf_path):
    """Extract text from a PDF (cached as <pdf>.txt). Needs pypdf."""
    txt_path = pdf_path[:-4] + ".txt" if pdf_path.endswith(".pdf") else pdf_path + ".txt"
    if not os.path.exists(txt_path) or os.path.getsize(txt_path) == 0:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        pages = [(p.extract_text() or "") for p in reader.pages]
        with open(txt_path, "w") as f:
            f.write("\n=====PAGE=====\n".join(pages))
    return read_text(txt_path)


def norm(s):
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()


def socrata(dataset, params, timeout=110, domain="data.cityofchicago.org", tries=4, cache=None):
    """SODA query with retries. If cache (a filename in raw/context) is given, the
    result is saved there and reused when the live API keeps failing."""
    import time
    url = "https://%s/resource/%s.json?%s" % (domain, dataset, urllib.parse.urlencode(params))
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf8"))
            if cache:
                with open(raw_path(cache), "w") as f:
                    json.dump(data, f)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    if cache and os.path.exists(raw_path(cache)):
        print("WARNING: live API failed (%s), using cached %s" % (last, cache))
        with open(raw_path(cache)) as f:
            return json.load(f)
    raise last


def write_json(name, obj):
    path = os.path.join(DATA, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote", os.path.relpath(path, ROOT))
    return path


def load_json(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def money(s):
    """'$1,234,567.89' or '1234567' -> float. Trailing sentence periods are dropped."""
    t = re.sub(r"[^0-9.\-]", "", str(s)).rstrip(".")
    return float(t)
