<?php
// Test profile detection for different HTML files

$profilesDir = __DIR__ . DIRECTORY_SEPARATOR . 'Extract Profiles' . DIRECTORY_SEPARATOR . 'Network';
$capturesDir = __DIR__ . DIRECTORY_SEPARATOR . 'Captures' . DIRECTORY_SEPARATOR . '2025-11-10';

// Load profiles
function load_profiles_test($dir) {
    $profiles = [];
    $files = glob($dir . DIRECTORY_SEPARATOR . '*.json');
    foreach ($files as $file) {
        $content = @file_get_contents($file);
        if ($content === false) continue;
        $profile = json_decode($content, true);
        if (json_last_error() === JSON_ERROR_NONE && is_array($profile)) {
            $profileName = $profile['profile_name'] ?? basename($file, '.json');
            $profiles[$profileName] = $profile;
        }
    }
    return $profiles;
}

// Detect profile
function detect_profile_test($html, $url, $profiles) {
    $html_lower = strtolower($html);
    $url_lower = strtolower($url);
    
    $scores = [];
    
    foreach ($profiles as $name => $profile) {
        if (!isset($profile['detection'])) continue;
        
        $score = 0;
        
        // Check domain patterns
        if (!empty($profile['detection']['domain_patterns'])) {
            foreach ($profile['detection']['domain_patterns'] as $pattern) {
                if (stripos($url_lower, strtolower($pattern)) !== false) {
                    $score += 10;
                    echo "  [+10] Domain match: {$pattern}\n";
                }
            }
        }
        
        // Check HTML markers
        if (!empty($profile['detection']['html_markers'])) {
            foreach ($profile['detection']['html_markers'] as $marker) {
                if (stripos($html_lower, strtolower($marker)) !== false) {
                    $score += 5;
                    echo "  [+5] HTML marker: {$marker}\n";
                }
            }
        }
        
        $scores[$name] = $score;
    }
    
    arsort($scores);
    return $scores;
}

// Test files
$testFiles = [
    'networks_1.html' => 'https://cornellandassociates.appfolio.com/listings',
    'networks_2.html' => 'https://incitypropertyholdings.appfolio.com/listings',
    'networks_4.html' => 'https://milestoneproperties.appfolio.com/listings',
    'networks_5.html' => 'https://206pm.com/properties',
    'networks_6.html' => 'https://rentmilestone.com/properties'
];

$profiles = load_profiles_test($profilesDir);
echo "Loaded " . count($profiles) . " profiles: " . implode(', ', array_keys($profiles)) . "\n\n";

foreach ($testFiles as $filename => $url) {
    $filepath = $capturesDir . DIRECTORY_SEPARATOR . $filename;
    if (!file_exists($filepath)) {
        echo "SKIP: {$filename} - file not found\n\n";
        continue;
    }
    
    $html = file_get_contents($filepath);
    $htmlSize = strlen($html);
    
    echo "======================================\n";
    echo "File: {$filename}\n";
    echo "URL: {$url}\n";
    echo "Size: " . number_format($htmlSize) . " bytes\n";
    echo "--------------------------------------\n";
    
    $scores = detect_profile_test($html, $url, $profiles);
    
    echo "\nProfile Scores:\n";
    foreach ($scores as $name => $score) {
        echo "  {$name}: {$score} points\n";
    }
    
    $bestProfile = array_key_first($scores);
    $bestScore = $scores[$bestProfile] ?? 0;
    
    if ($bestScore >= 5) {
        echo "\n✓ Selected profile: {$bestProfile} ({$bestScore} points)\n";
    } else {
        echo "\n✗ No profile matched (using default)\n";
    }
    
    echo "\n\n";
}
