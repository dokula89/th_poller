<?php
/**
 * API endpoint to fetch google_places with non-empty Website
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/db_config.php';

try {
    $conn = get_db_connection();

    // Optional limit
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 0; // 0 = no limit

    // Build SQL
    $sql = "SELECT id, Name, Website FROM google_places WHERE Website IS NOT NULL AND Website <> '' ORDER BY id DESC";
    if ($limit > 0) {
        $sql .= " LIMIT ?";
    }

    if ($limit > 0) {
        $stmt = $conn->prepare($sql);
        $stmt->bind_param('i', $limit);
    } else {
        $stmt = $conn->prepare($sql);
    }

    $stmt->execute();
    $result = $stmt->get_result();

    $websites = [];
    while ($row = $result->fetch_assoc()) {
        $websites[] = $row;
    }

    $stmt->close();
    $conn->close();

    echo json_encode([
        'ok' => true,
        'websites' => $websites,
        'count' => count($websites)
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => $e->getMessage()
    ]);
}
?>
