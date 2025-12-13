<?php
// Use shared DB connection
require_once __DIR__ . '/db_connection.php';
_no_cache_headers();

$mysqli = get_shared_db();
if (!$mysqli) {
    out_json(['ok' => false, 'error' => 'DB connection failed'], 500);
}

$metro = isset($_GET['metro']) ? trim($_GET['metro']) : '';
$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 500;

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
