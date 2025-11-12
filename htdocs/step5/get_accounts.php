<?php
/**
 * API endpoint to fetch accounts data for the queue poller
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/db_config.php';

try {
    // Open DB connection
    $conn = get_db_connection();
    // Get search term if provided
    $search = isset($_GET['search']) ? trim($_GET['search']) : '';
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 200;
    
    // Build query
    if (!empty($search)) {
        $like = '%' . $search . '%';
        $stmt = $conn->prepare("
            SELECT id, username, first_name, last_name, email, role, registered, last_seen
            FROM accounts
            WHERE username LIKE ? OR email LIKE ? OR first_name LIKE ? OR last_name LIKE ? 
               OR CONCAT(first_name,' ',last_name) LIKE ?
            ORDER BY COALESCE(last_seen, registered) DESC, id DESC
            LIMIT ?
        ");
        $stmt->bind_param('sssssi', $like, $like, $like, $like, $like, $limit);
    } else {
        $stmt = $conn->prepare("
            SELECT id, username, first_name, last_name, email, role, registered, last_seen
            FROM accounts
            ORDER BY COALESCE(last_seen, registered) DESC, id DESC
            LIMIT ?
        ");
        $stmt->bind_param('i', $limit);
    }
    
    $stmt->execute();
    $result = $stmt->get_result();
    
    $accounts = [];
    while ($row = $result->fetch_assoc()) {
        $accounts[] = $row;
    }
    
    $stmt->close();
    
    echo json_encode([
        'ok' => true,
        'accounts' => $accounts,
        'count' => count($accounts),
        'search' => $search
    ]);
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => $e->getMessage()
    ]);
}
?>
