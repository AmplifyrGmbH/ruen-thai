<?php
/* Passwortschutz (Staging) + Auslieferung der statischen Seiten.
   Alle Anfragen laufen über dieses Skript (siehe .htaccess). Ohne gültige
   Zugangsdaten antwortet der Server mit 401 (HTTP Basic Auth), Suchmaschinen sehen
   also keine Inhalte. Zusätzlich: X-Robots-Tag noindex auf jeder Antwort.
   Zugangsdaten stehen in gate.config.php (nicht im Repo). Fehlt die Datei, bleibt
   die Seite gesperrt (fail closed). */
header('X-Robots-Tag: noindex, nofollow, noarchive, nosnippet');
header('Cache-Control: private, no-store');

$cfg = @include __DIR__ . '/gate.config.php';
if (!is_array($cfg) || empty($cfg['hash'])) {
    http_response_code(503);
    exit('Gesperrt: Zugang nicht konfiguriert.');
}

function gate_credentials() {
    $u = $_SERVER['PHP_AUTH_USER'] ?? null;
    $p = $_SERVER['PHP_AUTH_PW'] ?? null;
    if ($u === null) {
        $h = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
        if (stripos($h, 'Basic ') === 0) {
            $d = base64_decode(substr($h, 6), true);
            if ($d !== false && strpos($d, ':') !== false) { [$u, $p] = explode(':', $d, 2); }
        }
    }
    return [$u, $p];
}

[$u, $p] = gate_credentials();
$ok = $u !== null && $p !== null && hash_equals($cfg['user'], (string)$u) && password_verify((string)$p, $cfg['hash']);
if (!$ok) {
    usleep(400000); // bremst Durchprobieren
    header('WWW-Authenticate: Basic realm="Ruen Thai (Entwurf)", charset="UTF-8"');
    http_response_code(401);
    header('Content-Type: text/plain; charset=utf-8');
    exit('Zugang erforderlich.');
}

$root = __DIR__;
$path = urldecode((string)parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
$path = '/' . ltrim(str_replace(["\0", '\\'], '', $path), '/');
if (strpos($path, '..') !== false) { http_response_code(400); exit; }

// Sperre: Entwicklungs- und Konfigurationsdateien nie ausliefern
if (preg_match('#(^|/)(\.|_src/|tools/|data/|gate\.|README|\.github)#i', $path) && $path !== '/') {
    http_response_code(404); readfile($root . '/404.html'); exit;
}

if ($path === '/') { $file = $root . '/index.html'; }
elseif ($path === '/anfrage.php') { require $root . '/anfrage.php'; exit; }
elseif (is_file($root . $path)) { $file = $root . $path; }
elseif (is_file($root . $path . '.html')) { $file = $root . $path . '.html'; }
else { http_response_code(404); header('Content-Type: text/html; charset=utf-8'); readfile($root . '/404.html'); exit; }

// .html direkt angefragt -> auf saubere URL umleiten (wie .htaccess ohne Gate)
if (substr($file, -5) === '.html' && substr($path, -5) === '.html' && $path !== '/index.html') {
    header('Location: ' . substr($path, 0, -5), true, 301); exit;
}

$types = ['html'=>'text/html; charset=utf-8','css'=>'text/css; charset=utf-8','js'=>'application/javascript; charset=utf-8','json'=>'application/json',
  'webp'=>'image/webp','jpg'=>'image/jpeg','jpeg'=>'image/jpeg','png'=>'image/png','ico'=>'image/x-icon','svg'=>'image/svg+xml',
  'woff2'=>'font/woff2','txt'=>'text/plain; charset=utf-8','xml'=>'application/xml'];
$ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
header('Content-Type: ' . ($types[$ext] ?? 'application/octet-stream'));
header('Content-Length: ' . filesize($file));
readfile($file);
