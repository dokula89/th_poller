<?php
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');

function out_json($arr, $code = 200) {
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// Basic DB config
$DB_HOST = '127.0.0.1';
$DB_USER = 'local_uzr';
$DB_PASS = 'fuck';
$DB_NAME = 'offta';
$DB_PORT = 3306;

// Get metro_name from query parameter
$metro_name = isset($_GET['metro']) ? trim($_GET['metro']) : '';

$mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($mysqli->connect_errno) {
    out_json(['ok' => false, 'error' => 'DB connection failed: ' . $mysqli->connect_error], 500);
}
$mysqli->set_charset('utf8mb4');

try {
    if (empty($metro_name) || $metro_name === 'All') {
        out_json(['ok' => true, 'empty_count' => 0, 'metro' => $metro_name]);
    }
    
    // First, get the metro_id for the given metro_name from major_metros table
    $stmt = $mysqli->prepare("SELECT id FROM major_metros WHERE metro_name = ? LIMIT 1");
    if (!$stmt) {
        out_json(['ok' => false, 'error' => 'Prepare failed: ' . $mysqli->error], 500);
    }
    
    $stmt->bind_param('s', $metro_name);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result->fetch_assoc();
    $stmt->close();
    
    if (!$row) {
        out_json(['ok' => true, 'empty_count' => 0, 'metro' => $metro_name, 'message' => 'Metro not found']);
    }
    
    $metro_id = (int)$row['id'];
    
    // Count google_addresses where king_county_parcels_id IS NULL or empty AND metro_id matches
        // Count google_addresses where king_county_parcels_id IS NULL (only) AND metro_id matches
        $stmt2 = $mysqli->prepare("
            SELECT COUNT(*) as empty_count 
            FROM google_addresses 
            WHERE metro_id = ? 
            AND king_county_parcels_id IS NULL
        ");
    
    if (!$stmt2) {
        out_json(['ok' => false, 'error' => 'Prepare count failed: ' . $mysqli->error], 500);
    }
    
    $stmt2->bind_param('i', $metro_id);
    $stmt2->execute();
    $result2 = $stmt2->get_result();
    $row2 = $result2->fetch_assoc();
    $stmt2->close();
    
    $empty_count = (int)($row2['empty_count'] ?? 0);
    
    out_json([
        'ok' => true, 
        'empty_count' => $empty_count,
        'metro' => $metro_name,
        'metro_id' => $metro_id
    ]);
    
} catch (Throwable $e) {
    out_json(['ok' => false, 'error' => $e->getMessage()], 500);
} finally {
    if ($mysqli) $mysqli->close();
}
