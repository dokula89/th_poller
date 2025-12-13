<?php
/**
 * Receive and store pending jobs timestamp from Queue Poller
 * Called every 30 seconds when pending jobs are checked
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

$timestamp = $_POST['timestamp'] ?? '';

if (empty($timestamp)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Timestamp is required']);
    exit;
}

// Validate timestamp format (YYYY-MM-DD HH:MM:SS)
if (!preg_match('/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/', $timestamp)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid timestamp format']);
    exit;
}

// Store timestamp in a file
$timestamp_file = __DIR__ . '/last_pending_check.txt';

try {
    file_put_contents($timestamp_file, $timestamp);
    
    echo json_encode([
        'success' => true,
        'message' => 'Timestamp updated successfully',
        'timestamp' => $timestamp,
        'server_time' => date('Y-m-d H:i:s')
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Failed to write timestamp file',
        'details' => $e->getMessage()
    ]);
}
