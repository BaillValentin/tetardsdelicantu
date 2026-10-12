"""Find candidate Commons photos per species, download previews + contact sheets.
Run in GitHub Actions (Commons is reachable there)."""
import json, re, sys, io, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "especes-corse-flashcards/1.0 (https://github.com/BaillValentin)"}
OK_LIC = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [0-9.]+|cc by(-sa)?[- ][0-9.]+.*)", re.I)
ALIASES = {
    "Peltodoris atromaculata": ["Discodoris atromaculata"],
    "Caulerpa cylindracea": ["Caulerpa racemosa var. cylindracea", "Caulerpa racemosa"],
    "Flabellina affinis": ["Paraflabellina affinis"],
    "Sphyraena viridensis": ["Sphyraena"],
    "Reteporella grimaldii": ["Sertella septentrionalis", "Reteporella"],
    "Hippocampus guttulatus": ["Hippocampus ramulosus"],
    "Cratena peregrina": ["Hervia peregrina"],
}
BAD = re.compile(r"\b(dead|market|march[eé]|mercado|museum|mus[eé]e|specimen|drawing|illustration|plate|fossil|map|distribution|skeleton|stamp|cooked|food|dish|plat|fried|frozen|fishmonger|poissonnerie|herbarium|preserved|catch|caught|fisherm|aquarium|aquário|acquario|tank|lithograph|engraving|diagram|svg|book|page)\b", re.I)
GOOD = re.compile(r"(underwater|sous-marin|diving|plong|scuba|snorkel|reef|in situ|habitat|seabed|corse|corsica|mediterr|m[eé]diterran)", re.I)

def get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("retry", e, file=sys.stderr); time.sleep(2 + 3 * i)
    raise SystemExit("API failed")

def strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()

def titles_for(name):
    titles = []
    for cat in [name]:
        d = get({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat,
                 "cmtype": "file", "cmlimit": "200"})
        titles += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
    d = get({"action": "query", "list": "search", "srsearch": f'"{name}" filetype:bitmap',
             "srnamespace": "6", "srlimit": "60"})
    titles += [m["title"] for m in d.get("query", {}).get("search", [])]
    seen = []
    for t in titles:
        if t not in seen and re.search(r"\.(jpe?g|png|webp|tiff?)$", t, re.I):
            seen.append(t)
    return seen

def info(titles):
    out = []
    for i in range(0, len(titles), 40):
        d = get({"action": "query", "titles": "|".join(titles[i:i+40]), "prop": "imageinfo|categories",
                 "iiprop": "url|size|extmetadata|mime", "iiurlwidth": "900", "cllimit": "max",
                 "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription|Credit|Categories"})
        for p in d["query"]["pages"]:
            if "imageinfo" not in p: continue
            ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
            lic = em.get("LicenseShortName", {}).get("value", "")
            cats = " ".join(c["title"] for c in p.get("categories", []))
            out.append({"title": p["title"], "w": ii["width"], "h": ii["height"],
                        "license": lic, "artist": strip(em.get("Artist", {}).get("value", "")),
                        "desc": strip(em.get("ImageDescription", {}).get("value", ""))[:300],
                        "cats": cats[:1500], "page": ii["descriptionurl"], "thumb": ii.get("thumburl"),
                        "orig": ii["url"]})
    return out

def score(c):
    text = " ".join([c["title"], c["desc"], c["cats"]])
    s = 0
    if GOOD.search(text): s += 5
    s += len(GOOD.findall(text)) * 0.5
    if BAD.search(c["title"] + " " + c["desc"]): s -= 10
    if BAD.search(c["cats"]): s -= 4
    if c["w"] >= 1200: s += 1
    ar = c["w"] / max(c["h"], 1)
    if ar > 2.2 or ar < 0.5: s -= 3
    return s

def extra(n=16):
    """Targeted searches from tools/extra_queries.tsv (slug<TAB>search query)."""
    out = {}
    for line in open("tools/extra_queries.tsv", encoding="utf-8"):
        slug, q = line.rstrip("\n").split("\t")
        d = get({"action": "query", "list": "search", "srsearch": q + " filetype:bitmap",
                 "srnamespace": "6", "srlimit": "40"})
        ts = [m["title"] for m in d.get("query", {}).get("search", [])]
        if q.startswith("incategory:") is False and not ts: continue
        out.setdefault(slug, []).extend(ts)
    for slug, ts in out.items():
        cands = [c for c in info(list(dict.fromkeys(ts))) if OK_LIC.match(c["license"].strip()) and c["w"] >= 700 and c["thumb"]]
        for c in cands: c["score"] = score(c)
        cands.sort(key=lambda c: -c["score"])
        sheet(slug + "-extra", cands[:n], rows=4)
        json.dump(cands[:n], open(f"candidates/{slug}-extra.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def sheet(name, top, rows=2):
    thumbs = []
    for k, c in enumerate(top):
        try:
            url = c["thumb"].replace("/900px-", "/300px-")
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                im = Image.open(io.BytesIO(r.read())).convert("RGB")
            im.thumbnail((300, 300)); thumbs.append((k, im))
        except Exception as e:
            print("  thumb fail", c["title"], e)
        time.sleep(0.3)
    img = Image.new("RGB", (4 * 310, rows * 330), "white")
    dr = ImageDraw.Draw(img)
    for k, im in thumbs:
        x, y = (k % 4) * 310, (k // 4) * 330
        img.paste(im, (x + 5, y + 25)); dr.text((x + 5, y + 5), f"#{k} {top[k]['license']}", fill="black")
    img.save(f"candidates/{name}.jpg", quality=80)

def main(only=None, n=8):
    sheets = {}
    for line in open("tools/species.tsv", encoding="utf-8"):
        slug, fr, latin = line.rstrip("\n").split("\t")
        if only and slug not in only: continue
        cands = []
        for name in [latin] + ALIASES.get(latin, []):
            ts = titles_for(name)
            cands += info(ts)
            if len(cands) >= 15: break
        uniq = {c["title"]: c for c in cands}
        cands = [c for c in uniq.values() if OK_LIC.match(c["license"].strip()) and c["w"] >= 700 and c["thumb"]]
        for c in cands: c["score"] = score(c)
        cands.sort(key=lambda c: -c["score"])
        top = cands[:n]
        print(slug, len(uniq), "->", len(cands), "licensed;", [round(c["score"], 1) for c in top], flush=True)
        thumbs = []
        for k, c in enumerate(top):
            try:
                url = c["thumb"].replace("/900px-", "/300px-")
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    im = Image.open(io.BytesIO(r.read())).convert("RGB")
                im.thumbnail((300, 300)); thumbs.append((k, im))
            except Exception as e:
                print("  thumb fail", c["title"], e)
            time.sleep(0.3)
        sheet = Image.new("RGB", (4 * 310, 2 * 330), "white")
        dr = ImageDraw.Draw(sheet)
        for k, im in thumbs:
            x, y = (k % 4) * 310, (k // 4) * 330
            sheet.paste(im, (x + 5, y + 25)); dr.text((x + 5, y + 5), f"#{k} {top[k]['license']}", fill="black")
        sheet.save(f"candidates/{slug}.jpg", quality=80)
        sheets[slug] = {"fr": fr, "latin": latin, "candidates": top}
    json.dump(sheets, open("candidates/candidates.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    import os; os.makedirs("candidates", exist_ok=True)
    if sys.argv[1:] == ["extra"]: extra()
    else: main(sys.argv[1:] or None)
