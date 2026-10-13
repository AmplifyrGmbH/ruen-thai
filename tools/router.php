<?php
// Lokaler Entwicklungs-Router (php -S localhost:8000 tools/router.php) — bildet die Clean-URLs aus .htaccess nach.
$root = dirname(__DIR__);
$path = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));
if ($path === '/') { readfile($root . '/index.html'); return true; }
$file = $root . $path;
if (is_file($file)) { return false; }
if (is_file($file . '.html')) { readfile($file . '.html'); return true; }
http_response_code(404);
readfile($root . '/404.html');
return true;
