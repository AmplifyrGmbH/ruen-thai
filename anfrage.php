<?php
/* Reservationsanfrage -> E-Mail. Läuft auf Hostpoint (PHP + mail()).
   EINRICHTEN: Empfängeradresse je Restaurant unten eintragen. Solange eine
   Adresse leer ist, meldet das Formular "noch nicht aktiviert" und verweist
   auf das Telefon (es wird dann nichts versendet). */
header('Content-Type: application/json; charset=utf-8');

$RECIPIENTS = [
    'Ruen Thai by Suthita' => '',   // TODO: z. B. enge@ihre-domain.ch
    'Ruen Thai Thalwil'    => '',   // TODO
];
$FROM = '';                          // TODO: Absender auf eigener Domain, z. B. noreply@ihre-domain.ch

function out($ok, $msg = '', $code = 200) {
    http_response_code($code);
    echo json_encode(['ok' => $ok, 'message' => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}
function clean($v, $max = 300) {
    $v = trim((string)$v);
    $v = str_replace(["\r", "\n"], ' ', $v);
    return mb_substr($v, 0, $max);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(false, 'Ungültige Anfrage.', 405);
if (!empty($_POST['website'])) out(true);                       // Honeypot: Bots still "erfolgreich"

$ort = clean($_POST['ort'] ?? '');
$name = clean($_POST['name'] ?? '');
$tel = clean($_POST['telefon'] ?? '', 40);
$mail = clean($_POST['email'] ?? '', 120);
$datum = clean($_POST['datum'] ?? '', 20);
$zeit = clean($_POST['zeit'] ?? '', 10);
$pers = clean($_POST['personen'] ?? '', 20);
$msg = trim(mb_substr((string)($_POST['bemerkung'] ?? ''), 0, 1000));

if ($name === '' || $tel === '' || $datum === '' || $zeit === '' || $pers === '') out(false, 'Bitte füllen Sie alle Pflichtfelder aus.', 422);
if ($mail !== '' && !filter_var($mail, FILTER_VALIDATE_EMAIL)) out(false, 'Bitte prüfen Sie die E-Mail-Adresse.', 422);

$to = $RECIPIENTS[$ort] ?? '';
if ($to === '' || $FROM === '') out(false, 'Die Online-Reservation ist noch nicht aktiviert. Bitte rufen Sie uns an.', 503);

$body = "Neue Reservationsanfrage\n\nRestaurant: $ort\nName: $name\nTelefon: $tel\nE-Mail: " . ($mail ?: '-') .
        "\nDatum: $datum\nUhrzeit: $zeit\nPersonen: $pers\n\nBemerkung:\n" . ($msg ?: '-') . "\n";
$headers = "From: Ruen Thai Website <$FROM>\r\nContent-Type: text/plain; charset=UTF-8\r\n";
if ($mail !== '') $headers .= "Reply-To: $mail\r\n";

$ok = mail($to, '=?UTF-8?B?' . base64_encode("Reservation $ort: $name, $datum $zeit") . '?=', $body, $headers);
$ok ? out(true) : out(false, 'Das hat leider nicht geklappt. Bitte rufen Sie uns an.', 500);
