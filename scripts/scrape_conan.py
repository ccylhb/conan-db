# -*- coding: utf-8 -*-
"""Conan Exiles scraper — 7daystodie style, fandom auto-generated infoboxes.

Boards: weapons / armor / thralls / consumables.
Item infobox fields are machine-generated (uniqueName, dmg, armor, NPCHealth...)
so parsing is reliable: flat |key = value lines inside one template block.
"""
import json, os, re, sys, time, hashlib, urllib.request, urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "src", "data")
CACHE_DIR = os.path.join(BASE_DIR, "scripts", "cache")
API = "https://conanexiles.fandom.com/api.php"
UA = "ConanDB/1.0 (site: conan-db.pages.dev; contact franceiwhdbks865@gmail.com)"
GAME = "conanexiles"

FETCH_CATS = ["Weapons", "Armor", "Thralls", "Consumables"]

BOARDS = {
    "weapons": [],
    "armor": [],
    "thralls": [],
    "consumables": [],
}

num_re = re.compile(r"-?\d+(?:\.\d+)?")


def num(v):
    if v is None:
        return None
    m = num_re.search(v)
    if not m:
        return None
    try:
        f = float(m.group(0))
        return int(f) if f == int(f) else f
    except ValueError:
        return None


def strip_comments(wt):
    return re.sub(r"<!--.*?-->", "", wt, flags=re.S)


def match_tpl(wt, name, strict=True):
    """Return the inner body of template `name` using brace depth tracking."""
    pat = re.compile(
        r"\{\{\s*" + name.replace(" ", "[ _]") + r"\s*(\||\n|\}\})",
        flags=re.I,
    )
    m = pat.search(wt)
    if not m:
        return None
    start = m.start() + 2
    depth = 1
    i = start
    while i < len(wt) - 1 and depth > 0:
        if wt[i] == "{":
            depth += 1
        elif wt[i] == "}":
            depth -= 1
        i += 1
    body = wt[start:i - 1]
    return body if depth == 0 else body  # tolerate unbalanced tail


def split_param_lines(body):
    """Split top-level |params, protecting {{...}} / [[...]] nesting."""
    parts = []
    buf = []
    depth_t = 0  # {{ }}
    depth_l = 0  # [[ ]]
    i = 0
    while i < len(body):
        c = body[i]
        if c == "|" and depth_t == 0 and depth_l == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
            if body.startswith("{{", i):
                depth_t += 1
                i += 1
            elif body.startswith("}}", i):
                depth_t -= 1
                i += 1
            elif body.startswith("[[", i):
                depth_l += 1
                i += 1
            elif body.startswith("]]", i):
                depth_l -= 1
                i += 1
        i += 1
    parts.append("".join(buf))
    return parts


def parse_params(body):
    out = {}
    for part in split_param_lines(body):
        part = part.strip()
        if not part or part.startswith("|"):
            part = part[1:].strip()
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if not k or k in out:
            continue
        out[k] = v.strip()
    return out


def clean(v):
    """Wikitext value -> plain text."""
    if not v:
        return ""
    v = strip_comments(v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)  # drop simple templates
    v = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", v)
    v = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2", v)
    v = re.sub(r"\[(https?://\S+)\]", "", v)
    v = v.replace("'''", "").replace("''", "")
    # 兜底：清掉被截断的模板尾巴与孤立括号（残留形如 '… Hunger. }'）
    v = re.sub(r"\{\{[^{}]*$", "", v)
    v = v.replace("}", "").replace("{", "")
    return re.sub(r"\s+", " ", v).strip()


def find_section(wt, title):
    """First section matching title at any level; return body."""
    pat = re.compile(r"^\s*(={2,6})\s*" + re.escape(title) + r"\s*\1\s*$",
                     flags=re.I | re.M)
    m = pat.search(wt)
    if not m:
        return ""
    lvl = len(m.group(1))
    rest = wt[m.end():]
    nxt = re.search(r"^\s*={%d,6}.*?=.*$\Z" % lvl, rest, flags=re.M | re.S)
    return rest[:nxt.start()] if nxt else rest


def first_para(text):
    for ln in text.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith(("=", "{", "|", "[[")) and not ln.startswith("<"):
            return clean(ln)[:400]
    return ""


def api(p):
    url = API + "?" + urllib.parse.urlencode({**p, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=40))


def cat_members(cat):
    titles, cont = [], {}
    while True:
        r = api({"action": "query", "list": "categorymembers",
                 "cmtitle": cat, "cmtype": "page", "cmnamespace": "0",
                 "cmlimit": "500", **cont})
        titles += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
        cont = r.get("continue") or {}
        if not cont:
            return titles
        time.sleep(0.4)


# --- wiki 魔术字展开 ---------------------------------------------------------
# 清洗器用 re.sub(r"\{\{[^{}]*\}\}", "", v) 整段删无名模板，{{PAGENAME}}（条目名）
# 随之消失，正文出现 "The is a ..." 残句。必须在清洗前展开成真实文本。
_MAGIC_TITLE = re.compile(r"\{\{\s*(?:SUB|BASE|FULL)?PAGENAME(?:E)?\s*\}\}", re.I)
_MAGIC_GAME = re.compile(r"\{\{\s*(?:Gamename|Game|SITENAME|Sitename)\s*\}\}", re.I)
_MAGIC_DROP = re.compile(
    r"\{\{\s*(?:DISPLAYTITLE|DEFAULTSORT|#(?:expr|var|if|ifeq|ifexist|switch|tag|invoke|time|pos|len|replace|sub|explode|titleparts)[^}]*)\}\}",
    re.I,
)


def expand_magic(wt, title):
    """把 {{PAGENAME}} 换成条目名，丢弃解析器函数等元魔术字。"""
    if not wt:
        return wt
    wt = _MAGIC_TITLE.sub(lambda _m: title, wt)
    wt = _MAGIC_GAME.sub("Conan Exiles", wt)
    wt = _MAGIC_DROP.sub("", wt)
    return wt


def fetch_wikitexts(titles, cache_path):
    if os.path.exists(cache_path):
        return json.load(open(cache_path, encoding="utf-8"))
    wts = {}
    batch = 20
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        try:
            r = api({"action": "query", "prop": "revisions",
                     "rvprop": "content", "rvslots": "main",
                     "titles": "|".join(chunk)})
        except Exception as e:
            print(f"  [batch {i}] ERR {str(e)[:60]}, retry once")
            time.sleep(3)
            r = api({"action": "query", "prop": "revisions",
                     "rvprop": "content", "rvslots": "main",
                     "titles": "|".join(chunk)})
        for pg in r["query"]["pages"].values():
            rev = pg.get("revisions") or []
            wts[pg["title"]] = rev[0]["slots"]["main"]["*"] if rev else ""
        if (i // batch) % 10 == 0:
            print(f"  fetched {i + len(chunk)}/{len(titles)}")
        time.sleep(0.35)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(wts, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return wts


def slug(t):
    s = re.sub(r"\s+", "-", t.strip().lower())
    return re.sub(r"[^a-z0-9\-]", "", s) or "item"


def scrape_items(titles, wts):
    boards = {b: [] for b in BOARDS}
    for t in titles:
        wt = wts.get(t, "")
        if not wt:
            continue
        blk = match_tpl(wt, "Item infobox", strict=True)
        if not blk:
            continue
        p = parse_params(blk)
        itype = clean(p.get("type", "")).lower()
        board = None
        if itype == "weapon":
            board = "weapons"
        elif itype == "armor":
            board = "armor"
        elif itype == "consumable":
            board = "consumables"
        if not board:
            continue
        rec = {
            "title": t,
            "slug": slug(t),
            "infobox": "Item",
            "name": clean(p.get("name", "")) or t,
            "image": clean(p.get("image", "")),
            "desc": clean(p.get("desc", "")),
            "item_type": clean(p.get("type", "")),
            "grade": clean(p.get("grade", "")),
            "id": clean(p.get("id", "")),
            "dura": num(p.get("dura")),
            "weight": num(p.get("weight")),
            "is_craftable": clean(p.get("iscraftable", "")),
            "can_be_dismantled": clean(p.get("canbedismantled", "")),
            "dlc": clean(p.get("dlcpackage", "")),
            "effect": clean(p.get("effect", "")),
        }
        if board == "weapons":
            rec.update({
                "weapon_type": clean(p.get("weapontype", "")),
                "weapon_class": clean(p.get("weaponclass", "")),
                "archetype": clean(p.get("weaponarchetype", "")),
                "dmg": num(p.get("dmg")),
                "dmg_light": num(p.get("dmglight")),
                "dmg_heavy": num(p.get("dmgheavy")),
                "armor_pen": num(p.get("armor pen")),
                "stamina_basic": num(p.get("staminabasic")),
                "stamina_special": num(p.get("staminaspecial")),
                "poise": num(p.get("poise")),
                "item_tier": num(p.get("itemtier")),
                "base_damage_type": clean(p.get("basedamagetype", "")),
            })
        elif board == "armor":
            rec.update({
                "armor": num(p.get("armor")),
                "armor_type": clean(p.get("armortype", "")),
                "armor_set": clean(p.get("armorset", "")),
                "heat_res": num(p.get("heatres")),
                "cold_res": num(p.get("coldres")),
                "bonus": clean(p.get("bonus", "")),
                "min_level": num(p.get("minlevelrequirement")),
                "equip_slot": num(p.get("equipslot")),
                "dyeable": clean(p.get("dyeable", "")),
            })
        elif board == "consumables":
            rec.update({
                "stack": num(p.get("stack")),
                "heal": num(p.get("heal")),
                "food": num(p.get("food")),
                "drink": num(p.get("drink")),
                "ingredient": clean(p.get("ingredient", "")),
            })
        dsec = find_section(wt, "Description")
        rec["intro"] = first_para(dsec) if dsec else ""
        boards[board].append(rec)
    return boards


def scrape_thralls(titles, wts):
    out = []
    for t in titles:
        wt = wts.get(t, "")
        if not wt:
            continue
        blk = match_tpl(wt, "Thrall infobox", strict=True)
        if not blk:
            continue
        p = parse_params(blk)
        health = num(p.get("npchealth"))
        if health is None:
            continue  # hub/overview pages without stats
        out.append({
            "title": t,
            "slug": slug(t),
            "infobox": "Thrall",
            "name": clean(p.get("name", "")) or t,
            "image": clean(p.get("image", "")),
            "id": clean(p.get("id", "")),
            "class": clean(p.get("class", "")),
            "type": clean(p.get("type", "")),
            "hp": health,
            "armor": num(p.get("npcarmor")),
            "kill_xp": num(p.get("npckillxp")),
            "temperament": clean(p.get("npctemperament", "")),
            "thrallable": clean(p.get("thrallable", "")),
            "faction": clean(p.get("fac", "")),
            "loc": clean(p.get("loc", "")),
        })
    return out


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    titles = set()
    for cat in FETCH_CATS:
        ts = cat_members("Category:" + cat)
        titles.update(ts)
        print(f"[cat] {cat}: {len(ts)} titles")
    titles = sorted(titles)
    print(f"[total] {len(titles)} unique pages")
    cache = os.path.join(CACHE_DIR, "wikitexts.json")
    wts = fetch_wikitexts(titles, cache)
    # 展开 wiki 魔术字（缓存保持原始，每次解析重展开，便于回滚）
    wts = {t: expand_magic(wt, t) for t, wt in wts.items()}
    boards = scrape_items(titles, wts)
    thralls = scrape_thralls(titles, wts)
    for b, rows in boards.items():
        out = os.path.join(DATA_DIR, f"conan_{b}.json")
        json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[out] {b}: {len(rows)}")
    out = os.path.join(DATA_DIR, "conan_thralls.json")
    json.dump(thralls, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[out] thralls: {len(thralls)}")
    total = sum(len(v) for v in boards.values()) + len(thralls)
    print(f"[done] {total} entries")


if __name__ == "__main__":
    main()
