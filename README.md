# Ruen Thai — Website

Statische Mehrseiten-Website (kein Framework, kein Build-Tool auf dem Server) für Hostpoint.

| Seite | URL | Datei |
|---|---|---|
| Landingpage mit Standortwahl | `/` | `index.html` |
| Ruen Thai by Suthita (Zürich Enge) | `/enge` | `enge.html` |
| Ruen Thai Thalwil | `/thalwil` | `thalwil.html` |
| Ruenthai 2 Take Away (Badenerstrasse) | `/badenerstrasse` | `badenerstrasse.html` |
| Über uns / Kontakt | `/ueber-uns`, `/kontakt` | `ueber-uns.html`, `kontakt.html` |
| Impressum / Datenschutz / 404 | `/impressum`, `/datenschutz` | `*.html` |

## Inhalte ändern
Die HTML-Seiten werden aus `data/restaurants.json` (Adressen, Zeiten, Menü, Bewertungen, FAQ) generiert:

```bash
python3 tools/build.py      # erzeugt alle .html, sitemap.xml, robots.txt, llms.txt, Icons
```
Danach die geänderten Dateien committen. Design: `assets/css/style.css`, Verhalten: `assets/js/main.js`.

## Lokal ansehen
```bash
php -S localhost:8000 tools/router.php
```

## Staging: Passwortschutz und noindex (aktueller Zustand)
Die Seite ist **passwortgeschützt und komplett noindex**:
- Jede Anfrage läuft über `gate.php` (HTTP-Basic-Auth, Benutzer `ruenthai`). Ohne Passwort gibt es nur `401`.
- `X-Robots-Tag: noindex` (Header), `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">` auf jeder Seite, `robots.txt` mit `Disallow: /`, keine `sitemap.xml`/`llms.txt`.
- Das Passwort steht **nicht im Repo** (das Repo ist öffentlich). Der bcrypt-Hash kommt aus dem GitHub-Secret `GATE_PASSWORD_HASH`; die Action erzeugt daraus auf dem Server `gate.config.php`. Lokal liegt eine Kopie in `gate.config.php` (gitignored). Fehlt die Datei, bleibt die Seite gesperrt.
- Passwort ändern: neuen Hash erzeugen (`php -r 'echo password_hash("NEUES-PASSWORT", PASSWORD_BCRYPT, ["cost"=>12]);'`), Secret aktualisieren, Action erneut ausführen.

**Livegang:** `STAGING = False` in `tools/build.py`, `python3 tools/build.py`, dann `.htaccess.live` als `.htaccess` verwenden (und `gate.php` entfernen), Impressum/Datenschutz ausfüllen.

## Hostpoint
- Alles ausser `tools/`, `data/`, `_src/` hochladen (macht die GitHub Action `deploy-hostpoint.yml` bei Push auf `main`; Secrets `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`, `FTP_SERVER_DIR`, `GATE_PASSWORD_HASH` setzen).
- `.htaccess` (Staging) erzwingt HTTPS und leitet alles über `gate.php`; `.htaccess.live` enthält die Live-Variante mit sauberen URLs, 404-Seite und Caching.
- Reservationsformular: in `anfrage.php` die Empfänger-E-Mail-Adressen (`$RECIPIENTS`) und `$FROM` (Absender auf eigener Domain) eintragen. Solange sie leer sind, verweist das Formular aufs Telefon.

## Vor dem Livegang klären (TODO)
- Domain: `data/restaurants.json` → `site.url` (aktuell Platzhalter `https://ruenthairestaurant.ch`), danach `build.py` neu laufen lassen.
- **Impressum und Datenschutz** vom Betreiber ausfüllen lassen (Firma, Inhaber, UID, E-Mail) und rechtlich prüfen.
- Öffnungszeiten, Preise, Telefonnummern mit dem Betreiber bestätigen (Quellen: frühere Website im Web-Archiv, Google, zuri.net; teils widersprüchlich).
- Fotos: aktuell Symbolfotos (Pexels) plus ein Archivfoto vom Gastraum. Echte Fotos des Betreibers einsetzen, Menüs vollständig übernehmen.
- Optional: Google-Business-Profile verlinken (`sameAs` im Schema), Geo-Koordinaten ergänzen.
