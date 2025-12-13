<?php
/**
 * Get Queue Websites with Stats
 * 
 * Returns queue_websites with network_daily_stats for today's date joined
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Database configuration
$DB_HOST = '172.104.206.182';
$DB_PORT = 3306;
$DB_NAME = 'offta';
$DB_USER = 'seattlelisted_usr';
$DB_PASS = 'Seattlelisted2024!';

try {
    // Connect to database
    $dsn = "mysql:host={$DB_HOST};port={$DB_PORT};dbname={$DB_NAME};charset=utf8mb4";
    $pdo = new PDO($dsn, $DB_USER, $DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false
    ]);
    
    // Get query parameters
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 100;
    $status = isset($_GET['status']) ? $_GET['status'] : null;
    $metro = isset($_GET['metro']) ? $_GET['metro'] : null;
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    // Build query - join queue_websites with network_daily_stats for the selected date
    $sql = "
        SELECT 
            qw.id,
            qw.link,
            qw.the_css,
            qw.capture_mode,
            qw.status,
            qw.priority,
            qw.attempts,
            qw.last_error,
            qw.source_table,
            qw.source_id,
            qw.output_json_path,
            qw.created_at,
            qw.updated_at,
            qw.processed_at,
            qw.run_interval_minutes,
            qw.steps,
            qw.listing_id,
            qw.click_x,
            qw.click_y,
            COALESCE(nds.price_changes, 0) as price_changes,
            COALESCE(nds.apartments_added, 0) as apartments_added,
            COALESCE(nds.apartments_subtracted, 0) as apartments_subtracted,
            COALESCE(nds.total_listings, 0) as total_listings
        FROM queue_websites qw
        LEFT JOIN network_daily_stats nds ON qw.id = nds.network_id AND nds.date = :stat_date
        WHERE qw.source_table = 'networks'
    ";
    
    $params = ['stat_date' => $date];
    
    if ($status && $status !== 'all') {
        $sql .= " AND qw.status = :status";
        $params['status'] = $status;
    }
    
    $sql .= " ORDER BY qw.priority DESC, qw.processed_at DESC LIMIT :limit";
    
    $stmt = $pdo->prepare($sql);
    foreach ($params as $key => $value) {
        $stmt->bindValue(':' . $key, $value);
    }
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    
    $items = $stmt->fetchAll();
    
    echo json_encode([
        'success' => true,
        'count' => count($items),
        'date' => $date,
        'items' => $items
    ]);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Database error: ' . $e->getMessage()
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Error: ' . $e->getMessage()
    ]);
}
