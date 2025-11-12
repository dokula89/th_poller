<?php
/**
 * API endpoint to get row counts for database tables
 * This allows the sync feature to check remote database status via HTTP
 * 
 * Usage: http://yourdomain.com/get_table_counts.php
 * Returns: JSON with table names and row counts
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database connection
$host = 'localhost';
$user = 'seattlelisted_usr';
$pass = 'T@5z6^pl}';
$db = 'offta';

try {
    $conn = new mysqli($host, $user, $pass, $db);
    
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Database connection failed: ' . $conn->connect_error
        ]);
        exit;
    }
    
    // Tables to check
    $tables = [
        'queue_websites',
        'networks',
        'apartment_listings',
        'apartment_listings_price_changes',
        'google_addresses',
        'google_places',
        'network_daily_stats'
    ];
    
    $counts = [];
    
    foreach ($tables as $table) {
        $result = $conn->query("SELECT COUNT(*) as cnt FROM `$table`");
        if ($result) {
            $row = $result->fetch_assoc();
            $counts[$table] = (int)$row['cnt'];
        } else {
            // Table doesn't exist or query failed
            $counts[$table] = null;
        }
    }
    
    $conn->close();
    
    echo json_encode([
        'success' => true,
        'counts' => $counts,
        'timestamp' => date('Y-m-d H:i:s')
    ]);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
?>
