<?php
// Use shared DB connection
require_once __DIR__ . '/db_connection.php';
_no_cache_headers();

$mysqli = get_shared_db();
if (!$mysqli) {
    out_json(['ok' => false, 'error' => 'DB connection failed'], 500);
}

$onlyNames = isset($_GET['only']) && strtolower($_GET['only']) === 'names';
$hasParcel = isset($_GET['has_parcel']) && ($_GET['has_parcel'] === '1' || strtolower($_GET['has_parcel']) === 'true');

try {
    if ($onlyNames) {
        // Distinct metro names for dropdown
        $sql = "SELECT DISTINCT metro_name FROM major_metros WHERE metro_name IS NOT NULL AND metro_name <> ''";
        if ($hasParcel) {
            $sql .= " AND parcel_link IS NOT NULL AND parcel_link <> ''";
        }
        $sql .= " ORDER BY metro_name";
        $res = $mysqli->query($sql);
        if (!$res) {
            out_json(['ok' => false, 'error' => 'Query failed: ' . $mysqli->error], 500);
        }
        $names = [];
        while ($row = $res->fetch_assoc()) {
            $names[] = $row['metro_name'];
        }
        out_json(['ok' => true, 'names' => $names, 'count' => count($names)]);
    } else {
        // Full rows
        $limit = isset($_GET['limit']) ? max(1, (int)$_GET['limit']) : 500;
        $where = [];
        if ($hasParcel) {
            $where[] = "parcel_link IS NOT NULL AND parcel_link <> ''";
        }
        $whereSql = '';
        if (!empty($where)) {
            $whereSql = ' WHERE ' . implode(' AND ', $where);
        }
        $sql = "SELECT id, metro_name, county_name, lat, lng, parcel_link FROM major_metros" . $whereSql . " ORDER BY metro_name LIMIT " . $limit;
        $res = $mysqli->query($sql);
        if (!$res) {
            out_json(['ok' => false, 'error' => 'Query failed: ' . $mysqli->error], 500);
        }
        $rows = [];
        while ($r = $res->fetch_assoc()) {
            $rows[] = [
                'id' => (int)$r['id'],
                'metro_name' => $r['metro_name'],
                'county_name' => $r['county_name'],
                'lat' => isset($r['lat']) ? (float)$r['lat'] : null,
                'lng' => isset($r['lng']) ? (float)$r['lng'] : null,
                'parcel_link' => $r['parcel_link'],
            ];
        }
        out_json(['ok' => true, 'rows' => $rows, 'total' => count($rows)]);
    }
} catch (Throwable $e) {
    out_json(['ok' => false, 'error' => $e->getMessage()], 500);
} finally {
    if ($mysqli) $mysqli->close();
}
