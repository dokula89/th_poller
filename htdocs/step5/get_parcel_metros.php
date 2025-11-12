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

$metro = isset($_GET['metro']) ? trim($_GET['metro']) : '';
$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 500;

$mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($mysqli->connect_errno) {
    out_json(['ok' => false, 'error' => 'DB connection failed: ' . $mysqli->connect_error], 500);
}
$mysqli->set_charset('utf8mb4');

try {
    // Query google_addresses (parcel table) joined with major_metros for metro_name
    // Get distinct metro rows that have parcels
    $where = [];
    $params = [];
    $types = '';
    
    if (!empty($metro) && strtolower($metro) !== 'all') {
        $where[] = "m.metro_name = ?";
        $params[] = $metro;
        $types .= 's';
    }
    
    $whereSql = !empty($where) ? ' WHERE ' . implode(' AND ', $where) : '';
    
    // Get metros with their parcel links and count of addresses
    $sql = "SELECT 
                m.id,
                m.metro_name,
                m.county_name,
                m.parcel_link,
                COUNT(g.id) as address_count
            FROM major_metros m
            LEFT JOIN google_addresses g ON g.metro_id = m.id
            $whereSql
            GROUP BY m.id, m.metro_name, m.county_name, m.parcel_link
            HAVING m.parcel_link IS NOT NULL AND m.parcel_link <> ''
            ORDER BY m.metro_name, m.county_name
            LIMIT ?";
    
    $params[] = $limit;
    $types .= 'i';
    
    $stmt = $mysqli->prepare($sql);
    if (!$stmt) {
        out_json(['ok' => false, 'error' => 'Prepare failed: ' . $mysqli->error], 500);
    }
    
    if (!empty($params)) {
        $stmt->bind_param($types, ...$params);
    }
    
    $stmt->execute();
    $res = $stmt->get_result();
    
    $rows = [];
    while ($r = $res->fetch_assoc()) {
        $rows[] = [
            'id' => (int)$r['id'],
            'metro_name' => $r['metro_name'],
            'county_name' => $r['county_name'],
            'parcel_link' => $r['parcel_link'],
            'address_count' => (int)$r['address_count']
        ];
    }
    
    out_json(['ok' => true, 'rows' => $rows, 'total' => count($rows), 'metro_filter' => $metro ?: 'All']);
} catch (Throwable $e) {
    out_json(['ok' => false, 'error' => $e->getMessage()], 500);
} finally {
    if ($mysqli) $mysqli->close();
}
