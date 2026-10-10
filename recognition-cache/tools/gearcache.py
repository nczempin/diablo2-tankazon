#!/usr/bin/env python3
"""D2R gear-recognition cache: add reference images, match query images.

Cache layout (CACHE root, default ./recognition-cache):
  index.json            list of entries {name, category, file, sha256, phash, dhash, source, added}
  sources.json          curated source allowlist {domain_or_repo: note}
  <category>/<slug>-<sha8>.png
Categories: rune, gem, helm, armor, shield, weapon, gloves, belt, boots, ring, amulet, charm, jewel, misc.
"""
import argparse, hashlib, json, os, re, sys, datetime
from PIL import Image
import imagehash

CATS = "rune gem helm armor shield weapon gloves belt boots ring amulet charm jewel misc".split()

def root(a): return os.path.abspath(a.cache)
def load(r):
    p = os.path.join(r, "index.json")
    return json.load(open(p)) if os.path.exists(p) else []
def save(r, idx):
    json.dump(idx, open(os.path.join(r, "index.json"), "w"), indent=1, sort_keys=True)

def norm(img):
    """Trim near-black border (inventory slot background), convert to RGB."""
    img = img.convert("RGB")
    g = img.convert("L").point(lambda v: 255 if v > 28 else 0)
    box = g.getbbox()
    return img.crop(box) if box else img

def hashes(img):
    n = norm(img)
    return str(imagehash.phash(n)), str(imagehash.dhash(n)), n

def crop_arg(img, c):
    if not c: return img
    x, y, w, h = map(int, c.split(","))
    return img.crop((x, y, x + w, y + h))

def cmd_add(a):
    r = root(a); idx = load(r)
    if a.category not in CATS: sys.exit(f"category must be one of {CATS}")
    img = crop_arg(Image.open(a.image), a.crop)
    ph, dh, n = hashes(img)
    os.makedirs(os.path.join(r, a.category), exist_ok=True)
    buf = n.tobytes() + str(n.size).encode()
    sha = hashlib.sha256(buf).hexdigest()
    if any(e["sha256"] == sha for e in idx):
        print("duplicate (sha256 already cached)"); return
    slug = re.sub(r"[^a-z0-9]+", "-", a.name.lower()).strip("-")
    rel = f"{a.category}/{slug}-{sha[:8]}.png"
    n.save(os.path.join(r, rel))
    idx.append(dict(name=a.name, category=a.category, file=rel, sha256=sha, phash=ph, dhash=dh,
                    source=a.source, status=a.status, added=datetime.date.today().isoformat()))
    save(r, idx); print("added", rel)

def dist(h1, h2): return imagehash.hex_to_hash(h1) - imagehash.hex_to_hash(h2)

def cmd_confirm(a):
    r = root(a); idx = load(r)
    hits = [e for e in idx if e["file"] == a.file]
    if not hits: sys.exit("no such file in index")
    e = hits[0]; e["name"] = a.name; e["status"] = "confirmed"
    save(r, idx); print("confirmed", a.file, "as", a.name)

def cmd_match(a):
    r = root(a); idx = [e for e in load(r) if not a.category or e["category"] == a.category]
    if not idx: print("CACHE MISS: no references for", a.category or "any category"); return
    img = crop_arg(Image.open(a.image), a.crop)
    ph, dh, _ = hashes(img)
    scored = sorted(((dist(ph, e["phash"]) + dist(dh, e["dhash"]), e) for e in idx), key=lambda t: t[0])
    for d, e in scored[: a.top]:
        st = "" if e.get("status", "confirmed") == "confirmed" else "  (PENDING name)"
        print(f"{d:3d}  {e['name']}  [{e['category']}]  {e['file']}{st}")
    best = scored[0][0]
    if best > a.threshold:
        print(f"WEAK MATCH (best distance {best} > {a.threshold}): treat as cache miss")

def cmd_grid(a):
    img = Image.open(a.image)
    x0, y0, cw, ch, cols, rows = map(int, a.grid.split(","))
    os.makedirs(a.out, exist_ok=True)
    for rr in range(rows):
        for cc in range(cols):
            x, y = x0 + cc * cw, y0 + rr * ch
            img.crop((x, y, x + cw, y + ch)).save(os.path.join(a.out, f"r{rr}c{cc}.png"))
    print(f"wrote {rows*cols} cells to {a.out}")

p = argparse.ArgumentParser()
p.add_argument("--cache", default="recognition-cache")
s = p.add_subparsers(dest="cmd", required=True)
q = s.add_parser("add"); q.add_argument("image"); q.add_argument("--name", required=True)
q.add_argument("--category", required=True); q.add_argument("--source", required=True); q.add_argument("--crop")
q.add_argument("--status", default="confirmed", choices=["confirmed", "pending"],
    help="pending = name is a provisional visual label awaiting Nic's confirmation")
q.set_defaults(f=cmd_add)
q = s.add_parser("match"); q.add_argument("image"); q.add_argument("--category"); q.add_argument("--crop")
q.add_argument("--top", type=int, default=3); q.add_argument("--threshold", type=int, default=24); q.set_defaults(f=cmd_match)
q = s.add_parser("grid"); q.add_argument("image"); q.add_argument("--grid", required=True,
    help="x0,y0,cell_w,cell_h,cols,rows"); q.add_argument("--out", required=True); q.set_defaults(f=cmd_grid)
q = s.add_parser("confirm"); q.add_argument("file"); q.add_argument("--name", required=True); q.set_defaults(f=cmd_confirm)
a = p.parse_args(); a.f(a)
