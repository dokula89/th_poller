<?php
// Use shared DB connection
require_once __DIR__ . '/db_connection.php';
_no_cache_headers();

$mysqli = get_shared_db();
if (!$mysqli) {
    out_json(['ok' => false, 'error' => 'DB connection failed'], 500);
}

$limit = isset($_GET['limit']) ? max(1, min(1000, (int)$_GET['limit'])) : 500;

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
