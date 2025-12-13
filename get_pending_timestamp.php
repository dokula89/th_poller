<?php
/**
 * Get the last pending jobs check timestamp from database
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

try {
    $conn = new mysqli('localhost', 'root', '', 'offta');
    
    if ($conn->connect_error) {
        throw new Exception('Database connection failed: ' . $conn->connect_error);
    }
    
    // Get the most recent timestamp
    $query = "SELECT checked_at FROM pending_jobs_log ORDER BY id DESC LIMIT 1";
    $result = $conn->query($query);
    
    if ($result && $result->num_rows > 0) {
        $row = $result->fetch_assoc();
        $last_check = $row['checked_at'];
        
        // Calculate time ago
        $timestamp = strtotime($last_check);
        $now = time();
        $diff_seconds = $now - $timestamp;
        
        if ($diff_seconds < 60) {
            $time_ago = $diff_seconds . ' seconds ago';
        } elseif ($diff_seconds < 3600) {
            $minutes = floor($diff_seconds / 60);
            $time_ago = $minutes . ' minute' . ($minutes != 1 ? 's' : '') . ' ago';
        } elseif ($diff_seconds < 86400) {
            $hours = floor($diff_seconds / 3600);
            $time_ago = $hours . ' hour' . ($hours != 1 ? 's' : '') . ' ago';
        } else {
            $days = floor($diff_seconds / 86400);
            $time_ago = $days . ' day' . ($days != 1 ? 's' : '') . ' ago';
        }
        
        echo json_encode([
            'success' => true,
            'last_check' => $last_check,
            'timestamp' => $timestamp,
            'time_ago' => $time_ago,
            'seconds_ago' => $diff_seconds,
            'formatted' => date('M j, Y g:i:s A', $timestamp)
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error' => 'No timestamp found',
            'message' => 'Pending jobs checker may not have run yet'
        ]);
    }
    
    $conn->close();
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
