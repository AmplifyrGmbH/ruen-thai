#!/usr/bin/env python3
"""
Ruen Thai — Seitengenerator.

Erzeugt aus data/restaurants.json die fertigen, statischen HTML-Seiten im
Projekt-Root (index.html, enge.html, thalwil.html, badenerstrasse.html, ueber-uns.html, kontakt.html, impressum.html,
datenschutz.html, 404.html) sowie sitemap.xml, robots.txt, llms.txt und Icons.
Das Ergebnis ist reines HTML (kein JS nötig zum Lesen der Inhalte) und wird
direkt auf Hostpoint ausgeliefert. Änderungen an Inhalten: JSON anpassen,
`python3 tools/build.py` ausführen, Ergebnis committen.
"""
import json
import html
import os
import re
from datetime import date
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "restaurants.json").read_text(encoding="utf-8"))
SITE = DATA["site"]
LOCS = DATA["locations"]
BASE = SITE["url"].rstrip("/")
TODAY = date.today().isoformat()
# STAGING = True: Seite ist passwortgeschützt und komplett noindex (Meta, Header, robots.txt, keine Sitemap/llms.txt).
# Zum Livegang auf False setzen, neu bauen und .htaccess.live als .htaccess verwenden.
STAGING = True

DAY_SHORT = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]
DAY_SCHEMA = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
ORDER = [1, 2, 3, 4, 5, 6, 0]


def e(s):
    return html.escape(str(s), quote=True)


def img(name, alt, cls="", lazy=True, sizes=None, priority=False):
    path = ROOT / "assets" / "img" / f"{name}.webp"
    w, h = Image.open(path).size
    attrs = f'src="/assets/img/{name}.webp" width="{w}" height="{h}" alt="{e(alt)}"'
    if cls:
        attrs += f' class="{cls}"'
    if priority:
        attrs += ' fetchpriority="high"'
    elif lazy:
        attrs += ' loading="lazy" decoding="async"'
    return f"<img {attrs}>"


def addr_line(l):
    return f'{l["street"]}, {l["zip"]} {l["city"]}'


def route_url(l):
    from urllib.parse import quote
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote(addr_line(l))


def map_embed(l):
    from urllib.parse import quote
    return "https://www.google.com/maps?q=" + quote(l["name"] + ", " + addr_line(l)) + "&output=embed"


def ranges_text(r):
    return " · ".join(f"{a}–{b}" for a, b in r) if r else "geschlossen"


def group_hours(l):
    rows = []
    for d in ORDER:
        t = ranges_text(l["hours"][str(d)])
        if rows and rows[-1]["text"] == t:
            rows[-1]["days"].append(d)
        else:
            rows.append({"days": [d], "text": t})
    for r in rows:
        r["label"] = DAY_SHORT[r["days"][0]] if len(r["days"]) == 1 else f'{DAY_SHORT[r["days"][0]]}–{DAY_SHORT[r["days"][-1]]}'
    return rows


def hours_table(l):
    rows = "".join(
        f'<tr data-days="{",".join(str(d) for d in r["days"])}"><th scope="row">{r["label"]}</th><td>{e(r["text"])}</td></tr>'
        for r in group_hours(l)
    )
    return f'<table class="hours"><caption class="sr-only" style="position:absolute;left:-9999px">Öffnungszeiten {e(l["name"])}</caption>{rows}</table>'


def status_html(l):
    hours = json.dumps(l["hours"], separators=(",", ":"))
    return f'<span class="status" data-hours=\'{hours}\'><i></i>Öffnungszeiten siehe unten</span>'


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"


def faq_schema(items):
    return {
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in items],
    }


def faq_html(items):
    return '<div class="faq">' + "".join(
        f'<details><summary>{e(q["q"])}</summary><div><p>{e(q["a"])}</p></div></details>' for q in items
    ) + "</div>"


# ---------------------------------------------------------------- Layout
def head(title, desc, path, extra_head="", noindex=False):
    url = BASE + (path if path != "/" else "/")
    robots = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">\n' if (noindex or STAGING) else ""
    return f"""<!DOCTYPE html>
<html lang="de-CH">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}<link rel="canonical" href="{url}">
<meta name="theme-color" content="#13294F">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/assets/img/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE["name"]}">
<meta property="og:locale" content="de_CH">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{BASE}/assets/img/og-image.jpg">
<link rel="preload" href="/assets/fonts/fraunces.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/css/style.css?v={TODAY}">
<script>document.documentElement.classList.add('js')</script>
{extra_head}</head>
"""


def header(active, cta):
    def a(href, label, key):
        cur = ' aria-current="page"' if active == key else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    nav = "".join([
        a("/enge", "Enge", "enge"),
        a("/thalwil", "Thalwil", "thalwil"),
        a("/badenerstrasse", "Badenerstrasse", "badenerstrasse"),
        a("/catering", "Catering", "catering"),
        a("/ueber-uns", "Über uns", "about"),
        a("/kontakt", "Kontakt", "kontakt"),
    ])
    return f"""<a class="skip-link" href="#main">Zum Inhalt springen</a>
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand" href="/" aria-label="Ruen Thai – Startseite">
      <img src="/assets/img/logo-icon.png" width="39" height="52" alt="">
      <span class="brand__word">Ruen Thai<small>Thai Restaurant</small></span>
    </a>
    <nav class="nav" id="site-nav" aria-label="Hauptnavigation">{nav}</nav>
    <div class="header-actions">
      <a class="btn btn--primary btn--sm" href="{cta[0]}">{cta[1]}</a>
      <button type="button" class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Menü öffnen"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>
"""


def footer():
    blocks = "".join(
        f'<address><strong>{e(l["name"])}</strong><br>{e(l["street"])}<br>{e(l["zip"])} {e(l["city"])}<br>'
        f'<a href="tel:{l["tel"]}">{e(l["telDisplay"])}</a></address>'
        for l in LOCS
    )
    return f"""<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <img src="/assets/img/logo-full-white.png" width="63" height="130" alt="Ruen Thai Restaurant" loading="lazy">
        <p>Authentische Thai-Küche seit {SITE["since"]}: Restaurants in Zürich Enge und Thalwil sowie Take Away an der Badenerstrasse.</p>
      </div>
      <div class="footer-col"><h2>Standorte</h2>{blocks}</div>
      <div class="footer-col"><h2>Entdecken</h2><ul>
        <li><a href="/enge">Ruen Thai by Suthita, Enge</a></li>
        <li><a href="/thalwil">Ruen Thai, Thalwil</a></li>
        <li><a href="/badenerstrasse">Take Away Badenerstrasse</a></li>
        <li><a href="/catering">Catering &amp; Partyservice</a></li>
        <li><a href="/ueber-uns">Über uns</a></li>
        <li><a href="/kontakt">Kontakt</a></li>
        <li><a href="/#faq">Häufige Fragen</a></li>
      </ul></div>
      <div class="footer-col"><h2>Rechtliches</h2><ul>
        <li><a href="/impressum">Impressum</a></li>
        <li><a href="/datenschutz">Datenschutz</a></li>
      </ul></div>
    </div>
    <div class="footer-base"><span>© {date.today().year} Ruen Thai. Alle Rechte vorbehalten.</span><span>Zürich · Thalwil</span></div>
  </div>
</footer>
<script src="/assets/js/main.js?v={TODAY}" defer></script>
</body>
</html>
"""


def callbar(l):
    primary = (
        f'<a class="btn btn--accent" href="tel:{l["tel"]}">Anrufen</a>'
        f'<a class="btn btn--ghost" href="{route_url(l)}" target="_blank" rel="noopener">Route</a>'
    )
    if l["reserve"]:
        primary += '<a class="btn btn--primary" href="#reservation">Reservieren</a>'
    return f'<div class="callbar">{primary}</div>'


# ---------------------------------------------------------------- Schema
def org_schema():
    return {
        "@type": "Organization",
        "@id": BASE + "/#organization",
        "name": SITE["name"],
        "url": BASE + "/",
        "logo": BASE + "/assets/img/logo-full.png",
        "foundingDate": str(SITE["since"]),
        "areaServed": [{"@type": "City", "name": "Zürich"}, {"@type": "City", "name": "Thalwil"}],
        "subOrganization": [{"@id": f'{BASE}/{l["file"]}#restaurant'} for l in LOCS],
    }


def restaurant_schema(l):
    specs = []
    for d in ORDER:
        for a, b in l["hours"][str(d)]:
            specs.append({"@type": "OpeningHoursSpecification", "dayOfWeek": DAY_SCHEMA[d], "opens": a, "closes": b})
    return {
        "@type": "Restaurant",
        "@id": f'{BASE}/{l["file"]}#restaurant',
        "name": l["name"],
        "url": f'{BASE}/{l["file"]}',
        "image": f'{BASE}/assets/img/{l["img"]}.webp',
        "telephone": l["tel"],
        "servesCuisine": "Thai",
        "priceRange": l["price"],
        "address": {"@type": "PostalAddress", "streetAddress": l["street"], "postalCode": l["zip"], "addressLocality": l["city"], "addressCountry": "CH"},
        "areaServed": l["area"],
        "openingHoursSpecification": specs,
        "parentOrganization": {"@id": BASE + "/#organization"},
        "acceptsReservations": bool(l["reserve"]),
    }


def breadcrumb_schema(l):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": l["name"], "item": f'{BASE}/{l["file"]}'},
        ],
    }


# ---------------------------------------------------------------- Seiten
def page_home():
    L = {l["key"]: l for l in LOCS}
    cards = "".join(
        f"""<article class="loc theme-{l["theme"]} on-theme">
  <div class="loc__top"><span class="loc__num">{l["number"]}</span><span class="loc__badge">{e(l["typeLabel"])}</span></div>
  <div class="loc__photo">{img(l["img"], l["name"] + " – Gericht")}</div>
  <h3 class="loc__title">{e(l["name"])}</h3>
  <p class="loc__addr">{e(l["street"])}, {e(l["zip"])} {e(l["city"])}</p>
  <div class="loc__meta">
    {status_html(l)}
    <span class="loc__rating"><b>★ {l["rating"]}</b> auf Google ({l["ratingCount"]}) · {e(l["price"])}</span>
    <a class="loc__cta loc__link" href="/{l["file"]}">Zum Standort <span class="arrow" aria-hidden="true">→</span></a>
  </div>
</article>"""
        for l in LOCS
    )
    marquee_words = ["Pad Thai", "Gaeng Keow Wan", "Tom Yum", "Satay Gai", "Massaman Gai", "Pad Kra Pao", "Goong Pong Garee", "Poh Pia Taud"]
    group = ""
    for i, w in enumerate(marquee_words):
        group += f"<span>{e(w)}</span><i></i>"
        if i == 2:
            group += '<span class="thai" lang="th">อร่อย</span><i></i>'
        if i == 5:
            group += '<span class="thai" lang="th">เผ็ด</span><i></i>'
    dishes = "".join(
        f'<figure class="reveal">{img(d["img"], d["title"] + ": " + d["text"])}<figcaption><b>{e(d["title"])}</b><span>{e(d["text"])}</span></figcaption></figure>'
        for d in DATA["dishes"]
    )
    reviews = "".join(
        f'<figure class="review reveal"><blockquote>{e(r["t"])}</blockquote><figcaption>{e(r["a"])} · {e(l["short"])}</figcaption></figure>'
        for l in LOCS for r in l["reviews"][:1]
    )
    schema = {"@context": "https://schema.org", "@graph": [
        org_schema(),
        {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": SITE["name"], "inLanguage": "de-CH", "publisher": {"@id": BASE + "/#organization"}},
        faq_schema(DATA["faq"]),
    ]}
    title = "Ruen Thai – Thai Restaurant Zürich Enge, Thalwil & Take Away"
    desc = "Authentische Thai-Küche seit 2004: Restaurants in Zürich Enge und Thalwil, Take Away an der Badenerstrasse. Wählen Sie Ihr Ruen Thai und reservieren Sie."
    out = head(title, desc, "/", jsonld(schema))
    out += '<body>\n' + header("home", ("/#standorte", "Standort wählen"))
    out += f"""<main id="main">

<section class="hero hero--cards">
  <div class="container">
    <div class="hero__top">
      <div>
        <p class="hero__kicker"><span>Zürich · Thalwil · seit {SITE["since"]}</span><span class="thai" lang="th" aria-hidden="true">สวัสดี</span></p>
        <h1 class="display"><span style="white-space:nowrap">Thai-Küche</span> mit&nbsp;<em>Herz</em>.</h1>
      </div>
      <div class="hero__side">
        <p class="hero__lead">Ruen Thai ist die Familie hinter drei Thai-Adressen in Zürich und Thalwil: zwei Restaurants zum Verweilen, ein Take Away für den schnellen Genuss.</p>
        <div class="hero__actions"><a class="btn btn--ghost" href="tel:{SITE["mainPhone"]}">Enge · {SITE["mainPhoneDisplay"]}</a><a class="btn btn--ghost" href="/kontakt">Alle Kontakte</a></div>
      </div>
    </div>
    <p class="hero__pick" id="standorte"><span>Wählen Sie Ihr Ruen Thai</span><i aria-hidden="true"></i></p>
    <div class="locs hero__cards">{cards}</div>
  </div>
</section>

<div class="marquee" aria-hidden="true"><div class="marquee__track"><div class="marquee__group">{group}</div><div class="marquee__group">{group}</div></div></div>

<section class="section section--dark story waves" id="ueber-uns">
  <div class="container story__grid">
    <div class="story__text reveal">
      <p class="eyebrow">Über uns</p>
      <div class="story__year" aria-hidden="true">{SITE["since"]}</div>
      <h2 class="h2" style="margin-bottom:22px">Ein Traum, der nach <em style="color:var(--gold)">Zuhause</em> schmeckt.</h2>
      <p class="lead">Das erste Ruen Thai öffnete {SITE["since"]} in Thalwil, mit dem Traum vom eigenen Restaurant und authentischer Thai-Küche in der Schweiz. Heute gibt es drei Standorte in Zürich und Thalwil.</p>
      <p style="margin-top:28px"><a class="btn btn--accent" href="/ueber-uns">Unsere Geschichte <span class="arrow" aria-hidden="true">→</span></a></p>
    </div>
    <div class="story__photo reveal">{img("about-interior", "Gastraum mit gedeckten Tischen, Kristalllüster und goldenem Wandbild")}</div>
  </div>
</section>

<section class="section" id="gerichte">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Aus unserer Küche</p><h2 class="h2">Frisch gekocht, <em>intensiv</em> gewürzt.</h2></div>
      <p class="lead">Curries, Nudeln, Suppen und Wok-Gerichte: Pad Thai, Massaman Gai, Tom Yum oder grünes Curry. Die Speisekarte jedes Standorts finden Sie auf dessen Seite.</p>
    </div>
    <div class="bento">{dishes}</div>
    <p class="photo-note">Symbolfotos. Die Bilder der Gerichte liefert der Betreiber.</p>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Gästestimmen</p><h2 class="h2">Was unsere Gäste <em>sagen</em>.</h2></div>
      <p class="lead">Echte Stimmen aus Google- und TripAdvisor-Bewertungen, von Zürich bis Thalwil.</p>
    </div>
    <div class="reviews">{reviews}</div>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2 class="h2">Hunger auf <em style="color:var(--gold)">Thai</em>?</h2>
    <p>Rufen Sie an, reservieren Sie einen Tisch oder holen Sie Ihr Essen ab. Adressen, Öffnungszeiten und Telefonnummern aller Standorte finden Sie auf der Kontaktseite.</p>
    <div class="cta-band__links"><a class="btn btn--accent" href="/kontakt">Kontakt &amp; Öffnungszeiten <span class="arrow" aria-hidden="true">→</span></a><a class="btn btn--ghost" href="tel:{SITE["mainPhone"]}">{SITE["mainPhoneDisplay"]}</a></div>
  </div>
</section>

<section class="section section--cream" id="faq">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Häufige Fragen</p><h2 class="h2">Antworten, <em>bevor</em> Sie fragen.</h2></div>
      <p class="lead">Das Wichtigste zu Standorten, Öffnungszeiten, Reservation und Preisen auf einen Blick.</p>
    </div>
    {faq_html(DATA["faq"])}
  </div>
</section>

</main>
"""
    out += footer()
    return out


H1_HTML = {
    "enge": 'Ruen Thai <em>by Suthita</em>',
    "thalwil": 'Ruen Thai <em>Thalwil</em>',
    "badenerstrasse": 'Ruenthai 2 <em>Take Away</em>',
}


def page_location(l):
    others = [o for o in LOCS if o["key"] != l["key"]]
    if l["reserve"]:
        primary = '<a class="btn btn--primary" href="#reservation">Tisch reservieren <span class="arrow" aria-hidden="true">→</span></a>'
        cta = ("#reservation", "Tisch reservieren")
    else:
        primary = f'<a class="btn btn--primary" href="tel:{l["tel"]}">Jetzt anrufen &amp; bestellen</a>'
        cta = (f'tel:{l["tel"]}', "Jetzt anrufen")
    ghost = (f'<a class="btn btn--ghost" href="tel:{l["tel"]}">{e(l["telDisplay"])}</a>' if l["reserve"]
             else f'<a class="btn btn--ghost" href="{route_url(l)}" target="_blank" rel="noopener">Route planen</a>')

    menu = "".join(
        f'<div class="menu__item reveal"><h3>{e(m["n"])}</h3><p>{e(m["d"])}</p>' + (f'<span class="menu__price">{e(m["p"])}</span>' if m["p"] else "") + "</div>"
        for m in l["menu"]
    )
    gallery = "".join(
        f'<figure class="reveal">{img(g["img"], g["alt"])}<figcaption><b>{e(g["t"])}</b>' + ('<span>Foto: Ruen Thai</span>' if g.get("real") else "") + '</figcaption></figure>'
        for g in l["gallery"][:5]
    )
    reviews = "".join(f'<figure class="review reveal"><blockquote>{e(r["t"])}</blockquote><figcaption>{e(r["a"])}</figcaption></figure>' for r in l["reviews"])
    facts = "".join(f"<li>{e(f)}</li>" for f in l["facts"])
    catering_link = ('<p style="margin-top:22px"><a class="btn btn--ghost btn--sm" href="/catering">Catering für Ihren Anlass <span class="arrow" aria-hidden="true">→</span></a></p>'
                     if l.get("catering") else "")
    others_html = "".join(
        f'<a class="other theme-{o["theme"]}" href="/{o["file"]}"><b>{e(o["name"])}</b><span>{e(o["typeLabel"])} · {e(o["city"])}</span></a>' for o in others
    )

    if l["reserve"]:
        action = f"""<section class="section" id="reservation">
  <div class="container">
    <div class="reserve theme-{l["theme"]} waves reveal">
      <div class="reserve__text">
        <p class="eyebrow">Tischreservation</p>
        <h2 class="h2">Ihr Tisch bei <em>{e(l["short"])}</em>.</h2>
        <p>Senden Sie uns Ihre Anfrage, wir bestätigen sie telefonisch oder per E-Mail. Mit Ihrer E-Mail-Adresse erhalten Sie sofort eine Eingangsbestätigung. Für kurzfristige Reservationen rufen Sie am besten direkt an: <a href="tel:{l["tel"]}">{e(l["telDisplay"])}</a>.</p>
      </div>
      <form class="form" data-reserve-form data-success="Danke! Ihre Anfrage ist bei uns. Wir bestätigen Ihren Tisch so rasch wie möglich." action="/anfrage.php" method="post">
        <input type="hidden" name="typ" value="reservation">
        <input type="hidden" name="ort" value="{e(l["name"])}">
        <div class="field hp" aria-hidden="true"><label>Webseite<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
        <div class="form__row">
          <div class="field"><label for="f-name">Name *</label><input id="f-name" name="name" type="text" required autocomplete="name"></div>
          <div class="field"><label for="f-tel">Telefon *</label><input id="f-tel" name="telefon" type="tel" required autocomplete="tel"></div>
        </div>
        <div class="form__row">
          <div class="field"><label for="f-date">Datum *</label><input id="f-date" name="datum" type="date" required></div>
          <div class="field"><label for="f-time">Uhrzeit *</label><input id="f-time" name="zeit" type="time" required step="900"></div>
        </div>
        <div class="form__row">
          <div class="field"><label for="f-pers">Personen *</label>
            <select id="f-pers" name="personen" required><option>1</option><option selected>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10 oder mehr</option></select></div>
          <div class="field"><label for="f-mail">E-Mail (optional)</label><input id="f-mail" name="email" type="email" autocomplete="email"></div>
        </div>
        <div class="field"><label for="f-msg">Bemerkung (optional)</label><textarea id="f-msg" name="bemerkung" rows="3" placeholder="z. B. Allergien, Kinderstuhl, Geburtstag"></textarea></div>
        <button class="btn" type="submit">Anfrage senden <span class="arrow" aria-hidden="true">→</span></button>
        <p class="form__status" role="status" aria-live="polite"></p>
        <p class="form__small">Mit dem Absenden stimmen Sie der Bearbeitung Ihrer Angaben gemäss <a href="/datenschutz" style="text-decoration:underline">Datenschutzerklärung</a> zu.</p>
      </form>
    </div>
  </div>
</section>"""
    else:
        action = f"""<section class="section" id="bestellen">
  <div class="container">
    <div class="order theme-{l["theme"]} waves reveal">
      <div>
        <p class="eyebrow">Bestellen &amp; abholen</p>
        <a class="order__phone" href="tel:{l["tel"]}">{e(l["telDisplay"])}</a>
        <p>Rufen Sie kurz vorher an, wir halten Ihr Essen bereit. Von Montag bis Freitag, 10:30 bis 17:00 Uhr.</p>
      </div>
      <ol class="order__steps">
        <li>Anrufen und Gericht oder Tagesmenü wählen</li>
        <li>Wir kochen frisch und halten alles bereit</li>
        <li>Abholen an der Badenerstrasse 582 und geniessen</li>
      </ol>
    </div>
  </div>
</section>"""

    schema = {"@context": "https://schema.org", "@graph": [
        org_schema(), restaurant_schema(l), breadcrumb_schema(l), faq_schema(l["faq"]),
    ]}
    out = head(l["title"], l["metaDescription"], "/" + l["file"], jsonld(schema))
    out += '<body class="has-callbar">\n' + header(l["key"], cta)
    out += f"""<main id="main">

<section class="l-hero theme-{l["theme"]} on-theme waves">
  <div class="container l-hero__grid">
    <div class="l-hero__copy">
      <nav class="crumbs" aria-label="Brotkrumen"><a href="/">Startseite</a><span aria-hidden="true">/</span><span aria-current="page">{e(l["short"])}</span></nav>
      <p class="eyebrow">{e(l["typeLabel"])} · {e(l["area"])}</p>
      <h1 class="display">{H1_HTML[l["key"]]}</h1>
      <p class="l-hero__lead">{e(l["lead"])}</p>
      <div class="l-hero__actions">{primary}{ghost}</div>
      {status_html(l)}
    </div>
    <div class="l-hero__photo">{img(l["heroImg"], l["name"] + ": Gericht", priority=True, lazy=False)}</div>
  </div>
</section>

<section class="infobar" aria-label="Auf einen Blick">
  <div class="container infobar__grid">
    <div class="infobar__item"><small>Adresse</small><b>{e(l["street"])}<br>{e(l["zip"])} {e(l["city"])}</b></div>
    <div class="infobar__item"><small>Telefon</small><b><a href="tel:{l["tel"]}">{e(l["telDisplay"])}</a></b></div>
    <div class="infobar__item"><small>Preisniveau</small><b>{e(l["price"])}</b></div>
    <div class="infobar__item"><small>Google</small><b>★ {l["rating"]} ({l["ratingCount"]})</b></div>
  </div>
</section>

<section class="section">
  <div class="container l-intro">
    <div class="reveal">
      <p class="eyebrow">Willkommen</p>
      <h2 class="h2">Das erwartet <em>Sie</em>.</h2>
      <p class="lead">{e(l["story"])}</p>
      <ul class="facts">{facts}</ul>
      {catering_link}
    </div>
    <aside class="hours-card reveal">
      <h2 class="serif">Öffnungszeiten</h2>
      {hours_table(l)}
      <address><strong>{e(l["name"])}</strong><br>{e(l["street"])}, {e(l["zip"])} {e(l["city"])}
        <p>{e(l["transit"])}</p>
        <a class="btn btn--primary btn--sm" href="tel:{l["tel"]}">Anrufen</a><a class="btn btn--ghost btn--sm" href="{route_url(l)}" target="_blank" rel="noopener">Route</a>
      </address>
    </aside>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Impressionen</p><h2 class="h2">{e(l["galleryTitle"])}</h2></div>
      <p class="lead">Ein Blick auf Teller und Atmosphäre bei {e(l["short"])}.</p>
    </div>
    <div class="bento bento--loc">{gallery}</div>
    <p class="photo-note">Bilder ohne Quellenangabe sind Symbolfotos; die Originalbilder liefert der Betreiber.</p>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Speisekarte</p><h2 class="h2">{e(l["menuTitle"])}</h2></div>
      <p class="lead">Authentisch gekocht, nach Rezepten mit langjähriger Tradition.</p>
    </div>
    <div class="menu">{menu}</div>
    <p class="menu-note">{e(l["menuNote"])}</p>
  </div>
</section>

{action}

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Gästestimmen</p><h2 class="h2">★ {l["rating"]} <em>auf Google</em>.</h2></div>
      <p class="lead">{l["ratingCount"]} Bewertungen, Preisniveau {e(l["price"])} pro Person.</p>
    </div>
    <div class="reviews">{reviews}</div>
  </div>
</section>

<section class="section">
  <div class="container map">
    <div class="map__frame">
      <button class="btn btn--ghost" type="button" data-map-src="{e(map_embed(l))}" data-map-title="{e(l["name"])} auf der Karte">Karte anzeigen</button>
      <p>Beim Anzeigen der Karte werden Daten an Google Maps übertragen. Alternativ <a href="{route_url(l)}" target="_blank" rel="noopener" style="text-decoration:underline">Route in Google Maps öffnen</a>.</p>
    </div>
    <div class="others"><h2>Weitere Standorte</h2>{others_html}</div>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Häufige Fragen</p><h2 class="h2">Gut <em>zu wissen</em>.</h2></div>
      <p class="lead">Antworten zu {e(l["name"])}.</p>
    </div>
    {faq_html(l["faq"])}
  </div>
</section>

</main>
"""
    out += callbar(l) + footer()
    return out


def simple_page(title, desc, path, body_html, active=""):
    out = head(title, desc, path, noindex=False)
    out += "<body>\n" + header(active, ("/#standorte", "Standort wählen"))
    out += f'<main id="main"><div class="container">{body_html}</div></main>\n' + footer()
    return out


def page_impressum():
    body = """<div class="prose">
<h1>Impressum</h1>
<p class="todo"><strong>Vom Betreiber zu ergänzen:</strong> Die rechtlich verbindlichen Angaben (Firma, Rechtsform, Inhaber, UID/Handelsregister, E-Mail) fehlen noch und dürfen nicht geraten werden. Bitte vor dem Livegang vollständig ausfüllen.</p>
<h2>Angaben zum Betreiber</h2>
<p>[Firma / Inhaber – bitte ergänzen]<br>[Rechtsform und UID-Nr. – bitte ergänzen]</p>
<h2>Standorte und Kontakt</h2>
<p><strong>Ruen Thai by Suthita</strong><br>General-Wille-Strasse 18, 8002 Zürich<br>Telefon <a href="tel:+41442811414">044 281 14 14</a></p>
<p><strong>Ruen Thai Thalwil</strong><br>Ludretikonerstrasse 21, 8800 Thalwil<br>Telefon <a href="tel:+41434435989">043 443 59 89</a></p>
<p><strong>Ruenthai 2 Take Away</strong><br>Badenerstrasse 582, 8048 Zürich<br>Telefon <a href="tel:+41438174780">043 817 47 80</a></p>
<p>E-Mail: [bitte ergänzen]</p>
<h2>Haftungsausschluss</h2>
<p>Die Inhalte dieser Website wurden mit grösster Sorgfalt erstellt. Für Richtigkeit, Vollständigkeit und Aktualität wird keine Gewähr übernommen. Öffnungszeiten und Preise können sich ändern.</p>
<h2>Urheberrecht</h2>
<p>Texte, Bilder und Gestaltung unterliegen dem Urheberrecht. Symbolfotos stammen von Pexels (kostenlose Nutzung).</p>
</div>"""
    return simple_page("Impressum – Ruen Thai", "Impressum und Kontaktangaben von Ruen Thai in Zürich Enge, Thalwil und an der Badenerstrasse.", "/impressum", body)


def page_datenschutz():
    body = """<div class="prose">
<h1>Datenschutzerklärung</h1>
<p class="todo"><strong>Entwurf:</strong> Diese Erklärung ist eine Vorlage und muss vor dem Livegang vom Betreiber geprüft und mit den Angaben zur verantwortlichen Stelle ergänzt werden (Hinweis: keine Rechtsberatung).</p>
<h2>Verantwortliche Stelle</h2>
<p>[Firma / Inhaber, Adresse, E-Mail – bitte ergänzen]</p>
<h2>Hosting und Server-Logfiles</h2>
<p>Diese Website wird bei Hostpoint AG (Schweiz) gehostet. Beim Aufruf werden technisch notwendige Daten (IP-Adresse, Datum und Uhrzeit, aufgerufene Seite, Browser) in Server-Logfiles gespeichert. Sie dienen dem sicheren Betrieb der Website.</p>
<h2>Reservationsanfragen</h2>
<p>Wenn Sie das Reservationsformular verwenden, werden Ihre Angaben (Name, Telefon, Datum, Uhrzeit, Personenzahl, optional E-Mail und Bemerkung) per E-Mail an das gewählte Restaurant gesendet und ausschliesslich zur Bearbeitung Ihrer Anfrage verwendet. Geben Sie Ihre E-Mail-Adresse an, erhalten Sie eine automatische Eingangsbestätigung.</p>
<h2>Catering-Anfragen</h2>
<p>Wenn Sie das Catering-Formular verwenden, werden Ihre Angaben (Name, optional Firma, Telefon, E-Mail, Datum, Gästezahl, Anlass, Ort und Wünsche) per E-Mail an Ruen Thai gesendet und ausschliesslich zur Bearbeitung Ihrer Anfrage und für die Offerte verwendet. Sie erhalten eine automatische Eingangsbestätigung.</p>
<h2>Google Maps</h2>
<p>Karten werden erst nach Ihrem Klick auf «Karte anzeigen» von Google Maps geladen. Dabei werden Daten (u. a. Ihre IP-Adresse) an Google übertragen. Ohne Klick findet keine Übertragung statt.</p>
<h2>Schriften, Cookies und Tracking</h2>
<p>Schriften werden lokal vom eigenen Server geladen. Diese Website setzt keine Cookies und verwendet keine Analyse- oder Tracking-Tools.</p>
<h2>Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft, Berichtigung und Löschung Ihrer Personendaten. Wenden Sie sich dazu an die oben genannte verantwortliche Stelle.</p>
</div>"""
    return simple_page("Datenschutz – Ruen Thai", "Datenschutzerklärung der Website von Ruen Thai: Hosting, Reservationsformular, Google Maps nach Klick, keine Cookies.", "/datenschutz", body)


def page_404():
    out = head("Seite nicht gefunden – Ruen Thai", "Diese Seite gibt es nicht. Zurück zur Startseite von Ruen Thai.", "/404", noindex=True)
    out += "<body>\n" + header("", ("/#standorte", "Standort wählen"))
    out += """<main id="main"><div class="nf">
<p class="display" aria-hidden="true">404</p>
<h1 class="h3">Diese Seite ist uns durch die Lappen gegangen.</h1>
<p class="lead" style="margin-inline:auto">Hier finden Sie sicher, was Sie suchen:</p>
<div class="cta-band__links" style="justify-content:center">
<a class="btn btn--primary" href="/">Startseite</a><a class="btn btn--ghost" href="/enge">Enge</a><a class="btn btn--ghost" href="/thalwil">Thalwil</a><a class="btn btn--ghost" href="/badenerstrasse">Badenerstrasse</a>
</div></div></main>
""" + footer()
    return out


def loc_cards_html():
    return "".join(
        f"""<article class="loc theme-{l["theme"]} on-theme reveal">
  <div class="loc__top"><span class="loc__num">{l["number"]}</span><span class="loc__badge">{e(l["typeLabel"])}</span></div>
  <div class="loc__photo">{img(l["img"], l["name"] + " – Gericht")}</div>
  <h3 class="loc__title">{e(l["name"])}</h3>
  <p class="loc__addr">{e(l["street"])}, {e(l["zip"])} {e(l["city"])}</p>
  <div class="loc__meta">
    {status_html(l)}
    <span class="loc__rating"><b>★ {l["rating"]}</b> auf Google ({l["ratingCount"]}) · {e(l["price"])}</span>
    <a class="loc__cta loc__link" href="/{l["file"]}">Zum Standort <span class="arrow" aria-hidden="true">→</span></a>
  </div>
</article>"""
        for l in LOCS
    )


def page_about():
    faq = [q for q in DATA["faq"] if q["q"] in ("Seit wann gibt es Ruen Thai?", "Welche Standorte gibt es?")]
    rows = "".join(
        f'''<a class="row-loc reveal" href="/{l["file"]}"><span class="row-loc__n">{l["number"]}</span>
  <span class="row-loc__main"><b>{e(l["name"])}</b><small>{e(l["typeLabel"])} · {e(l["street"])}, {e(l["zip"])} {e(l["city"])}</small></span>
  <span class="row-loc__go">Zum Standort <span class="arrow" aria-hidden="true">→</span></span></a>'''
        for l in LOCS
    )
    schema = {"@context": "https://schema.org", "@graph": [
        org_schema(),
        {"@type": "AboutPage", "@id": BASE + "/ueber-uns#page", "url": BASE + "/ueber-uns", "name": "Über uns – Ruen Thai", "about": {"@id": BASE + "/#organization"}, "inLanguage": "de-CH"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Über uns", "item": BASE + "/ueber-uns"}]},
        faq_schema(faq),
    ]}
    out = head("Über uns – Ruen Thai, Thai-Küche seit 2004 in Zürich & Thalwil",
               "Die Geschichte von Ruen Thai: 2004 in Thalwil eröffnet, heute zwei Restaurants und ein Take Away in Zürich und Thalwil. Authentische Thai-Küche mit Tradition.",
               "/ueber-uns", jsonld(schema))
    out += "<body>\n" + header("about", ("/#standorte", "Standort wählen"))
    out += f"""<main id="main">

<section class="pg-hero">
  <div class="container">
    <nav class="crumbs crumbs--dark" aria-label="Brotkrumen"><a href="/">Startseite</a><span aria-hidden="true">/</span><span aria-current="page">Über uns</span></nav>
    <p class="eyebrow">Über uns</p>
    <h1 class="pg-hero__title">Eine Familie, <em>ein Geschmack</em>, drei Adressen.</h1>
    <div class="pg-hero__grid">
      <div class="pg-hero__text">
        <p class="dropcap">Das erste Ruen Thai öffnete {SITE["since"]} in Thalwil. Die Inhaber verwirklichten damit den Traum vom eigenen Restaurant und legten den Grundstein für authentische Thai-Küche in der Schweiz.</p>
        <p>Die Gerichte entstehen nach eigens kreierten Rezepten mit langjähriger Tradition, in Räumen mit viel Liebe zum Detail. Später kamen das Restaurant Ruen Thai by Suthita in der Enge und das Take Away an der Badenerstrasse dazu.</p>
      </div>
      <figure class="pg-hero__photo">{img("about-interior", "Gastraum mit gedeckten Tischen, Kristalllüster und goldenem Wandbild", priority=True, lazy=False)}<figcaption>Gastraum mit gedeckten Tischen und goldenem Wandbild.</figcaption></figure>
    </div>
  </div>
</section>

<section class="facts-strip" aria-label="Ruen Thai in Zahlen">
  <div class="container facts-strip__grid">
    <div><b>{SITE["since"]}</b><span>Eröffnung in Thalwil</span></div>
    <div><b>3</b><span>Standorte</span></div>
    <div><b>650+</b><span>Google-Bewertungen</span></div>
    <div><b>Nr. 1</b><span>TripAdvisor Thalwil</span></div>
  </div>
</section>

<section class="section">
  <div class="container chapters">
    <div class="chapters__head reveal"><p class="eyebrow">Kapitel</p><h2 class="h2">Wie alles <em>begann</em>.</h2></div>
    <ol class="chapters__list">
      <li class="reveal"><b>{SITE["since"]}</b><div><h3>Ruen Thai in Thalwil</h3><p>Das erste Restaurant öffnet an der Ludretikonerstrasse. Gemütlich eingerichtet, mit eigenen Rezepten und viel Liebe zum Detail.</p></div></li>
      <li class="reveal"><b>Später</b><div><h3>Zürich kommt dazu</h3><p>Mit Ruen Thai by Suthita in der Enge und dem Take Away Ruenthai 2 an der Badenerstrasse wächst aus einem Restaurant eine kleine Familie von Adressen.</p></div></li>
      <li class="reveal"><b>Heute</b><div><h3>Gästeliebling</h3><p>Über 650 Google-Bewertungen an drei Standorten. In Thalwil führt Ruen Thai die TripAdvisor-Liste an.</p></div></li>
    </ol>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="pull reveal">
      <p class="pull__q">«Schweizer Qualität, die schmeckt wie bei einer thailändischen Familie zu Hause.»</p>
      <p class="pull__a">So beschreibt Ruen Thai den eigenen Anspruch.</p>
    </div>
    <div class="principles">
      <div class="reveal"><span>01</span><h3>Rezepte mit Tradition</h3><p>Eigens kreierte Rezepte mit langjähriger Tradition: intensive Aromen, ausgewogen zwischen süss, scharf, sauer und salzig.</p></div>
      <div class="reveal"><span>02</span><h3>Täglich frisch</h3><p>Es wird frisch gekocht, und die Mittagsmenüs wechseln täglich, auch mit vegetarischen Gerichten.</p></div>
      <div class="reveal"><span>03</span><h3>Schweizer Qualität</h3><p>Mehrere Gerichte entstehen mit Schweizer Poulet. Gäste loben immer wieder Portionen und Service.</p></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Besuchen Sie uns</p><h2 class="h2">Drei Adressen, <em>ein Geschmack</em>.</h2></div>
      <p class="lead">Jeder Standort hat eine eigene Seite mit Speisekarte, Öffnungszeiten und Reservation.</p>
    </div>
    <div class="row-locs">{rows}</div>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Häufige Fragen</p><h2 class="h2">Kurz <em>erklärt</em>.</h2></div>
      <p class="lead">Mehr Antworten finden Sie auf der Startseite und auf den Standortseiten.</p>
    </div>
    {faq_html(faq)}
  </div>
</section>

</main>
""" + footer()
    return out


def page_contact():
    cards = "".join(
        f"""<article class="loc contact theme-{l["theme"]} on-theme reveal" style="min-height:0">
  <div class="loc__top"><span class="loc__num">{l["number"]}</span><span class="loc__badge">{e(l["typeLabel"])}</span></div>
  <h2 class="loc__title">{e(l["name"])}</h2>
  <address class="loc__addr" style="font-style:normal">{e(l["street"])}<br>{e(l["zip"])} {e(l["city"])}</address>
  <p class="contact__phone"><a href="tel:{l["tel"]}">{e(l["telDisplay"])}</a></p>
  {status_html(l)}
  <div class="contact__hours">{hours_table(l)}</div>
  <p class="loc__addr" style="margin:14px 0 0">{e(l["transit"])}</p>
  <div class="contact__actions">
    <a class="btn btn--sm" style="background:var(--t-fg);color:var(--t-bg)" href="tel:{l["tel"]}">Anrufen</a>
    <a class="btn btn--sm btn--ghost" style="color:var(--t-fg)" href="{route_url(l)}" target="_blank" rel="noopener">Route</a>
    <a class="btn btn--sm btn--ghost" style="color:var(--t-fg)" href="/{l["file"]}{'#reservation' if l["reserve"] else ''}">{'Reservieren' if l["reserve"] else 'Zur Seite'}</a>
  </div>
  <div class="map__frame contact__map"><button class="btn btn--sm btn--ghost" type="button" data-map-src="{e(map_embed(l))}" data-map-title="{e(l["name"])} auf der Karte" style="color:var(--t-fg)">Karte anzeigen</button></div>
</article>"""
        for l in LOCS
    )
    schema = {"@context": "https://schema.org", "@graph": [
        org_schema(),
        {"@type": "ContactPage", "@id": BASE + "/kontakt#page", "url": BASE + "/kontakt", "name": "Kontakt – Ruen Thai", "about": {"@id": BASE + "/#organization"}, "inLanguage": "de-CH"},
        *[restaurant_schema(l) for l in LOCS],
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Kontakt", "item": BASE + "/kontakt"}]},
    ]}
    out = head("Kontakt & Öffnungszeiten – Ruen Thai Zürich Enge, Thalwil, Badenerstrasse",
               "Adressen, Telefonnummern und Öffnungszeiten aller drei Ruen-Thai-Standorte: Zürich Enge, Thalwil und Take Away Badenerstrasse. Jetzt anrufen oder Route planen.",
               "/kontakt", jsonld(schema))
    out += "<body>\n" + header("kontakt", ("/#standorte", "Standort wählen"))
    out += f"""<main id="main">

<section class="l-hero theme-navy on-theme waves" style="padding-bottom:64px">
  <div class="container">
    <nav class="crumbs" aria-label="Brotkrumen"><a href="/">Startseite</a><span aria-hidden="true">/</span><span aria-current="page">Kontakt</span></nav>
    <p class="eyebrow">Kontakt</p>
    <h1 class="display">Wir freuen uns <em>auf Sie</em>.</h1>
    <p class="l-hero__lead">Ruen Thai erreichen Sie an drei Standorten in Zürich und Thalwil. Rufen Sie direkt beim gewünschten Standort an: Enge {SITE["mainPhoneDisplay"]}, Thalwil 043 443 59 89, Take Away Badenerstrasse 043 817 47 80.</p>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="locs">{cards}</div>
    <p class="menu-note" style="margin-top:28px">Öffnungszeiten laut Drittquellen. Bitte vor dem Besuch kurz telefonisch bestätigen, besonders an Feiertagen.</p>
  </div>
</section>

<section class="cta-band">
  <div class="container">
    <h2 class="h2">Lieber <em style="color:var(--gold)">reservieren</em>?</h2>
    <p>In den Restaurants Enge und Thalwil können Sie online einen Tisch anfragen.</p>
    <div class="cta-band__links"><a class="btn btn--accent" href="/enge#reservation">Tisch in der Enge</a><a class="btn btn--accent" href="/thalwil#reservation">Tisch in Thalwil</a><a class="btn btn--ghost" style="color:var(--cream)" href="/catering#anfrage">Catering anfragen</a></div>
  </div>
</section>

</main>
""" + footer()
    return out


CATERING_FAQ = [
    {"q": "Bietet Ruen Thai Catering an?",
     "a": "Ja. Ruen Thai bietet Catering und Partyservice für Firmenanlässe, Apéros, Geburtstage und Familienfeiern. Gekocht wird in unserem Restaurant Ruen Thai by Suthita in Zürich Enge."},
    {"q": "Welche Gerichte gibt es im Catering?",
     "a": "Wir stellen das Menü aus unserer Küche nach Ihren Wünschen zusammen, zum Beispiel Frühlingsrollen, Satay-Spiessli mit Erdnuss-Sauce, Currys mit Jasminreis oder Pad Thai. Vegetarische Gerichte sind möglich. Allergien berücksichtigen wir gerne, bitte geben Sie diese in der Anfrage an."},
    {"q": "Was kostet ein Catering?",
     "a": "Der Preis hängt von Gästezahl, Menü und Service ab. Nach Ihrer Anfrage erhalten Sie einen Menüvorschlag mit Offerte."},
    {"q": "Wie früh sollte ich anfragen?",
     "a": "So früh wie möglich, besonders bei grösseren Gruppen und an Wochenenden. Für kurzfristige Anlässe rufen Sie uns am besten direkt an: 044 281 14 14."},
    {"q": "Wie läuft eine Catering-Anfrage ab?",
     "a": "Sie senden uns Datum, Gästezahl, Anlass und Ihre Wünsche über das Formular oder per Telefon. Wir melden uns mit einem Menüvorschlag und einer Offerte. Nach Ihrer Bestätigung kochen wir frisch für Ihren Anlass."},
]


def page_catering():
    enge = next(l for l in LOCS if l["key"] == "enge")
    gallery_items = [
        ("dish-red-curry", "Rotes Curry mit Jasminreis", "Rotes Thai-Curry mit Poulet und Jasminreis"),
        ("g-enge-satay", "Satay mit Erdnuss-Sauce", "Gegrillte Satay-Spiesse mit Erdnusssauce"),
        ("g-enge-fruehlingsrollen", "Frühlingsrollen", "Knusprige Frühlingsrollen mit Dip"),
        ("dish-green-curry", "Grünes Curry", "Grünes Thai-Curry mit Thai-Basilikum"),
        ("dish-padthai", "Pad Thai", "Pad Thai mit Sprossen, Erdnüssen und Limette"),
    ]
    gallery = "".join(f'<figure class="reveal">{img(i, alt)}<figcaption><b>{e(t)}</b></figcaption></figure>' for i, t, alt in gallery_items)
    schema = {"@context": "https://schema.org", "@graph": [
        org_schema(),
        {"@type": "Service", "@id": BASE + "/catering#service", "name": "Thai-Catering und Partyservice",
         "serviceType": "Catering", "url": BASE + "/catering",
         "description": "Thai-Catering und Partyservice von Ruen Thai für Firmenanlässe, Apéros, Geburtstage und Familienfeiern, gekocht im Restaurant Ruen Thai by Suthita in Zürich Enge.",
         "provider": {"@id": f'{BASE}/{enge["file"]}#restaurant'},
         "brand": {"@id": BASE + "/#organization"},
         "areaServed": {"@type": "City", "name": "Zürich"}},
        restaurant_schema(enge),
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Catering", "item": BASE + "/catering"}]},
        faq_schema(CATERING_FAQ),
    ]}
    out = head("Thai-Catering Zürich – Partyservice von Ruen Thai",
               "Thai-Catering für Firmenanlässe, Apéros und Feiern in Zürich: frisch gekocht von Ruen Thai in der Enge. Jetzt online anfragen und Menüvorschlag mit Offerte erhalten.",
               "/catering", jsonld(schema))
    out += "<body>\n" + header("catering", ("#anfrage", "Catering anfragen"))
    out += f"""<main id="main">

<section class="pg-hero">
  <div class="container">
    <nav class="crumbs crumbs--dark" aria-label="Brotkrumen"><a href="/">Startseite</a><span aria-hidden="true">/</span><span aria-current="page">Catering</span></nav>
    <p class="eyebrow">Catering &amp; Partyservice</p>
    <h1 class="pg-hero__title">Thai-Küche für <em>Ihren Anlass</em>.</h1>
    <div class="pg-hero__grid">
      <div class="pg-hero__text">
        <p class="dropcap">Ruen Thai bietet Catering und Partyservice für Firmenanlässe, Apéros, Geburtstage und Familienfeiern. Gekocht wird in unserem Restaurant Ruen Thai by Suthita in Zürich Enge, nach denselben Rezepten wie im Restaurant.</p>
        <p>Sie sagen uns Datum, Gästezahl und Wünsche. Wir stellen das Menü zusammen und senden Ihnen einen Vorschlag mit Offerte.</p>
        <p style="margin-top:28px"><a class="btn btn--primary" href="#anfrage">Catering anfragen <span class="arrow" aria-hidden="true">→</span></a> <a class="btn btn--ghost" href="tel:{enge["tel"]}">{e(enge["telDisplay"])}</a></p>
      </div>
      <figure class="pg-hero__photo">{img("dish-teller", "Thai-Gerichte zum Teilen für ein Catering", priority=True, lazy=False)}<figcaption>Gerichte zum Teilen, ideal für Apéro und Buffet.</figcaption></figure>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Anlässe</p><h2 class="h2">Für jede <em>Gelegenheit</em>.</h2></div>
      <p class="lead">Vom Apéro im Büro bis zum Familienfest: Wir richten das Menü nach Anlass und Gästezahl.</p>
    </div>
    <div class="principles">
      <div class="reveal"><span>01</span><h3>Firmenanlässe und Apéros</h3><p>Fingerfood wie Frühlingsrollen und Satay-Spiessli für Apéro, Teamevent oder Kundenanlass.</p></div>
      <div class="reveal"><span>02</span><h3>Geburtstage und Familienfeste</h3><p>Currys, Nudeln und Wok-Gerichte zum Teilen, damit alle am Tisch etwas finden.</p></div>
      <div class="reveal"><span>03</span><h3>Vegetarisch und nach Wunsch</h3><p>Vegetarische Gerichte sind möglich. Allergien und Wünsche berücksichtigen wir gerne.</p></div>
    </div>
  </div>
</section>

<section class="section section--cream">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Aus unserer Küche</p><h2 class="h2">Frisch gekocht, <em>zum Teilen</em>.</h2></div>
      <p class="lead">Eine Auswahl an Gerichten, die sich für Catering besonders eignen. Das Menü stellen wir mit Ihnen zusammen.</p>
    </div>
    <div class="bento bento--loc">{gallery}</div>
    <p class="photo-note">Symbolfotos. Die Bilder der Gerichte liefert der Betreiber.</p>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="order theme-lacquer waves reveal">
      <div>
        <p class="eyebrow">So funktioniert es</p>
        <h2 class="h2">In drei Schritten <em>zum Catering</em>.</h2>
      </div>
      <ol class="order__steps">
        <li>Anfrage senden mit Datum, Gästezahl, Anlass und Wünschen</li>
        <li>Wir melden uns mit Menüvorschlag und Offerte</li>
        <li>Nach Ihrer Bestätigung kochen wir frisch für Ihren Anlass</li>
      </ol>
    </div>
  </div>
</section>

<section class="section section--cream" id="anfrage">
  <div class="container">
    <div class="reserve theme-navy waves reveal">
      <div class="reserve__text">
        <p class="eyebrow">Catering-Anfrage</p>
        <h2 class="h2">Erzählen Sie uns von <em>Ihrem Anlass</em>.</h2>
        <p>Je genauer Ihre Angaben, desto passender unser Vorschlag. Sie erhalten sofort eine Eingangsbestätigung per E-Mail, wir melden uns danach persönlich. Lieber telefonisch? <a href="tel:{enge["tel"]}">{e(enge["telDisplay"])}</a>.</p>
      </div>
      <form class="form" data-reserve-form data-success="Danke! Ihre Catering-Anfrage ist bei uns. Wir melden uns mit einem Vorschlag." action="/anfrage.php" method="post">
        <input type="hidden" name="typ" value="catering">
        <div class="field hp" aria-hidden="true"><label>Webseite<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
        <div class="form__row">
          <div class="field"><label for="c-anlass">Anlass *</label>
            <select id="c-anlass" name="anlass" required><option value="" selected disabled>Bitte wählen</option><option>Firmenanlass</option><option>Apéro</option><option>Geburtstag</option><option>Familienfest</option><option>Hochzeit</option><option>Anderer Anlass</option></select></div>
          <div class="field"><label for="c-date">Datum *</label><input id="c-date" name="datum" type="date" required></div>
        </div>
        <div class="form__row">
          <div class="field"><label for="c-gaeste">Anzahl Gäste *</label><input id="c-gaeste" name="gaeste" type="number" min="1" max="2000" inputmode="numeric" required></div>
          <div class="field"><label for="c-service">Lieferung oder Abholung *</label>
            <select id="c-service" name="service" required><option value="" selected disabled>Bitte wählen</option><option>Lieferung</option><option>Abholung in der Enge</option><option>Noch offen</option></select></div>
        </div>
        <div class="field"><label for="c-ort">Ort des Anlasses (optional)</label><input id="c-ort" name="eventort" type="text" autocomplete="street-address" placeholder="z. B. Firmenadresse in Zürich"></div>
        <div class="form__row">
          <div class="field"><label for="c-name">Name *</label><input id="c-name" name="name" type="text" required autocomplete="name"></div>
          <div class="field"><label for="c-firma">Firma (optional)</label><input id="c-firma" name="firma" type="text" autocomplete="organization"></div>
        </div>
        <div class="form__row">
          <div class="field"><label for="c-tel">Telefon *</label><input id="c-tel" name="telefon" type="tel" required autocomplete="tel"></div>
          <div class="field"><label for="c-mail">E-Mail *</label><input id="c-mail" name="email" type="email" required autocomplete="email"></div>
        </div>
        <div class="field"><label for="c-msg">Wünsche (optional)</label><textarea id="c-msg" name="bemerkung" rows="4" placeholder="z. B. Lieblingsgerichte, vegetarisch, Allergien, Budget pro Person"></textarea></div>
        <button class="btn" type="submit">Anfrage senden <span class="arrow" aria-hidden="true">→</span></button>
        <p class="form__status" role="status" aria-live="polite"></p>
        <p class="form__small">Mit dem Absenden stimmen Sie der Bearbeitung Ihrer Angaben gemäss <a href="/datenschutz" style="text-decoration:underline">Datenschutzerklärung</a> zu.</p>
      </form>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="section-head">
      <div><p class="eyebrow">Häufige Fragen</p><h2 class="h2">Gut <em>zu wissen</em>.</h2></div>
      <p class="lead">Antworten rund um Catering und Partyservice von Ruen Thai. Sie haben ein Restaurant-Anliegen? Zur <a href="/enge" style="text-decoration:underline">Enge</a> oder nach <a href="/thalwil" style="text-decoration:underline">Thalwil</a>.</p>
    </div>
    {faq_html(CATERING_FAQ)}
  </div>
</section>

</main>
""" + footer()
    return out


# ---------------------------------------------------------------- Dateien
def write(name, content):
    (ROOT / name).write_text(content, encoding="utf-8")
    print("wrote", name)


def make_icons():
    icon = Image.open(ROOT / "assets/img/logo-icon.png").convert("RGBA")
    ico_src = Image.new("RGBA", (256, 256), (255, 251, 244, 255))
    s = 200 / icon.height
    ic = icon.resize((round(icon.width * s), 200))
    ico_src.paste(ic, ((256 - ic.width) // 2, 28), ic)
    ico_src.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    ico_src.resize((180, 180)).convert("RGB").save(ROOT / "apple-touch-icon.png")
    og = Image.open(ROOT / "assets/img/hero-02.webp").convert("RGB")
    w, h = og.size
    th = round(w * 630 / 1200)
    og = og.crop((0, (h - th) // 2, w, (h - th) // 2 + th)).resize((1200, 630), Image.LANCZOS)
    og.save(ROOT / "assets/img/og-image.jpg", quality=82, optimize=True)


def main():
    make_icons()
    write("index.html", page_home())
    for l in LOCS:
        write(f'{l["file"]}.html', page_location(l))
    write("ueber-uns.html", page_about())
    write("kontakt.html", page_contact())
    write("catering.html", page_catering())
    write("impressum.html", page_impressum())
    write("datenschutz.html", page_datenschutz())
    write("404.html", page_404())

    if STAGING:
        write("robots.txt", "User-agent: *\nDisallow: /\n")
        for f in ("sitemap.xml", "llms.txt"):
            if (ROOT / f).exists():
                (ROOT / f).unlink(); print("removed", f, "(Staging)")
        return

    pages = ["/"] + [f'/{l["file"]}' for l in LOCS] + ["/catering", "/ueber-uns", "/kontakt", "/impressum", "/datenschutz"]
    urls = "".join(
        f"  <url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod><changefreq>{'weekly' if p == '/' else 'monthly'}</changefreq><priority>{'1.0' if p == '/' else ('0.9' if p.count('/') == 1 and p not in ('/impressum', '/datenschutz') else '0.3')}</priority></url>\n"
        for p in pages
    )
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')

    bots = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "Applebot-Extended", "OAI-SearchBot", "Bytespider", "Amazonbot", "Meta-ExternalAgent"]
    robots = "User-agent: *\nAllow: /\nDisallow: /anfrage.php\n\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"Sitemap: {BASE}/sitemap.xml\n"
    write("robots.txt", robots)

    lines = [f"# {SITE['name']}", "", f"> {SITE['name']} ist eine Thai-Restaurantgruppe mit zwei Restaurants (Zürich Enge, Thalwil) und einem Take Away (Zürich Badenerstrasse). Das erste Restaurant eröffnete {SITE['since']} in Thalwil.", "", "## Standorte", ""]
    for l in LOCS:
        lines.append(f"- [{l['name']}]({BASE}/{l['file']}): {l['typeLabel']}, {addr_line(l)}, Tel. {l['telDisplay']}, Preisniveau {l['price']} pro Person.")
    lines += ["", "## Wichtigste Seiten", "", f"- [Startseite]({BASE}/): Übersicht und Standortwahl", f"- [Catering]({BASE}/catering): Thai-Catering und Partyservice für Firmenanlässe und Feiern, Anfrage online", f"- [Über uns]({BASE}/ueber-uns): Geschichte seit {SITE['since']}", f"- [Kontakt]({BASE}/kontakt): Adressen, Telefon, Öffnungszeiten", f"- [Häufige Fragen]({BASE}/#faq)", "", "## Kontakt", "", f"Telefon Enge: {SITE['mainPhoneDisplay']} · Thalwil: 043 443 59 89 · Take Away: 043 817 47 80", ""]
    write("llms.txt", "\n".join(lines))


if __name__ == "__main__":
    main()
