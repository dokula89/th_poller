<?php
// Use shared DB connection
require_once __DIR__ . '/db_connection.php';
_no_cache_headers();

$mysqli = get_shared_db();
if (!$mysqli) {
    out_json(['ok' => false, 'error' => 'DB connection failed'], 500);
}

// Get metro_name from query parameter
$metro_name = isset($_GET['metro']) ? trim($_GET['metro']) : '';

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
    
    // Count google_addresses where king_county_parcels_id IS NULL (only) AND metro_id matches
        // Also exclude addresses with parcel_error
        // Only count King County addresses (json_dump must contain "King County")
        $stmt2 = $mysqli->prepare("
            SELECT COUNT(*) as empty_count 
            FROM google_addresses 
            WHERE metro_id = ? 
            AND king_county_parcels_id IS NULL
            AND (parcel_error IS NULL OR parcel_error = '')
            AND json_dump LIKE '%King County%'
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
