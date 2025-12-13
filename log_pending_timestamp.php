<?php
/**
 * Log pending jobs check timestamp to external database
 * Receives timestamp from Queue Poller and inserts into pending_jobs_log table
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');

// Accept both GET and POST for testing
$timestamp = $_POST['timestamp'] ?? $_GET['timestamp'] ?? '';
$action = $_GET['action'] ?? '';

// If action=update, insert current timestamp and return
if ($action === 'update') {
    $current_timestamp = date('Y-m-d H:i:s');
    
    try {
        $conn = new mysqli('localhost', 'offtanco_local_uzr', 'QK[EtQwMa0N3', 'offtanco_offta');
        
        if ($conn->connect_error) {
            throw new Exception('Database connection failed: ' . $conn->connect_error);
        }
        
        $stmt = $conn->prepare("INSERT INTO pending_jobs_log (checked_at) VALUES (?)");
        $stmt->bind_param('s', $current_timestamp);
        
        if ($stmt->execute()) {
            echo json_encode([
                'success' => true,
                'message' => 'Status updated successfully',
                'timestamp' => $current_timestamp,
                'id' => $conn->insert_id
            ]);
        } else {
            throw new Exception('Failed to insert timestamp: ' . $stmt->error);
        }
        
        $stmt->close();
        $conn->close();
        exit;
        
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $e->getMessage()
        ]);
        exit;
    }
}

// If GET request with no timestamp, show last 5 logs
if ($_SERVER['REQUEST_METHOD'] === 'GET' && empty($timestamp)) {
    try {
        $conn = new mysqli('localhost', 'offtanco_local_uzr', 'QK[EtQwMa0N3', 'offtanco_offta');
        
        if ($conn->connect_error) {
            throw new Exception('Database connection failed: ' . $conn->connect_error);
        }
        
        $result = $conn->query("SELECT * FROM pending_jobs_log ORDER BY id DESC LIMIT 5");
        $logs = [];
        
        while ($row = $result->fetch_assoc()) {
            $logs[] = $row;
        }
        
        echo json_encode([
            'success' => true,
            'message' => 'Last 5 pending jobs check logs',
            'logs' => $logs,
            'count' => count($logs)
        ]);
        
        $conn->close();
        exit;
        
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => $e->getMessage()
        ]);
        exit;
    }
}

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

try {
    // Connect to database
    $conn = new mysqli('localhost', 'offtanco_local_uzr', 'QK[EtQwMa0N3', 'offtanco_offta');
    
    if ($conn->connect_error) {
        throw new Exception('Database connection failed: ' . $conn->connect_error);
    }
    
    // Insert timestamp
    $stmt = $conn->prepare("INSERT INTO pending_jobs_log (checked_at) VALUES (?)");
    $stmt->bind_param('s', $timestamp);
    
    if ($stmt->execute()) {
        echo json_encode([
            'success' => true,
            'message' => 'Timestamp logged successfully',
            'timestamp' => $timestamp,
            'id' => $conn->insert_id
        ]);
    } else {
        throw new Exception('Failed to insert timestamp: ' . $stmt->error);
    }
    
    $stmt->close();
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
