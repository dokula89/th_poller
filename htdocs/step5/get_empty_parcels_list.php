<?php
// Use shared DB connection
require_once __DIR__ . '/db_connection.php';
_no_cache_headers();

$mysqli = get_shared_db();
if (!$mysqli) {
    out_json(['ok' => false, 'error' => 'DB connection failed'], 500);
}

$metro = isset($_GET['metro']) ? trim($_GET['metro']) : '';
$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 20; // default 20 per page
$page  = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
$offset = ($page - 1) * $limit;

try {
    // Build WHERE clause - exclude addresses with parcel_error
    // Only include addresses that have "King County" in json_dump (for King County Parcel Viewer)
    $where = [
        "ga.king_county_parcels_id IS NULL", 
        "(ga.parcel_error IS NULL OR ga.parcel_error = '')",
        "ga.json_dump LIKE '%King County%'"
    ];
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
                ga.parcel_error,
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
            'metro_name' => $r['metro_name'],
            'parcel_error' => $r['parcel_error'] ?? ''
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
