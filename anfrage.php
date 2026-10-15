<?php
/* Reservations- und Catering-Anfragen -> E-Mail. Läuft auf Hostpoint (PHP + mail()).
   EINRICHTEN: Empfängeradressen und Absender unten eintragen. Solange eine
   Adresse leer ist, meldet das Formular "noch nicht aktiviert" und verweist
   auf das Telefon (es wird dann nichts versendet).
   Der Gast erhält eine automatische Eingangsbestätigung, wenn er eine E-Mail angibt. */
header('Content-Type: application/json; charset=utf-8');

$RECIPIENTS = [
    'Ruen Thai by Suthita' => '',   // TODO: Reservationen Enge, z. B. enge@ihre-domain.ch
    'Ruen Thai Thalwil'    => '',   // TODO: Reservationen Thalwil
    'Catering'             => '',   // TODO: Catering-Anfragen, z. B. catering@ihre-domain.ch
];
$FROM = '';                          // TODO: Absender auf eigener Domain, z. B. noreply@ihre-domain.ch
$PHONES = ['Ruen Thai by Suthita' => '044 281 14 14', 'Ruen Thai Thalwil' => '043 443 59 89', 'Catering' => '044 281 14 14'];

date_default_timezone_set('Europe/Zurich');

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
function subject($s) { return '=?UTF-8?B?' . base64_encode($s) . '?='; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(false, 'Ungültige Anfrage.', 405);
if (!empty($_POST['website'])) out(true);                       // Honeypot: Bots still "erfolgreich"

$typ = ($_POST['typ'] ?? 'reservation') === 'catering' ? 'catering' : 'reservation';
$name = clean($_POST['name'] ?? '');
$tel = clean($_POST['telefon'] ?? '', 40);
$mail = clean($_POST['email'] ?? '', 120);
$datum = clean($_POST['datum'] ?? '', 20);
$msg = trim(mb_substr((string)($_POST['bemerkung'] ?? ''), 0, 1500));

if ($name === '' || $tel === '' || $datum === '') out(false, 'Bitte füllen Sie alle Pflichtfelder aus.', 422);
if ($mail !== '' && !filter_var($mail, FILTER_VALIDATE_EMAIL)) out(false, 'Bitte prüfen Sie die E-Mail-Adresse.', 422);

$d = DateTime::createFromFormat('!Y-m-d', $datum);
$today = new DateTime('today');
if (!$d || $d < $today || $d > (clone $today)->modify('+1 year')) out(false, 'Bitte wählen Sie ein Datum ab heute.', 422);
$datumText = $d->format('d.m.Y');

if ($typ === 'reservation') {
    $ort = clean($_POST['ort'] ?? '');
    $zeit = clean($_POST['zeit'] ?? '', 10);
    $pers = clean($_POST['personen'] ?? '', 20);
    if (!isset($RECIPIENTS[$ort]) || $ort === 'Catering') out(false, 'Bitte wählen Sie ein Restaurant.', 422);
    if ($zeit === '' || $pers === '') out(false, 'Bitte füllen Sie alle Pflichtfelder aus.', 422);
    $key = $ort;
    $betreff = "Reservation $ort: $name, $datumText $zeit";
    $body = "Neue Reservationsanfrage\n\nRestaurant: $ort\nName: $name\nTelefon: $tel\nE-Mail: " . ($mail ?: '-') .
            "\nDatum: $datumText\nUhrzeit: $zeit\nPersonen: $pers\n\nBemerkung:\n" . ($msg ?: '-') . "\n";
    $gastBetreff = "Ihre Reservationsanfrage bei $ort";
    $gastText = "Guten Tag $name\n\nVielen Dank für Ihre Reservationsanfrage. Wir haben sie erhalten und bestätigen Ihren Tisch so rasch wie möglich.\n\n" .
                "Restaurant: $ort\nDatum: $datumText\nUhrzeit: $zeit\nPersonen: $pers\n\n" .
                "Bitte beachten Sie: Ihre Reservation gilt erst nach unserer Bestätigung.";
} else {
    $anlass = clean($_POST['anlass'] ?? '', 60);
    $gaeste = clean($_POST['gaeste'] ?? '', 10);
    $service = clean($_POST['service'] ?? '', 60);
    $eventort = clean($_POST['eventort'] ?? '', 200);
    $firma = clean($_POST['firma'] ?? '', 120);
    if ($anlass === '' || $gaeste === '' || $service === '' || $mail === '') out(false, 'Bitte füllen Sie alle Pflichtfelder aus.', 422);
    if (!ctype_digit($gaeste) || (int)$gaeste < 1) out(false, 'Bitte geben Sie die Anzahl Gäste als Zahl an.', 422);
    $key = 'Catering';
    $betreff = "Catering-Anfrage: $anlass, $gaeste Gäste, $datumText ($name)";
    $body = "Neue Catering-Anfrage\n\nAnlass: $anlass\nDatum: $datumText\nGäste: $gaeste\nLieferung/Abholung: $service\nOrt des Anlasses: " . ($eventort ?: '-') .
            "\n\nName: $name\nFirma: " . ($firma ?: '-') . "\nTelefon: $tel\nE-Mail: $mail\n\nWünsche:\n" . ($msg ?: '-') . "\n";
    $gastBetreff = 'Ihre Catering-Anfrage bei Ruen Thai';
    $gastText = "Guten Tag $name\n\nVielen Dank für Ihre Catering-Anfrage. Wir haben sie erhalten und melden uns mit einem Menüvorschlag und einer Offerte.\n\n" .
                "Anlass: $anlass\nDatum: $datumText\nGäste: $gaeste\nLieferung/Abholung: $service";
}

$to = $RECIPIENTS[$key] ?? '';
if ($to === '' || $FROM === '') out(false, 'Die Online-Anfrage ist noch nicht aktiviert. Bitte rufen Sie uns an: ' . $PHONES[$key] . '.', 503);

$headers = "From: Ruen Thai Website <$FROM>\r\nContent-Type: text/plain; charset=UTF-8\r\n";
if ($mail !== '') $headers .= "Reply-To: $mail\r\n";
$ok = mail($to, subject($betreff), $body, $headers, "-f$FROM");
if (!$ok) out(false, 'Das hat leider nicht geklappt. Bitte rufen Sie uns an: ' . $PHONES[$key] . '.', 500);

// Eingangsbestätigung an den Gast (Fehler hier blockieren die Anfrage nicht)
if ($mail !== '') {
    $gastText .= "\n\nFragen? Rufen Sie uns an: " . $PHONES[$key] . "\n\nFreundliche Grüsse\nRuen Thai\n";
    $gastHeaders = "From: Ruen Thai <$FROM>\r\nReply-To: $to\r\nContent-Type: text/plain; charset=UTF-8\r\n";
    @mail($mail, subject($gastBetreff), $gastText, $gastHeaders, "-f$FROM");
}
out(true);
