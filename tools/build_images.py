"""Download the selected Commons photos, resize/compress them, and regenerate
images/, CREDITS.md, the card list in index.html and the cache list in sw.js.
Run in GitHub Actions (Commons is reachable there)."""
import json, re, io, time, hashlib, urllib.parse, urllib.request
from PIL import Image, ImageOps

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "especes-corse-flashcards/1.0 (https://github.com/BaillValentin)"}
OK_LIC = re.compile(r"^(cc0|public domain|pd|cc by(-sa)?[- ][0-9.]+)", re.I)

def fetch(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read()
        except Exception as e:
            print("retry", url, e); time.sleep(3 + 4 * i)
    raise SystemExit("download failed: " + url)

def strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()

species = [l.rstrip("\n").split("\t") for l in open("tools/species.tsv", encoding="utf-8")]
selection = json.load(open("tools/selection.json", encoding="utf-8"))
cards, credits, assets = [], [], []
for slug, fr, latin in species:
    title = selection[slug]
    q = urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2", "titles": title,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "900",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist"})
    page = json.loads(fetch(API + "?" + q))["query"]["pages"][0]
    ii = page["imageinfo"][0]; em = ii["extmetadata"]
    lic = em["LicenseShortName"]["value"].strip()
    assert OK_LIC.match(lic), (slug, title, lic)
    author = strip(em.get("Artist", {}).get("value", "")) or "Auteur inconnu"
    author = re.sub(r"\s*\(talk\)|\s*\(discussion\)", "", author)
    im = Image.open(io.BytesIO(fetch(ii.get("thumburl") or ii["url"])))
    im = ImageOps.exif_transpose(im).convert("RGB")
    if im.width > 900:
        im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    for q_ in (82, 76, 70, 64, 58, 50):
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q_, optimize=True, progressive=True)
        if buf.tell() < 195_000: break
    path = f"images/{slug}.jpg"
    open(path, "wb").write(buf.getvalue())
    print(slug, im.size, buf.tell() // 1024, "KB", lic, "|", author)
    cards.append({"fr": fr, "img": path, "author": f"{author} · {lic}"})
    credits.append(f"| {fr} (*{latin}*) | {author} | {lic} | [{title}]({ii['descriptionurl']}) |")
    assets.append(path)
    time.sleep(0.5)

open("CREDITS.md", "w", encoding="utf-8").write(
    "# Crédits photos\n\nToutes les photos proviennent de [Wikimedia Commons](https://commons.wikimedia.org) "
    "et sont sous licence libre. Elles ont été redimensionnées (900 px de large) et recompressées.\n\n"
    "| Espèce | Auteur | Licence | Fichier Commons |\n|---|---|---|---|\n" + "\n".join(credits) + "\n")

html = open("index.html", encoding="utf-8").read()
js = json.dumps(cards, ensure_ascii=False, indent=1)
html = re.sub(r"/\*CARDS\*/.*?/\*END\*/", lambda m: "/*CARDS*/" + js + "/*END*/", html, flags=re.S)
open("index.html", "w", encoding="utf-8").write(html)

files = ["./", "index.html", "manifest.json", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"] + assets
h = hashlib.sha1()
for f in files[1:]: h.update(open(f, "rb").read())
sw = open("sw.js", encoding="utf-8").read()
sw = re.sub(r"const VERSION = '.*?';", f"const VERSION = '{h.hexdigest()[:10]}';", sw)
sw = re.sub(r"const ASSETS = \[.*?\];", "const ASSETS = " + json.dumps(files, indent=1) + ";", sw, flags=re.S)
open("sw.js", "w", encoding="utf-8").write(sw)
