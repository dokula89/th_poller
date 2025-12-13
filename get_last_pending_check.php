<?php
/**
 * API endpoint to get the last time pending jobs were checked
 * Returns timestamp in various formats
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$timestamp_file = __DIR__ . '/last_pending_check.txt';

if (!file_exists($timestamp_file)) {
    echo json_encode([
        'success' => false,
        'error' => 'Timestamp file not found',
        'message' => 'Pending jobs checker may not have run yet'
    ]);
    exit;
}

$last_check = trim(file_get_contents($timestamp_file));

if (empty($last_check)) {
    echo json_encode([
        'success' => false,
        'error' => 'Timestamp file is empty'
    ]);
    exit;
}

// Calculate time ago
$timestamp = strtotime($last_check);
$now = time();
$diff_seconds = $now - $timestamp;

$time_ago = '';
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
