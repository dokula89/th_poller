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

$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 500;

$mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($mysqli->connect_errno) {
    out_json(['ok' => false, 'error' => 'DB connection failed: ' . $mysqli->connect_error], 500);
}
$mysqli->set_charset('utf8mb4');

try {
    // Get cities with 911_website
    $sql = "SELECT id, city_name, metro_id, `911_website` 
            FROM cities 
            WHERE `911_website` IS NOT NULL AND `911_website` <> '' 
            ORDER BY city_name 
            LIMIT " . $limit;
    
    $res = $mysqli->query($sql);
    if (!$res) {
        out_json(['ok' => false, 'error' => 'Query failed: ' . $mysqli->error], 500);
    }
    
    $rows = [];
    while ($r = $res->fetch_assoc()) {
        $rows[] = [
            'id' => (int)$r['id'],
            'city_name' => $r['city_name'],
            'metro_id' => (int)$r['metro_id'],
            '911_website' => $r['911_website'],
        ];
    }
    
    out_json(['ok' => true, 'rows' => $rows, 'total' => count($rows)]);
} catch (Throwable $e) {
    out_json(['ok' => false, 'error' => $e->getMessage()], 500);
} finally {
    if ($mysqli) $mysqli->close();
}
