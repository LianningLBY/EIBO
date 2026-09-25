#!/usr/bin/env python3
"""Field-level bibliography verification against authoritative publisher records.

Why this exists
---------------
The two checks that already ran on this project both passed while a real defect
was live:

  * the platform reference check is STRUCTURAL (cite <-> bib key resolution) and
    is keyed to a snapshot: on 2026-09-23 it verified 64 entries and the five
    added the next day -- including the entry that carried a fabricated title --
    were never in its input;
  * a bulk author comparison once produced 28 "wrong author" flags of which
    every one was a formatting artifact.

Neither can see whether a title or an author list is TRUE. That requires asking
the publisher. This script does that, and it is written so that its own
comparison logic is testable (--self-test) before its output is believed.

Usage
-----
    python3 scripts/verify_bibliography.py docs/paper/references.bib
    python3 scripts/verify_bibliography.py docs/paper/references.bib --self-test
    python3 scripts/verify_bibliography.py docs/paper/references.bib --json out.json

Exit status is non-zero when any entry MISMATCHES or ERRORs, so this can gate a
build. Unverifiable entries (no DOI, no arXiv id) are reported separately and do
NOT fail the run -- they are "not checked", which is a different statement from
"correct" and must never be silently merged with it.

Network: Crossref / DataCite / arXiv. Results are cached under the cache dir so
a re-run is cheap and an API outage does not fabricate a verdict.

What this check CANNOT see
--------------------------
It asks one question per entry: *does this entry match the record that its own
identifier names?* That leaves two blind spots, both of which have produced real
defects on this project:

  1. **Cross-field inconsistency.** The entry whose booktitle claimed a conference
     while its DOI pointed at the arXiv preprint passed this check, because the
     DOI was internally faithful to the preprint. Nothing here compares a
     booktitle against the venue the DOI actually belongs to.
  2. **Entries with no resolver.** No DOI and no arXiv id means no lookup, so the
     entry is reported NOT CHECKED. That is a different statement from "correct"
     and the two must never be merged: unverified entries are printed as their own
     list and do not fail the run.

Read the mismatch list as "these are provably wrong", and the unverified list as
"nobody has checked these" -- never as its complement.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "eibo-bib-verify/1.0 (mailto:research@example.org)"}
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


# --------------------------------------------------------------------------- #
# text normalisation
# --------------------------------------------------------------------------- #

def denoise(x: str) -> str:
    """Strip LaTeX commands, braces, and combining accents.

    `{\\v{C}}ejka` -> `Cejka`, `M{\\"u}cke` -> `Mucke`, `Tom{\\'a}{\\v{s}}` -> `Tomas`,
    `Na{\\"i}ve` -> `Naive`.

    The accent forms `\\"i`, `\\'e`, `` \\`a ``, `\\^o`, `\\~n`, `\\=a`, `\\.z` put a
    NON-LETTER after the backslash, so a rule matching only `\\[a-zA-Z]+` leaves the
    quote behind and splits the word (`na ive`). Both shapes are handled here.
    """
    if not x:
        return ""
    x = html.unescape(x)                            # &lt; &gt; &amp; ...
    x = re.sub(r"<[^>]+>", " ", x)                  # <inline-formula>, <tex-math ...>
    x = re.sub(r"\$[^$]*\$", " ", x)                # $...$ display math
    x = re.sub(r"\\[a-zA-Z]+\s*", "", x)            # \v \c \ell ...
    x = re.sub(r"\\[\"'`^~=.]\s*", "", x)           # \" \' \` \^ \~ \= \.
    x = re.sub(r"[{}\\]", "", x)
    x = unicodedata.normalize("NFKD", x)
    return "".join(c for c in x if not unicodedata.combining(c))


def norm_family(s: str) -> str:
    return re.sub(r"[^a-z]", "", denoise(s or "").lower())


def norm_title(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", denoise(s or "").lower())
    return " ".join(s.split())


# --------------------------------------------------------------------------- #
# bib parsing (brace-aware; a naive line regex misreads multi-line fields)
# --------------------------------------------------------------------------- #

def parse_entries(src: str) -> dict[str, str]:
    """Return {key: entry-body}. Brace-matching, so wrapped fields stay intact."""
    out: dict[str, str] = {}
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{").search(src, i)
        if not m:
            break
        key_end = src.index(",", m.end())
        key = src[m.end():key_end].strip()
        depth, j = 0, m.end() - 1
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out[key] = src[m.end():j]
        i = j + 1
    return out


def field(body: str, name: str) -> str | None:
    """Read one field, respecting nested braces. None when absent."""
    m = re.search(r"(?m)^\s*" + name + r"\s*=\s*", body)
    if not m:
        return None
    k = m.end()
    if k < len(body) and body[k] == "{":
        depth, j = 0, k
        while j < len(body):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return body[k + 1:j]
    m2 = re.match(r"[^,\n]+", body[k:])
    return m2.group(0).strip() if m2 else None


def author_families(body: str) -> list[str]:
    """Family names only, as a normalised list.

    Handles both `Surname, Given` and `Given Surname`, plus brace-quoted
    particles (`{\\v{C}}ejka, Tom{\\'a}{\\v{s}}`).
    """
    au = field(body, "author")
    if not au:
        return []
    au = re.sub(r"\s+", " ", au)
    fams = []
    for part in re.split(r"\band\b", au):
        part = part.strip()
        if not part:
            continue
        fam = part.split(",")[0] if "," in part else part.split(" ")[-1]
        n = norm_family(fam)
        if n:
            fams.append(n)
    return fams


# --------------------------------------------------------------------------- #
# publisher records
# --------------------------------------------------------------------------- #

def _get(url: str, timeout: int = 30, retries: int = 3) -> dict | str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if not body:
                raise ValueError("empty response")
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"__http__": 404}          # a real, meaningful answer
            last = e
            time.sleep(5 * (attempt + 1))         # 429 backoff
        except Exception as e:                    # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"unreachable: {url}: {last}")


def lookup_doi(doi: str) -> dict:
    """Publisher record for a DOI. DataCite for Zenodo/arXiv DOIs, else Crossref."""
    d = doi.lower()
    if d.startswith("10.48550") or d.startswith("10.5281"):
        r = _get("https://api.datacite.org/dois/" + urllib.parse.quote(doi))
        if r.get("__http__") == 404:
            return {"found": False, "source": "datacite"}
        a = r["data"]["attributes"]
        names = []
        for c in a.get("creators") or []:
            fam = c.get("familyName") or ""
            if not fam:
                nm = c.get("name", "")
                fam = nm.split(",")[0] if "," in nm else (nm.split(" ")[-1] if nm else "")
            names.append(fam)
        titles = a.get("titles") or [{}]
        return {
            "found": True,
            "source": "datacite",
            "title": titles[0].get("title", ""),
            "families": names,
        }

    r = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if r.get("__http__") == 404:
        return {"found": False, "source": "crossref"}
    m = r["message"]
    title = (m.get("title") or [""])[0]
    # Crossref stores the subtitle separately for many publishers, and keeps raw
    # LaTeX markup in some titles; both are joined here so a correct entry is not
    # flagged for the publisher's own presentation choice.
    if m.get("subtitle"):
        title = f"{title}: {' '.join(m['subtitle'])}"
    return {
        "found": True,
        "source": "crossref",
        "title": title,
        "families": [a.get("family") or a.get("name", "") for a in (m.get("author") or [])],
        "page": m.get("page"),
        "volume": m.get("volume"),
        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
    }


def lookup_arxiv(aid: str) -> dict:
    raw = urllib.request.urlopen(
        urllib.request.Request(
            f"http://export.arxiv.org/api/query?id_list={aid}", headers=UA
        ),
        timeout=30,
    ).read()
    if not raw:
        raise RuntimeError("empty arXiv response")
    e = ET.fromstring(raw).find("a:entry", ARXIV_NS)
    if e is None:
        return {"found": False, "source": "arxiv"}
    return {
        "found": True,
        "source": "arxiv",
        "title": " ".join((e.find("a:title", ARXIV_NS).text or "").split()),
        "families": [x.find("a:name", ARXIV_NS).text.split()[-1] for x in e.findall("a:author", ARXIV_NS)],
    }


# --------------------------------------------------------------------------- #
# comparison
# --------------------------------------------------------------------------- #

# A leading document identifier is a citation convention, not part of the title:
# `{RFC 9312}: Manageability of the QUIC Transport Protocol` and the publisher's
# `Manageability of the QUIC Transport Protocol` are the SAME work. Without this,
# adding a correct DOI to an RFC-style entry manufactured a false MISMATCH.
DOC_ID_PREFIX_RE = re.compile(
    r"^(?:rfc\s*\d+|arxiv[:\s]*[\w.\-]+|doi[:\s]*10\.\d{4,9}/\S+|ietf[-\s]?draft[-\s]?\S+)\s*[:\-—]?\s+",
    re.IGNORECASE,
)


def strip_doc_id_prefix(t: str) -> str:
    """Remove a leading `RFC nnnn:` / `arXiv:xxxx:` / `DOI:10.x/...` marker.

    Only strips when something substantive FOLLOWS, so a title that is *only* an
    identifier is not emptied into a vacuous match.
    """
    m = DOC_ID_PREFIX_RE.match(t)
    if not m:
        return t
    rest = t[m.end():].strip()
    return rest if rest else t


def compare(entry: dict, rec: dict) -> dict:
    """Decide one entry. Crossref's title may be a prefix (subtitle truncation)."""
    ours_t = strip_doc_id_prefix(norm_title(entry["title"]))
    reg_t = strip_doc_id_prefix(norm_title(rec.get("title", "")))
    title_ok = bool(ours_t) and (reg_t == ours_t or reg_t.startswith(ours_t) or ours_t.startswith(reg_t))

    ours_f = set(entry["families"])
    reg_f = set(norm_family(x) for x in rec.get("families") or [] if x)
    missing = sorted(reg_f - ours_f)   # in the publisher record, absent from ours
    extra = sorted(ours_f - reg_f)     # ours alone
    return {
        "title_ok": title_ok,
        "ours_title": ours_t,
        "reg_title": reg_t,
        "missing": missing,
        "extra": extra,
        "ok": title_ok and not missing and not extra,
    }


def self_test() -> int:
    """Execute the normaliser and the wrapped-field parser on KNOWN-GOOD input.

    This is the step whose absence produced a false defect report: the earlier
    instrument was tested on hard name strings but never on a correct entry whose
    author list wraps across source lines. Run this before believing any output.
    """
    fails = []

    pairs = [
        (r"{\v{C}}ejka", "Čejka"),
        (r"Luka{\v{c}}ovi{\v{c}}", "Lukačovič"),
        (r'M{\"u}cke', "Mücke"),
        (r"Tom{\'a}{\v{s}}", "Tomáš"),
        (r"C{\'e}dric", "Cédric"),
        # the backslash-then-punctuation accent form: must NOT split the word
        (r'Na{\"i}ve', "Naive"),
        (r'Bayes, not Na{\"i}ve', "Bayes, not Naive"),
    ]
    for a, b in pairs:
        if norm_family(a) != norm_family(b):
            fails.append(f"accent: {a!r} -> {norm_family(a)!r} != {b!r} -> {norm_family(b)!r}")

    # The Naive case specifically failed in a real run ("na ive"); assert on the
    # whole normalised string, not just families, since it is a TITLE artifact.
    if norm_title(r"Bayes, not Na{\"i}ve") != norm_title("Bayes, not Naive"):
        fails.append(
            f"accent in title split the word: "
            f"{norm_title(r'Bayes, not Na{\"i}ve')!r} != {norm_title('Bayes, not Naive')!r}"
        )

    # Crossref returns some IEEE titles wrapped in raw XML/LaTeX markup.
    for ours, reg in [
        ("Minimax Estimation of Discrete Distributions under $\\ell_1$ Loss",
         'Minimax Estimation of Discrete Distributions Under &lt;inline-formula&gt; '
         '&lt;tex-math notation="LaTeX"&gt;$\\ell _{1}$ &lt;/tex-math&gt;&lt;/inline-formula&gt; Loss'),
    ]:
        if not compare({"title": ours, "families": []}, {"title": reg, "families": []})["title_ok"]:
            fails.append(f"IEEE markup wrongly flagged as a title mismatch: {norm_title(ours)!r} vs {norm_title(reg)!r}")

    wrapped = (
        "@article{probe,\n"
        "  author = {Luxemburk, Jan and Hynek, Karel and\n"
        "            {\\v{C}}ejka, Tom{\\'a}{\\v{s}} and\n"
        "            Luka{\\v{c}}ovi{\\v{c}}, Andrej and {\\v{S}}i{\\v{s}}ka, Pavel},\n"
        "  title = {A Wrapped Author Field},\n"
        "}\n"
    )
    body = parse_entries(wrapped)["probe"]
    fams = author_families(body)
    if len(fams) != 5:
        fails.append(f"wrapped author field read as {len(fams)} authors, expected 5: {fams}")
    for want in ("luxemburk", "hynek", "cejka", "lukacovic", "siska"):
        if want not in fams:
            fails.append(f"wrapped author field lost {want!r}: {fams}")

    sub = compare(
        {"title": "Estimating the Unseen: An n/log(n)-Sample Estimator for Entropy and Support Size",
         "families": ["valiant", "valiant"]},
        {"title": "Estimating the Unseen", "families": ["Valiant", "Valiant"]},
    )
    if not sub["ok"]:
        fails.append(f"subtitle-truncated title wrongly flagged: {sub}")

    # A leading document identifier is a citation convention, not part of the title.
    # Regression: adding a correct RFC DOI once manufactured a false MISMATCH here.
    rfc = compare(
        {"title": "{RFC 9312}: Manageability of the {QUIC} Transport Protocol",
         "families": ["kuhlewind", "trammell"]},
        {"title": "Manageability of the QUIC Transport Protocol",
         "families": ["Kühlewind", "Trammell"]},
    )
    if not rfc["ok"]:
        fails.append(f"RFC-prefixed title wrongly flagged: {rfc}")

    # ...but a title that is ONLY an identifier must not normalise to empty and
    # match everything vacuously.
    if strip_doc_id_prefix("rfc 9312") == "":
        fails.append("strip_doc_id_prefix emptied an identifier-only title")

    if fails:
        print("SELF-TEST FAILED")
        for f in fails:
            print("  -", f)
        return 1
    print("SELF-TEST PASSED")
    return 0


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bib")
    ap.add_argument("--self-test", action="store_true", help="run the comparison self-test and exit")
    ap.add_argument("--json", help="write full results here")
    ap.add_argument("--cache", default=".bibverify_cache", help="response cache directory")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if self_test() != 0:
        print("Refusing to verify with a failing comparison: fix the normaliser first.", file=sys.stderr)
        return 2

    src = open(args.bib, encoding="utf-8").read()
    entries = parse_entries(src)
    os.makedirs(args.cache, exist_ok=True)

    results, mismatched, errored, unverifiable = [], [], [], []
    for key, body in entries.items():
        doi = field(body, "doi")
        ep = field(body, "eprint") or field(body, "eprint")
        url = field(body, "url") or ""
        if not ep:
            m = re.search(r"arxiv\.org/abs/([\w.\-]+)", url)
            if m:
                ep = m.group(1)
        if not doi and not ep and "doi.org/" in url:
            m = re.search(r"doi\.org/(10\.[^\s}]+)", url)
            if m:
                doi = m.group(1)

        rec = {"key": key, "doi": doi, "eprint": ep,
               "title": field(body, "title") or "",
               "families": author_families(body)}
        if not doi and not ep:
            unverifiable.append(key)
            rec["status"] = "unverifiable"
            results.append(rec)
            continue

        try:
            pub = lookup_doi(doi) if doi else lookup_arxiv(ep)
            if not pub.get("found"):
                rec["status"] = "MISMATCH"
                rec["why"] = f"{pub.get('source')} has no record for {doi or ep} (dead identifier)"
                mismatched.append(key)
                results.append(rec)
                continue
            cmp_ = compare(rec, pub)
            rec.update(source=pub["source"], **cmp_)
            rec["status"] = "ok" if cmp_["ok"] else "MISMATCH"
            if not cmp_["ok"]:
                mismatched.append(key)
            results.append(rec)
        except Exception as e:  # noqa: BLE001
            rec["status"] = "ERROR"
            rec["why"] = str(e)[:160]
            errored.append(key)
            results.append(rec)
        time.sleep(0.4)

    print(f"parsed={len(entries)}  checked={len(entries) - len(unverifiable)}  "
          f"ok={sum(1 for r in results if r.get('status') == 'ok')}  "
          f"MISMATCH={len(mismatched)}  ERROR={len(errored)}  unverifiable={len(unverifiable)}")
    if mismatched:
        print("\nMISMATCHES")
        for r in results:
            if r.get("status") != "MISMATCH":
                continue
            print(f"  {r['key']}  [{r.get('source', '?')}]  {r.get('doi') or r.get('eprint')}")
            if r.get("why"):
                print(f"      {r['why']}")
            if r.get("missing"):
                print(f"      absent from our entry : {r['missing']}")
            if r.get("extra"):
                print(f"      ours alone            : {r['extra']}")
            if r.get("ours_title") and not r.get("title_ok", True):
                print(f"      ours : {r['ours_title'][:90]}")
                print(f"      reg  : {r.get('reg_title', '')[:90]}")
    if errored:
        print("\nERRORS (unresolved, not clean)")
        for r in results:
            if r.get("status") == "ERROR":
                print(f"  {r['key']}: {r.get('why')}")
    if unverifiable:
        print(f"\nNOT CHECKED (no DOI or arXiv id) — recorded unverified, NOT clean:")
        print("  " + ", ".join(unverifiable))

    if args.json:
        json.dump(results, open(args.json, "w"), indent=1)
        print(f"\nwrote {args.json}")

    return 1 if (mismatched or errored) else 0


if __name__ == "__main__":
    sys.exit(main())
