<?php
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');

function out_json($arr, $code = 200) {
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// Basic DB config (keep consistent with other step5 endpoints)
$DB_HOST = '127.0.0.1';
$DB_USER = 'local_uzr';
$DB_PASS = 'fuck';
$DB_NAME = 'offta';
$DB_PORT = 3306;

$metro = isset($_GET['metro']) ? trim($_GET['metro']) : '';
$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 20; // default 20 per page
$page  = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
$offset = ($page - 1) * $limit;

$mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($mysqli->connect_errno) {
    out_json(['ok' => false, 'error' => 'DB connection failed: ' . $mysqli->connect_error], 500);
}
$mysqli->set_charset('utf8mb4');

try {
    // Build WHERE clause
    $where = ["ga.king_county_parcels_id IS NULL"]; // NULL-only per spec
    $params = [];
    $types = '';

    if (!empty($metro) && strtolower($metro) !== 'all') {
        $where[] = "m.metro_name = ?";
        $params[] = $metro;
        $types .= 's';
    }

    $whereSql = !empty($where) ? ' WHERE ' . implode(' AND ', $where) : '';

    // Query addresses missing king_county_parcels_id, join metros for name
    // Note: google_addresses typically stores latitude/longitude as 'latitude'/'longitude' and does not
    // have a 'formatted_address' column; we will extract it from json_dump when available.
    $sql = "SELECT 
                ga.id,
                ga.place_id,
                ga.source,
                ga.building_name,
                ga.latitude,
                ga.longitude,
                ga.json_dump,
                ga.metro_id,
                m.metro_name
            FROM google_addresses ga
            JOIN major_metros m ON ga.metro_id = m.id
            $whereSql
            ORDER BY ga.id DESC
            LIMIT ? OFFSET ?";

    $params[] = $limit;
    $params[] = $offset;
    $types .= 'ii';

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
    // Helper to extract formatted_address from json_dump quickly
    $extract_fmt = function (?string $jsonDump) {
        if (!$jsonDump) return null;
        if (preg_match('~"formatted_address"\s*:\s*"([^"]+)"~i', $jsonDump, $m)) {
            return $m[1];
        }
        return null;
    };

    while ($r = $res->fetch_assoc()) {
        $fmt = $extract_fmt($r['json_dump'] ?? null);
        if (!$fmt) {
            // fallback to building_name or place_id
            $fmt = $r['building_name'] ?: ($r['place_id'] ?: '');
        }
        $rows[] = [
            'id' => (int)$r['id'],
            'formatted_address' => $fmt,
            'place_id' => $r['place_id'],
            'lat' => isset($r['latitude']) ? (float)$r['latitude'] : null,
            'lng' => isset($r['longitude']) ? (float)$r['longitude'] : null,
            'metro_id' => isset($r['metro_id']) ? (int)$r['metro_id'] : null,
            'metro_name' => $r['metro_name']
        ];
    }

    out_json([
        'ok' => true,
        'rows' => $rows,
        'count' => count($rows),
        'limit' => $limit,
        'page' => $page,
        'has_next' => (count($rows) === $limit),
        'metro' => $metro ?: 'All'
    ]);
} catch (Throwable $e) {
    out_json(['ok' => false, 'error' => $e->getMessage()], 500);
} finally {
    if ($mysqli) $mysqli->close();
}
