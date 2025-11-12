<?php
// the_matcher.php: API endpoint to match a given address to google_places table and return IDs
// Usage: GET or POST with ?address=... (URL-encoded)
// Returns: JSON { match: true/false, google_addresses_id, google_places_id, matched_fulladdress, matched_street }

require_once __DIR__ . '/functions.php';
header('Content-Type: application/json; charset=utf-8');

$address = isset($_REQUEST['address']) ? trim($_REQUEST['address']) : '';
if ($address === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Missing address parameter']);
    exit;
}

$mysqli = get_db_connection();
if (!$mysqli) {
    http_response_code(500);
    echo json_encode(['error' => 'DB connect error']);
    exit;
}

$match = match_google_address($mysqli, $address);
if ($match) {
    echo json_encode(['match' => true] + $match);
} else {
    echo json_encode(['match' => false]);
}
$mysqli->close();
