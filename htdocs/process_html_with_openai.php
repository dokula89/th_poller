<?php
declare(strict_types=1);

// Browser-only UI: select an HTML file from Captures, process with OpenAI, save JSON to disk, and auto-download it.

if (PHP_SAPI === 'cli') {
    http_response_code(400);
    echo "This tool is browser-only. Open http://localhost/" . basename(__FILE__) . " in your browser.\n";
    exit(1);
}

// Allow longer processing for large HTML or slow network calls
@set_time_limit(600);

// ---------- Configuration ----------
$capturesBase = getenv('CAPTURES_DIR') ?: 'C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Captures';
$capturesBaseReal = realpath($capturesBase) ?: $capturesBase;
$localImagesDir = $capturesBase . DIRECTORY_SEPARATOR . 'images'; // Local images directory
$profilesDir = getenv('PROFILES_DIR') ?: 'C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Extract Profiles\\Network';
$profilesDirReal = realpath($profilesDir) ?: $profilesDir;

// Optional: server upload configuration
$uploadEndpoint   = getenv('UPLOAD_ENDPOINT') ?: '';
$uploadAuthToken  = getenv('UPLOAD_AUTH_TOKEN') ?: '';

// Optional: SFTP upload to remote folder (preferred)
$remoteJsonDir = getenv('REMOTE_JSON_DIR') ?: '/home/daniel/api/trustyhousing.com/manual_upload/json_uploads';
// Optional: remote directory for images and (optional) public base URL
$remoteImageDir = getenv('REMOTE_IMAGE_DIR') ?: '/home/daniel/api/trustyhousing.com/manual_upload/images';
$imageBaseUrl   = getenv('IMAGE_BASE_URL') ?: '';
// Limits for image handling to avoid long runs
$imageUploadLimit = (int)(getenv('IMAGE_UPLOAD_LIMIT') ?: '0'); // max images to upload per run (0 = unlimited)
$imageTimeBudget  = (int)(getenv('IMAGE_TIME_BUDGET') ?: '0'); // seconds budget for image uploads (0 = unlimited)
// Disable image uploads (handled by Python per user request)
$enableImageUpload = false;

// Simple job/progress tracking
$jobsDir = __DIR__ . DIRECTORY_SEPARATOR . 'job_status';
if (!is_dir($jobsDir)) { @mkdir($jobsDir, 0777, true); }
// Defaults aligned with th_poller/config_utils.py so it "just works" without env vars
$sftpHost = getenv('SFTP_HOST') ?: '172.104.206.182';
$sftpPort = (int)(getenv('SFTP_PORT') ?: '23655');
$sftpUser = getenv('SFTP_USER') ?: 'daniel';
$sftpPass = getenv('SFTP_PASS') ?: 'Driver89*';

// API key: environment or openai_key.txt next to this script
$api_key = getenv('OPENAI_API_KEY');
if (!$api_key) {
    $key_file = __DIR__ . DIRECTORY_SEPARATOR . 'openai_key.txt';
    if (is_file($key_file)) {
        $api_key = trim((string)file_get_contents($key_file));
    }
}

// ---------- Helpers ----------
function h(?string $s): string { return htmlspecialchars((string)$s ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function fmtTime(int $ts): string { return date('Y-m-d H:i:s', $ts); }

/**
 * Upload a JSON file to a remote server via multipart/form-data
 */
function uploadFileToServer(string $filePath, string $endpoint, string $token = ''): array {
  if ($endpoint === '' || !is_file($filePath)) {
    return ['success' => false, 'status' => 0, 'error' => 'Missing endpoint or file not found'];
  }
  $ch = curl_init($endpoint);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $headers = [];
  if ($token !== '') {
    $headers[] = 'Authorization: Bearer ' . $token;
  }
  if ($headers) curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
  $postFields = [
    'file' => new CURLFile($filePath, 'application/json', basename($filePath)),
    'filename' => basename($filePath),
    'source' => 'process_html_with_openai.php'
  ];
  curl_setopt($ch, CURLOPT_POST, true);
  curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
  $response = curl_exec($ch);
  $curlErrNo = curl_errno($ch);
  $curlErr   = $curlErrNo ? curl_error($ch) : '';
  $httpCode  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);
  if ($curlErrNo) {
    return ['success' => false, 'status' => $httpCode, 'error' => $curlErr, 'body' => (string)$response];
  }
  return ['success' => ($httpCode >= 200 && $httpCode < 300), 'status' => $httpCode, 'body' => (string)$response];
}

/**
 * Upload an image file to a remote server via multipart/form-data
 */
function uploadImageToServer(string $filePath, string $endpoint, string $token = ''): array {
  if ($endpoint === '' || !is_file($filePath)) {
    return ['success' => false, 'status' => 0, 'error' => 'Missing endpoint or file not found'];
  }
  
  // Detect mime type
  $mimeType = 'image/jpeg';
  $ext = strtolower(pathinfo($filePath, PATHINFO_EXTENSION));
  $mimeMap = [
    'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg',
    'png' => 'image/png', 'gif' => 'image/gif', 'webp' => 'image/webp'
  ];
  if (isset($mimeMap[$ext])) {
    $mimeType = $mimeMap[$ext];
  }
  
  $ch = curl_init($endpoint);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $headers = [];
  if ($token !== '') {
    $headers[] = 'Authorization: Bearer ' . $token;
  }
  if ($headers) curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
  $postFields = [
    'file' => new CURLFile($filePath, $mimeType, basename($filePath)),
    'filename' => basename($filePath),
    'source' => 'process_html_with_openai.php',
    'type' => 'image'
  ];
  curl_setopt($ch, CURLOPT_POST, true);
  curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
  $response = curl_exec($ch);
  $curlErrNo = curl_errno($ch);
  $curlErr   = $curlErrNo ? curl_error($ch) : '';
  $httpCode  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);
  if ($curlErrNo) {
    return ['success' => false, 'status' => $httpCode, 'error' => $curlErr, 'body' => (string)$response];
  }
  return ['success' => ($httpCode >= 200 && $httpCode < 300), 'status' => $httpCode, 'body' => (string)$response];
}

/**
 * Upload a file via SFTP using cURL to a specific remote directory and name.
 * Returns array: ['success'=>bool,'status'=>int,'error'=>string,'body'=>string]
 */
function uploadFileViaSftpCurl(string $filePath, string $remoteDir, string $remoteName, string $host, int $port, string $user, string $pass): array {
  if (!is_file($filePath)) {
    return ['success' => false, 'status' => 0, 'error' => 'Local file not found'];
  }
  if ($host === '' || $user === '' || $pass === '' || $remoteDir === '' || $remoteName === '') {
    return ['success' => false, 'status' => 0, 'error' => 'Missing SFTP configuration'];
  }
  $size = filesize($filePath);
  $fh = fopen($filePath, 'rb');
  if ($fh === false) {
    return ['success' => false, 'status' => 0, 'error' => 'Failed to open local file'];
  }
  $remoteDir = rtrim($remoteDir, '/');
  $url = "sftp://{$host}:{$port}{$remoteDir}/{$remoteName}";
  $ch = curl_init($url);
  curl_setopt($ch, CURLOPT_PROTOCOLS, CURLPROTO_SFTP);
  curl_setopt($ch, CURLOPT_USERPWD, $user . ':' . $pass);
  curl_setopt($ch, CURLOPT_UPLOAD, true);
  curl_setopt($ch, CURLOPT_INFILE, $fh);
  curl_setopt($ch, CURLOPT_INFILESIZE, $size);
  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  $response = curl_exec($ch);
  $curlErrNo = curl_errno($ch);
  $curlErr   = $curlErrNo ? curl_error($ch) : '';
  $httpCode  = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
  curl_close($ch);
  fclose($fh);
  if ($curlErrNo) {
    return ['success' => false, 'status' => $httpCode, 'error' => $curlErr, 'body' => (string)$response];
  }
  // Some SFTP servers may not set a traditional HTTP-like response code; treat lack of error as success.
  return ['success' => true, 'status' => $httpCode ?: 226, 'body' => (string)$response];
}

/**
 * Download an image to a temporary local file using HTTP(S).
 * Returns array: ['success'=>bool,'path'=>string,'ext'=>string,'error'=>string]
 */
function downloadImageToTemp(string $url, int $timeoutSec = 20): array {
  if (!filter_var($url, FILTER_VALIDATE_URL)) {
    return ['success' => false, 'error' => 'Invalid URL'];
  }
  $ch = curl_init($url);
  $tmp = tempnam(sys_get_temp_dir(), 'img_');
  if ($tmp === false) {
    return ['success' => false, 'error' => 'Failed to create temp file'];
  }
  $fh = fopen($tmp, 'wb');
  if ($fh === false) {
    @unlink($tmp);
    return ['success' => false, 'error' => 'Failed to open temp file'];
  }
  curl_setopt_array($ch, [
    CURLOPT_FILE => $fh,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_MAXREDIRS => 5,
    CURLOPT_SSL_VERIFYPEER => false,
    CURLOPT_CONNECTTIMEOUT => $timeoutSec,
    CURLOPT_TIMEOUT => $timeoutSec,
    CURLOPT_USERAGENT => 'Mozilla/5.0 (compatible; ListingsBot/1.0)'
  ]);
  $ok = curl_exec($ch);
  $errNo = curl_errno($ch);
  $err   = $errNo ? curl_error($ch) : '';
  $ctype = (string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
  curl_close($ch);
  fclose($fh);
  if (!$ok || $errNo) {
    @unlink($tmp);
    return ['success' => false, 'error' => $err ?: 'Download failed'];
  }
  // Guess extension from content-type or URL
  $ext = '';
  if (preg_match('/image\/(jpeg|jpg|png|gif|webp)/i', $ctype, $m)) {
    $map = ['jpeg' => 'jpg', 'jpg' => 'jpg', 'png' => 'png', 'gif' => 'gif', 'webp' => 'webp'];
    $ext = $map[strtolower($m[1])] ?? '';
  }
  if ($ext === '') {
    $path = parse_url($url, PHP_URL_PATH);
    if (is_string($path)) {
      $bn = strtolower((string)pathinfo($path, PATHINFO_EXTENSION));
      if (in_array($bn, ['jpg','jpeg','png','gif','webp'], true)) $ext = $bn === 'jpeg' ? 'jpg' : $bn;
    }
  }
  if ($ext === '') $ext = 'jpg';
  return ['success' => true, 'path' => $tmp, 'ext' => $ext];
}

/**
 * Save downloaded image to local Captures/images directory.
 * Returns ['success'=>bool, 'path'=>string, 'error'=>string]
 */
function saveImageLocally(string $tempPath, string $filename, string $localDir): array {
  if (!is_file($tempPath)) {
    return ['success' => false, 'error' => 'Temp file not found'];
  }
  if (!is_dir($localDir)) {
    if (!@mkdir($localDir, 0777, true)) {
      return ['success' => false, 'error' => 'Failed to create local directory'];
    }
  }
  $destPath = $localDir . DIRECTORY_SEPARATOR . $filename;
  if (!@copy($tempPath, $destPath)) {
    return ['success' => false, 'error' => 'Failed to copy image to local directory'];
  }
  return ['success' => true, 'path' => $destPath];
}

/**
 * Download and save images for listings locally to Captures/images directory.
 * Optionally upload to SFTP and HTTP server if credentials/endpoints provided.
 * Returns ['listings'=>array,'stats'=>['attempted'=>int,'saved'=>int,'uploaded_sftp'=>int,'uploaded_http'=>int],'log'=>array]
 */
function uploadListingImages(array $listings, string $remoteImageDir, string $host, int $port, string $user, string $pass, string $imageBaseUrl = '', int $maxUploads = 25, int $timeBudgetSec = 120, string $localImagesDir = '', string $httpEndpoint = '', string $httpToken = ''): array {
  file_put_contents('C:\\xampp\\htdocs\\debug_images.txt', sprintf(
    "uploadListingImages called:\n- Listings: %d\n- Local dir: %s\n- Max uploads: %d\n- Time budget: %d\n- HTTP endpoint: %s\n",
    count($listings), $localImagesDir, $maxUploads, $timeBudgetSec, $httpEndpoint
  ), FILE_APPEND);
  
  $attempted = 0; $saved = 0; $uploadedSftp = 0; $uploadedHttp = 0; $stoppedReason = '';
  $log = [];
  $remoteImageDir = rtrim($remoteImageDir, '/');
  $sftpEnabled = ($remoteImageDir !== '' && $host !== '' && $user !== '' && $pass !== '');
  $httpEnabled = ($httpEndpoint !== '');
  
  // Log folder info
  if ($localImagesDir !== '') {
    $log[] = "Local images folder: {$localImagesDir}";
  }
  if ($sftpEnabled) {
    $log[] = "SFTP upload enabled: {$host}:{$port}{$remoteImageDir}";
  }
  if ($httpEnabled) {
    $log[] = "HTTP upload enabled: {$httpEndpoint}";
  }
  
  $start = microtime(true);
  foreach ($listings as $idx => $listing) {
    if ($maxUploads > 0 && $attempted >= $maxUploads) { $stoppedReason = 'limit'; break; }
    if ($timeBudgetSec > 0 && (microtime(true) - $start) >= $timeBudgetSec) { $stoppedReason = 'time'; break; }
    $url = $listing['img_urls'] ?? '';
    if (!is_string($url) || $url === '') continue;
    
    // Support multiple images: if img_urls is comma/space separated, split them
    $imageUrls = preg_split('/[\s,]+/', trim($url), -1, PREG_SPLIT_NO_EMPTY);
    if (empty($imageUrls)) continue;
    
    $networkId = $listing['network_id'] ?? '1';
    $resultNumber = $listing['result_number'] ?? ($idx + 1);
    
    foreach ($imageUrls as $imageIndex => $imgUrl) {
      if ($maxUploads > 0 && $attempted >= $maxUploads) { $stoppedReason = 'limit'; break 2; }
      if ($timeBudgetSec > 0 && (microtime(true) - $start) >= $timeBudgetSec) { $stoppedReason = 'time'; break 2; }
      
      $attempted++;
      
      // Determine extension
      $ext = 'png';
      $path = parse_url($imgUrl, PHP_URL_PATH);
      if ($path) {
        $urlExt = pathinfo($path, PATHINFO_EXTENSION);
        if ($urlExt && in_array(strtolower($urlExt), ['jpg','jpeg','png','gif','webp'])) {
          $ext = strtolower($urlExt);
        }
      }
      
      // Build filename: network_{network_id}_{result_number}.{ext} OR network_{network_id}_{result_number}_{image_index}.{ext}
      if (count($imageUrls) > 1) {
        $filename = sprintf('network_%s_%03d_%d.%s', $networkId, $resultNumber, $imageIndex + 1, $ext);
      } else {
        $filename = sprintf('network_%s_%03d.%s', $networkId, $resultNumber, $ext);
      }
      
      // Download image
      $dl = downloadImageToTemp($imgUrl);
      if (!$dl['success']) {
        $listings[$idx]['img_download_error'] = $dl['error'] ?? 'download-failed';
        $log[] = "Failed to download image for result {$resultNumber}: " . ($dl['error'] ?? 'unknown error');
        continue;
      }
      
      // Save locally to Captures/images
      $localPath = null;
      if ($localImagesDir !== '') {
        $localSave = saveImageLocally($dl['path'], $filename, $localImagesDir);
        if ($localSave['success']) {
          $saved++;
          $localPath = $localSave['path'];
          $log[] = "Saved locally: {$filename} → {$localImagesDir}";
          // Store local path relative to Captures dir
          $relativePath = 'images' . DIRECTORY_SEPARATOR . $filename;
          if (count($imageUrls) > 1) {
            if (!isset($listings[$idx]['image_local_paths'])) {
              $listings[$idx]['image_local_paths'] = [];
            }
            $listings[$idx]['image_local_paths'][] = $relativePath;
          } else {
            $listings[$idx]['image_url'] = $relativePath; // Local relative path
            $listings[$idx]['image_local_path'] = $localPath; // Absolute path
          }
        } else {
          $log[] = "Failed to save locally: {$filename} - " . ($localSave['error'] ?? 'unknown error');
        }
      }
      
      // Optionally upload to SFTP
      if ($sftpEnabled && $localPath) {
        $up = uploadFileViaSftpCurl($localPath, $remoteImageDir, $filename, $host, $port, $user, $pass);
        if ($up['success']) {
          $uploadedSftp++;
          $remotePath = $remoteImageDir . '/' . $filename;
          $log[] = "Uploaded to SFTP: {$filename} → {$remotePath}";
          
          // Store as array if multiple images
          if (count($imageUrls) > 1) {
            if (!isset($listings[$idx]['image_remote_paths'])) {
              $listings[$idx]['image_remote_paths'] = [];
            }
            $listings[$idx]['image_remote_paths'][] = $remotePath;
            
            if ($imageBaseUrl !== '') {
              if (!isset($listings[$idx]['image_urls_array'])) {
                $listings[$idx]['image_urls_array'] = [];
              }
              $listings[$idx]['image_urls_array'][] = rtrim($imageBaseUrl, '/') . '/' . $filename;
            }
          } else {
            $listings[$idx]['image_remote_path'] = $remotePath;
            if ($imageBaseUrl !== '') {
              $listings[$idx]['image_url_remote'] = rtrim($imageBaseUrl, '/') . '/' . $filename;
            }
          }
          $listings[$idx]['img_uploaded_sftp'] = true;
        } else {
          $log[] = "Failed SFTP upload: {$filename} - " . ($up['error'] ?? 'unknown error');
          $listings[$idx]['img_uploaded_sftp'] = false;
          if (!empty($up['error'])) $listings[$idx]['img_upload_error_sftp'] = $up['error'];
        }
      }
      
      // Optionally upload to HTTP server
      if ($httpEnabled && $localPath) {
        $httpUp = uploadImageToServer($localPath, $httpEndpoint, $httpToken);
        if ($httpUp['success']) {
          $uploadedHttp++;
          $log[] = "Uploaded to HTTP server: {$filename} (status {$httpUp['status']})";
          $listings[$idx]['img_uploaded_http'] = true;
          if (!empty($httpUp['body'])) {
            $listings[$idx]['img_upload_response_http'] = $httpUp['body'];
          }
        } else {
          $log[] = "Failed HTTP upload: {$filename} - " . ($httpUp['error'] ?? "HTTP {$httpUp['status']}");
          $listings[$idx]['img_uploaded_http'] = false;
          if (!empty($httpUp['error'])) $listings[$idx]['img_upload_error_http'] = $httpUp['error'];
        }
      }
      
      // Clean up temp file
      @unlink($dl['path']);
    }
  }
  
  // Final summary log
  $log[] = "Summary: {$attempted} attempted, {$saved} saved locally, {$uploadedSftp} uploaded to SFTP, {$uploadedHttp} uploaded to HTTP";
  
  $stats = [
    'attempted' => $attempted, 
    'saved' => $saved, 
    'uploaded_sftp' => $uploadedSftp,
    'uploaded_http' => $uploadedHttp
  ];
  if ($stoppedReason) { 
    $stats['stopped_reason'] = $stoppedReason; 
    $stats['limit'] = $maxUploads; 
    $stats['time_budget'] = $timeBudgetSec; 
    $log[] = "Stopped early: {$stoppedReason}";
  }
  return ['listings' => $listings, 'stats' => $stats, 'log' => $log];
}

function listHtmlFiles(string $baseDir): array {
    $out = [];
    if (!is_dir($baseDir)) return $out;
    
    // Look only in date-based folders (YYYY-MM-DD format) with Networks and Websites subfolders
    $dateFolders = glob($baseDir . DIRECTORY_SEPARATOR . '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]', GLOB_ONLYDIR);
    
    foreach ($dateFolders as $dateFolder) {
        // Check both Networks and Websites subfolders
        foreach (['Networks', 'Websites'] as $subfolder) {
            $subfolderPath = $dateFolder . DIRECTORY_SEPARATOR . $subfolder;
            if (is_dir($subfolderPath)) {
                $htmlFiles = glob($subfolderPath . DIRECTORY_SEPARATOR . '*.html');
                foreach ($htmlFiles as $file) {
                    if (is_file($file)) {
                        $out[] = ['path' => $file, 'mtime' => filemtime($file)];
                    }
                }
            }
        }
    }
    
    usort($out, fn($a, $b) => $b['mtime'] <=> $a['mtime']); // newest first
    return $out;
}

/**
 * Helper: check if a table has a specific column.
 */
function db_has_column(mysqli $mysqli, string $table, string $column): bool {
  try {
    $tableEsc = preg_replace('/[^A-Za-z0-9_]/', '', $table);
    $colEsc = preg_replace('/[^A-Za-z0-9_]/', '', $column);
    $sql = "SHOW COLUMNS FROM `{$tableEsc}` LIKE '{$colEsc}'";
    if ($res = $mysqli->query($sql)) {
      $ok = (bool)$res->num_rows;
      $res->free();
      return $ok;
    }
  } catch (Throwable $e) {
    // ignore
  }
  return false;
}

function relLabel(string $fullPath, string $baseReal): string {
    $fullReal = realpath($fullPath) ?: $fullPath;
    $baseReal = realpath($baseReal) ?: $baseReal;
    if ($baseReal !== '' && stripos($fullReal, $baseReal) === 0) {
        $rel = ltrim(substr($fullReal, strlen($baseReal)), "\\/");
        return $rel !== '' ? $rel : basename($fullReal);
    }
    return basename($fullReal);
}

function validateInsideBase(string $selected, string $baseReal): ?string {
    $real = realpath($selected);
    $base = realpath($baseReal) ?: $baseReal;
    if (!$real || !$base) return null;
    return (stripos($real, $base) === 0) ? $real : null;
}

/**
 * Build a simple directory listing string for logging.
 */
function collectFolderListing(string $baseDir, int $maxLines = 400, int $maxDepth = 3): string {
  $baseReal = realpath($baseDir) ?: $baseDir;
  if (!is_dir($baseReal)) return "[Not a directory: $baseReal]";
  $lines = [];
  $it = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($baseReal, FilesystemIterator::SKIP_DOTS),
    RecursiveIteratorIterator::SELF_FIRST
  );
  foreach ($it as $fi) {
    if ($it->getDepth() > $maxDepth) { continue; }
    $full = $fi->getPathname();
    $rel = ltrim(substr($full, strlen($baseReal)), '\\/');
    $prefix = $fi->isDir() ? 'DIR ' : 'FILE';
    $lines[] = $prefix . ': ' . ($rel === '' ? basename($full) : $rel);
    if (count($lines) >= $maxLines) { $lines[] = '... (truncated)'; break; }
  }
  return implode("\n", $lines);
}

// ---------- Progress helpers ----------
function job_path(string $jobsDir, string $jobId): string {
  $safe = preg_replace('/[^A-Za-z0-9_-]/', '', $jobId);
  return rtrim($jobsDir, '\\/') . DIRECTORY_SEPARATOR . $safe . '.json';
}

function job_init(string $jobsDir, string $jobId, array $extra = []): void {
  $path = job_path($jobsDir, $jobId);
  $data = array_merge([
    'status' => 'running',
    'percent' => 0,
    'message' => 'Starting',
    'log' => [],
    'result' => null,
    'started_at' => time(),
    'updated' => time(),
  ], $extra);
  @file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
}

function job_update(string $jobsDir, string $jobId, array $changes = [], ?string $appendLog = null): void {
  $path = job_path($jobsDir, $jobId);
  $data = [];
  if (is_file($path)) {
    $data = json_decode((string)file_get_contents($path), true) ?: [];
  }
  foreach ($changes as $k => $v) { $data[$k] = $v; }
  if (!isset($data['log']) || !is_array($data['log'])) $data['log'] = [];
  if ($appendLog !== null) {
    $logText = $appendLog;
    if (strpos($logText, '[PHP]') !== 0) { $logText = '[PHP] ' . $logText; }
    $data['log'][] = '[' . date('H:i:s') . '] ' . $logText;
  }
  $data['updated'] = time();
  @file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
}

function job_read(string $jobsDir, string $jobId): array {
  $path = job_path($jobsDir, $jobId);
  if (!is_file($path)) return ['status' => 'unknown'];
  $data = json_decode((string)file_get_contents($path), true);
  return is_array($data) ? $data : ['status' => 'unknown'];
}

function job_is_paused(string $jobsDir, string $jobId): bool {
  $s = job_read($jobsDir, $jobId);
  return ($s['status'] ?? '') === 'paused';
}

function job_wait_if_paused(string $jobsDir, string $jobId, int $sleepMs = 500): void {
  // Busy-wait loop checking pause status; returns when not paused
  $i = 0;
  while (job_is_paused($jobsDir, $jobId)) {
    usleep($sleepMs * 1000);
    // Every ~5 seconds add a heartbeat to the log to show we're waiting
    $i += $sleepMs;
    if ($i >= 5000) {
      $i = 0;
      job_update($jobsDir, $jobId, ['message' => 'Paused'], 'Paused… waiting to resume');
    }
  }
}

/**
 * Load all extraction profiles from the profiles directory.
 * Returns array of profile objects indexed by profile name.
 */
function load_profiles(string $profilesDir): array {
  $profiles = [];
  if (!is_dir($profilesDir)) {
    return $profiles;
  }
  $files = glob($profilesDir . DIRECTORY_SEPARATOR . '*.json');
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

/**
 * Detect which profile to use based on HTML content and URL.
 * Returns profile array or null if no match (will use default).
 */
function detect_profile(string $html, string $url, array $profiles): ?array {
  $html_lower = strtolower($html);
  $url_lower = strtolower($url);
  
  $bestMatch = null;
  $bestScore = 0;
  
  foreach ($profiles as $profile) {
    if (!isset($profile['detection'])) continue;
    
    $score = 0;
    
    // Check domain patterns
    if (!empty($profile['detection']['domain_patterns'])) {
      foreach ($profile['detection']['domain_patterns'] as $pattern) {
        if (stripos($url_lower, strtolower($pattern)) !== false) {
          $score += 10;
        }
      }
    }
    
    // Check HTML markers
    if (!empty($profile['detection']['html_markers'])) {
      foreach ($profile['detection']['html_markers'] as $marker) {
        if (stripos($html_lower, strtolower($marker)) !== false) {
          $score += 5;
        }
      }
    }
    
    if ($score > $bestScore) {
      $bestScore = $score;
      $bestMatch = $profile;
    }
  }
  
  // Return profile if it has a reasonable match score
  return ($bestScore >= 5) ? $bestMatch : null;
}

/**
 * Preprocess HTML based on profile extraction rules.
 * Extracts the relevant container and strips irrelevant elements.
 */
function preprocess_html_with_profile(string $html, ?array $profile): string {
  // CRITICAL: Remove all <form> elements first - they contain filter dropdowns with fake data
  $html = preg_replace('/<form\b[^>]*>.*?<\/form>/si', '', $html);
  
  // Remove <select> elements that might be outside forms
  $html = preg_replace('/<select\b[^>]*>.*?<\/select>/si', '', $html);
  
  // Remove navigation, header, footer
  $html = preg_replace('/<nav\b[^>]*>.*?<\/nav>/si', '', $html);
  $html = preg_replace('/<header\b[^>]*>.*?<\/header>/si', '', $html);
  $html = preg_replace('/<footer\b[^>]*>.*?<\/footer>/si', '', $html);
  
  if ($profile === null || empty($profile['extraction']['container_selector'])) {
    // Default preprocessing
    if (preg_match('/<div[^>]*id=["\']result_container["\'][^>]*>(.*?)<\/div\s*>\s*(?:<\/div>)?\s*(?:<div[^>]*class=\"[^\"]*pagination|<\/body>)/si', $html, $matches)) {
      return $matches[1];
    } elseif (preg_match('/<div[^>]*class=\"[^\"]*js-listings-container[^\"]*\"[^>]*>(.*?)(?:<div[^>]*class=\"[^\"]*pagination|<\/body>)/si', $html, $matches)) {
      return $matches[1];
    }
    return $html;
  }
  
  // Try to extract container based on profile selectors
  $containerSelector = $profile['extraction']['container_selector'];
  $selectors = array_map('trim', explode(',', $containerSelector));
  
  foreach ($selectors as $selector) {
    // Simple extraction for id-based selectors
    if (preg_match('/^div\[id=[\'"]([^\'\"]+)[\'"]\]$/', $selector, $m)) {
      $id = $m[1];
      if (preg_match('/<div[^>]*id=["\']' . preg_quote($id, '/') . '["\'][^>]*>(.*?)<\/div/si', $html, $matches)) {
        return $matches[1];
      }
    }
    // Simple extraction for class-based selectors
    if (preg_match('/^div\.([a-z0-9_-]+)$/i', $selector, $m)) {
      $class = $m[1];
      if (preg_match('/<div[^>]*class=\"[^\"]*' . preg_quote($class, '/') . '[^\"]*\"[^>]*>(.*?)(?:<div[^>]*class=\"[^\"]*pagination|<\/body>)/si', $html, $matches)) {
        return $matches[1];
      }
    }
  }
  
  return $html;
}

/**
 * Build OpenAI prompt using profile template.
 */
function build_prompt_with_profile(string $html, ?array $profile): string {
  $template = $profile['openai_prompt_template'] ?? 
    "Extract all apartment listings from this HTML page.\n\nHTML Content:\n{html}\n\nReturn a JSON array of listing objects with these fields (use null if not found):\n- listing_website\n- title\n- bedrooms\n- bathrooms\n- sqft\n- price\n- img_urls (array)\n- full_address\n- street\n- city\n- state\n- description\n- available_date\n- phone_contact\n- email_contact\n- apply_now_link\n\nReturn ONLY the JSON array, no other text.";
  
  return str_replace('{html}', $html, $template);
}

// ---------- Build file list and selection ----------
$files = is_dir($capturesBaseReal) ? listHtmlFiles($capturesBaseReal) : [];
$latest = $files[0]['path'] ?? '';

$selectedRaw = isset($_GET['file']) ? (string)$_GET['file'] : '';
if ($selectedRaw && preg_match('/^[A-Za-z]:\//', $selectedRaw)) { // normalize C:/ -> C:\
    $selectedRaw = str_replace('/', '\\', $selectedRaw);
}
$selected = $selectedRaw ? (validateInsideBase($selectedRaw, $capturesBaseReal) ?: '') : '';
if ($selected === '' && $latest) $selected = $latest;

// Model selection
$availableModels = [
    'gpt-4o-mini' => [
        'name' => 'GPT-4o Mini',
        'context' => '128k tokens',
        'input_price' => '$0.150 / 1M tokens',
        'output_price' => '$0.600 / 1M tokens',
        'max_chars' => 280000,  // ~70k tokens input, leaves 16k completion + plenty of buffer
        'max_tokens' => 16000   // Max allowed for gpt-4o-mini
    ],
    'gpt-4o' => [
        'name' => 'GPT-4o',
        'context' => '128k tokens',
        'input_price' => '$2.50 / 1M tokens',
        'output_price' => '$10.00 / 1M tokens',
        'max_chars' => 280000,
        'max_tokens' => 16000
    ],
    'gpt-3.5-turbo' => [
        'name' => 'GPT-3.5 Turbo',
        'context' => '16k tokens',
        'input_price' => '$0.50 / 1M tokens',
        'output_price' => '$1.50 / 1M tokens',
        'max_chars' => 40000,
        'max_tokens' => 3000
    ]
];
$selectedModel = isset($_GET['model']) && isset($availableModels[$_GET['model']]) 
    ? (string)$_GET['model'] 
    : 'gpt-4o-mini';
$modelConfig = $availableModels[$selectedModel];

// Parsing method selection
$parseMethod = isset($_GET['method']) ? (string)$_GET['method'] : 'local';

$shouldProcess = isset($_GET['process']) && $selected !== '' && is_file($selected);

// Headless shortcut: if process=1 and headless=1, run the processing now and return JSON (no HTML/JS)
if ($shouldProcess && isset($_GET['headless']) && (string)$_GET['headless'] === '1') {
  // Generate job and set up params
  $job = bin2hex(random_bytes(8));
  job_init($jobsDir, $job, ['message' => 'Starting (headless)']);
  $method = $parseMethod ?: 'local';
  $model  = isset($availableModels[$selectedModel]) ? $selectedModel : 'gpt-4o-mini';
  $fileReal = validateInsideBase($selected, $capturesBaseReal) ?: '';

  job_update($jobsDir, $job, ['status' => 'running', 'percent' => 3, 'message' => 'Validating inputs'], 'Validating inputs');
  job_wait_if_paused($jobsDir, $job);
  if ($fileReal === '' || !is_file($fileReal)) {
    job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'Selected file not found'], 'Selected file not found');
    header('Content-Type: application/json'); echo json_encode(['ok' => false, 'job' => $job, 'status' => job_read($jobsDir, $job)]); exit;
  }

  $listings = []; $savePath = ''; $sftpResult = null; $uploadResult = null; $htmlUploadResult = null;
  try {
    if ($method === 'local') {
      job_update($jobsDir, $job, ['percent' => 8, 'message' => 'Parsing locally'], 'Parsing locally');
      job_wait_if_paused($jobsDir, $job);
      $listings = parseListingsLocally($fileReal);
      job_update($jobsDir, $job, ['percent' => 25, 'message' => 'Parsed ' . count($listings) . ' listings'], 'Parsed ' . count($listings) . ' listings');
      job_wait_if_paused($jobsDir, $job);
      $modelContent = json_encode($listings, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
      // Save JSON in the same directory as the HTML file (preserves Networks/Websites subfolder)
      $saveDir = dirname($fileReal);
      if ($saveDir === '' || !is_dir($saveDir)) { 
        $saveDir = __DIR__ . DIRECTORY_SEPARATOR . 'downloads'; 
      }
      if (!is_dir($saveDir)) { @mkdir($saveDir, 0777, true); }
      $baseHtml = basename($fileReal);
      $jsonName = preg_replace('/\.html?$/i', '.json', $baseHtml);
      if ($jsonName === $baseHtml) { $jsonName .= '.json'; }
      $savePath = rtrim($saveDir, "\\/") . DIRECTORY_SEPARATOR . $jsonName;
      @file_put_contents($savePath, $modelContent);
    } else {
      job_update($jobsDir, $job, ['percent' => 8, 'message' => 'Calling OpenAI'], 'Calling OpenAI');
      job_wait_if_paused($jobsDir, $job);
      if (!$api_key) {
        job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'OPENAI_API_KEY not set'], 'OPENAI_API_KEY not set');
        header('Content-Type: application/json'); echo json_encode(['ok' => false, 'job' => $job, 'status' => job_read($jobsDir, $job)]); exit;
      }
      $html_content = (string)file_get_contents($fileReal);
      if (preg_match('/<div[^>]*id=["\']result_container["\'][^>]*>(.*?)<\/div\s*>\s*(?:<\/div>)?\s*(?:<div[^>]*class=\"[^\"]*pagination|<\/body>)/si', $html_content, $matches)) {
        $html_content = $matches[1];
      } elseif (preg_match('/<div[^>]*class=\"[^\"]*js-listings-container[^\"]*\"[^>]*>(.*?)(?:<div[^>]*class=\"[^\"]*pagination|<\/body>)/si', $html_content, $matches)) {
        $html_content = $matches[1];
      }
      $html_content = preg_replace('/\s+style=\"[^\"]*\"/', '', $html_content);
      $html_content = preg_replace('/\s+data-[a-z-]+=\"[^\"]*\"/', '', $html_content);
      $html_content = preg_replace('/\s+aria-[a-z-]+=\"[^\"]*\"/', '', $html_content);
      $html_content = preg_replace('/\s+role=\"[^\"]*\"/', '', $html_content);
      $html_content = preg_replace('/\s+tabindex=\"[^\"]*\"/', '', $html_content);
      $html_content = preg_replace('/<!--.*?-->/s', '', $html_content);
      $html_content = preg_replace('/\s{2,}/', ' ', $html_content);
      $html_content = preg_replace('/>\s+</', '><', $html_content);
      $maxChars = $availableModels[$model]['max_chars'];
      $maxTokens = $availableModels[$model]['max_tokens'];
      $originalLength = strlen($html_content);
      if ($originalLength > $maxChars) {
        $html_content = substr($html_content, 0, $maxChars) . "\n\n[TRUNCATED: Showing first {$maxChars} of {$originalLength} chars. Extract all visible listings.]";
      }
      $prompt = "Extract all apartment listings from this HTML page.\n\nHTML Content:\n" . $html_content . "\n\nReturn a JSON array of listing objects with these fields (use null if not found):\n- listing_website\n- title\n- bedrooms\n- bathrooms\n- sqft\n- price\n- img_urls\n- full_address\n- street\n- city\n- state\n- description\n- available_date\n- phone_contact\n- email_contact\n- apply_now_link\n\nReturn ONLY the JSON array, no other text.";
      $data = [
        'model' => $model,
        'messages' => [
          ['role' => 'system', 'content' => 'You are an expert at extracting structured data from apartment listing HTML pages. Always return valid JSON.'],
          ['role' => 'user', 'content' => $prompt]
        ],
        'temperature' => 0.2,
        'max_tokens' => $maxTokens
      ];
      $ch = curl_init('https://api.openai.com/v1/chat/completions');
      curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
      curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $api_key
      ]);
      curl_setopt($ch, CURLOPT_POST, true);
      curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
      $response = curl_exec($ch);
      $curlErrNo = curl_errno($ch);
      $curlErr   = $curlErrNo ? curl_error($ch) : '';
      $httpCode  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
      curl_close($ch);
      if ($curlErrNo || $httpCode < 200 || $httpCode >= 300) {
        job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'OpenAI error'], 'OpenAI error: ' . ($curlErrNo ? $curlErr : ('HTTP ' . $httpCode)));
        header('Content-Type: application/json'); echo json_encode(['ok' => false, 'job' => $job, 'status' => job_read($jobsDir, $job)]); exit;
      }
      $jsonResp = json_decode($response, true);
      $modelContent = '';
      if (isset($jsonResp['choices'][0]['message']['content'])) {
        $modelContent = (string)$jsonResp['choices'][0]['message']['content'];
        if (preg_match('/^```(?:json)?\s*(.*)```\s*$/s', $modelContent, $m)) { $modelContent = $m[1]; }
      } else { $modelContent = (string)$response; }
      $decoded = json_decode($modelContent, true);
      if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
        $networkId = null; $baseHtml = basename($fileReal);
        if (preg_match('/networks_(\d+)/i', $baseHtml, $m)) { $networkId = (int)$m[1]; }
        foreach ($decoded as &$item) {
          if (!is_array($item)) continue;
          $item['network_id'] = $item['network_id'] ?? $networkId;
          $item['html_filename'] = $item['html_filename'] ?? $baseHtml;
        }
        unset($item);
        $modelContent = json_encode($decoded, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
      }
      $saveDir = '';
      $selectedReal = $fileReal;
      $capReal = realpath($capturesBaseReal) ?: $capturesBaseReal;
      if ($capReal && stripos($selectedReal, $capReal) === 0) {
        $rel = ltrim(substr($selectedReal, strlen($capReal)), "\\/");
        $parts = preg_split('/[\\\\\/]+/', $rel);
        if (!empty($parts)) {
          $maybeDateFolder = $parts[0];
          $candidate = rtrim($capReal, "\\/" ) . DIRECTORY_SEPARATOR . $maybeDateFolder;
          $saveDir = is_dir($candidate) ? $candidate : dirname($selectedReal);
        }
      }
      if ($saveDir === '') { $saveDir = __DIR__ . DIRECTORY_SEPARATOR . 'downloads'; }
      if (!is_dir($saveDir)) { @mkdir($saveDir, 0777, true); }
      $baseHtml = basename($selectedReal);
      $jsonName = preg_replace('/\.html?$/i', '.json', $baseHtml);
      if ($jsonName === $baseHtml) { $jsonName .= '.json'; }
      $savePath = rtrim($saveDir, "\\/") . DIRECTORY_SEPARATOR . $jsonName;
      @file_put_contents($savePath, $modelContent);
    }

    job_update($jobsDir, $job, ['percent' => 60, 'message' => 'Uploading JSON'], 'Uploading JSON via SFTP');
    job_wait_if_paused($jobsDir, $job);
    $remoteName = basename($savePath) ?: 'chatgpt_extract.json';
    if ($sftpHost !== '' && $sftpUser !== '' && $sftpPass !== '' && $remoteJsonDir !== '' && is_file($savePath)) {
      $sftpResult = uploadFileViaSftpCurl($savePath, $remoteJsonDir, $remoteName, $sftpHost, $sftpPort, $sftpUser, $sftpPass);
    }
    if ($uploadEndpoint !== '' && is_file($savePath)) {
      $uploadResult = uploadFileToServer($savePath, $uploadEndpoint, $uploadAuthToken);
    }
    job_update($jobsDir, $job, ['percent' => 80, 'message' => 'Uploading source HTML'], 'Uploading source HTML via SFTP');
    job_wait_if_paused($jobsDir, $job);
    $selectedReal2 = $fileReal;
    if (is_file($selectedReal2) && $sftpHost && $remoteJsonDir) {
      $htmlUploadResult = uploadFileViaSftpCurl($selectedReal2, $remoteJsonDir, basename($selectedReal2), $sftpHost, $sftpPort, $sftpUser, $sftpPass);
    }
    job_update($jobsDir, $job, [
      'status' => 'done',
      'percent' => 100,
      'message' => 'Completed',
      'result' => [
        'savePath' => $savePath,
        'sftp' => $sftpResult,
        'http' => $uploadResult,
        'htmlSftp' => $htmlUploadResult,
        'listingsCount' => is_array($listings) ? count($listings) : null,
        'method' => $method,
        'model' => $model
      ]
    ], 'Completed');
  } catch (Throwable $e) {
    job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'Exception: ' . $e->getMessage()], 'Exception: ' . $e->getMessage());
  }
  header('Content-Type: application/json'); echo json_encode(['ok' => true, 'job' => $job, 'status' => job_read($jobsDir, $job)]);
  exit;
}

// Async control endpoints
if (isset($_GET['action'])) {
  $action = (string)$_GET['action'];
  if ($action === 'status') {
    $job = isset($_GET['job']) ? (string)$_GET['job'] : '';
    header('Content-Type: application/json');
    echo json_encode(job_read($jobsDir, $job), JSON_UNESCAPED_SLASHES);
    exit;
  }
  if ($action === 'pause' || $action === 'resume') {
    $job = isset($_GET['job']) ? (string)$_GET['job'] : '';
    if ($job !== '') {
      if ($action === 'pause') {
        job_update($jobsDir, $job, ['status' => 'paused', 'message' => 'Paused'], 'Paused by user');
      } else {
        job_update($jobsDir, $job, ['status' => 'running', 'message' => 'Resuming'], 'Resumed by user');
      }
    }
    header('Content-Type: application/json'); echo json_encode(['ok' => true]);
    exit;
  }
  if ($action === 'process') {
    // Run the processing workflow and write progress to the job file
    $job = isset($_GET['job']) ? (string)$_GET['job'] : '';
    $method = isset($_GET['method']) ? (string)$_GET['method'] : 'local';
    $model = isset($_GET['model']) && isset($availableModels[$_GET['model']]) ? (string)$_GET['model'] : $selectedModel;
    $file = isset($_GET['file']) ? (string)$_GET['file'] : '';
    // Normalize Windows-style forward slashes (e.g., C:/path/to/file.html) to backslashes
    if ($file && preg_match('/^[A-Za-z]:\//', $file)) {
      $file = str_replace('/', '\\', $file);
    }
    // If no job id provided (headless/direct call), auto-generate one and init
    if ($job === '') {
      $job = bin2hex(random_bytes(8));
      job_init($jobsDir, $job, ['message' => 'Starting (auto-generated job)']);
    }
    $fileReal = validateInsideBase($file, $capturesBaseReal) ?: '';
  job_update($jobsDir, $job, ['status' => 'running', 'percent' => 3, 'message' => 'Validating inputs'], 'Validating inputs');
  job_wait_if_paused($jobsDir, $job);
    if ($fileReal === '' || !is_file($fileReal)) {
      job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'Selected file not found'], 'Selected file not found');
      header('Content-Type: application/json'); echo json_encode(['ok' => false]); exit;
    }
    // Choose flow
    $listings = [];
    $savePath = '';
    $sftpResult = null; $uploadResult = null; $htmlUploadResult = null;
    try {
      if ($method === 'local') {
  file_put_contents('C:\\xampp\\htdocs\\debug_flow.txt', "Method is local\n", FILE_APPEND);
  job_update($jobsDir, $job, ['percent' => 8, 'message' => 'Parsing locally'], 'Parsing locally');
  job_wait_if_paused($jobsDir, $job);
        $listings = parseListingsLocally($fileReal);
  file_put_contents('C:\\xampp\\htdocs\\debug_flow.txt', "Parsed " . count($listings) . " listings\n", FILE_APPEND);
  job_update($jobsDir, $job, ['percent' => 25, 'message' => 'Parsed ' . count($listings) . ' listings'], 'Parsed ' . count($listings) . ' listings');
  job_wait_if_paused($jobsDir, $job);
        
        // Download and save images locally to Captures/images
        if (count($listings) > 0) {
          job_update($jobsDir, $job, ['percent' => 30, 'message' => 'About to download ' . count($listings) . ' listing images'], 'About to download images');
          $imageResult = uploadListingImages(
            $listings, 
            $remoteImageDir, 
            $sftpHost, 
            $sftpPort, 
            $sftpUser, 
            $sftpPass, 
            $imageBaseUrl, 
            $imageUploadLimit, 
            $imageTimeBudget,
            $localImagesDir,
            $uploadEndpoint,
            $uploadAuthToken
          );
          $listings = $imageResult['listings'];
          $imageStats = $imageResult['stats'];
          $imageLog = $imageResult['log'] ?? [];
          
          // Display log messages
          foreach ($imageLog as $logEntry) {
            job_update($jobsDir, $job, ['message' => $logEntry], $logEntry);
          }
          
          // Build summary message with all stats
          $imgMsg = sprintf('Images: %d attempted, %d saved locally', 
            $imageStats['attempted'] ?? 0, 
            $imageStats['saved'] ?? 0
          );
          if (($imageStats['uploaded_sftp'] ?? 0) > 0) {
            $imgMsg .= sprintf(', %d uploaded to SFTP', $imageStats['uploaded_sftp']);
          }
          if (($imageStats['uploaded_http'] ?? 0) > 0) {
            $imgMsg .= sprintf(', %d uploaded to HTTP server', $imageStats['uploaded_http']);
          }
          job_update($jobsDir, $job, ['percent' => 50, 'message' => $imgMsg], $imgMsg);
          job_wait_if_paused($jobsDir, $job);
        }
        
        // Build JSON and save
        file_put_contents('C:\\xampp\\htdocs\\debug_listings.txt', sprintf(
          "About to save JSON - %d listings, first listing has fields: %s\n",
          count($listings),
          isset($listings[0]) ? implode(', ', array_keys($listings[0])) : 'N/A'
        ));
        $modelContent = json_encode($listings, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        // Save JSON in the same directory as the HTML file (preserves Networks/Websites subfolder)
        $saveDir = dirname($fileReal);
        if ($saveDir === '' || !is_dir($saveDir)) { 
          $saveDir = __DIR__ . DIRECTORY_SEPARATOR . 'downloads'; 
        }
        if (!is_dir($saveDir)) { @mkdir($saveDir, 0777, true); }
        $baseHtml = basename($fileReal);
        $jsonName = preg_replace('/\.html?$/i', '.json', $baseHtml);
        if ($jsonName === $baseHtml) { $jsonName .= '.json'; }
        $savePath = rtrim($saveDir, "\\/") . DIRECTORY_SEPARATOR . $jsonName;
        @file_put_contents($savePath, $modelContent);
      } else {
  job_update($jobsDir, $job, ['percent' => 5, 'message' => 'Loading extraction profiles'], 'Loading extraction profiles');
  job_wait_if_paused($jobsDir, $job);
        // Load extraction profiles
        $profiles = load_profiles($profilesDirReal);
        job_update($jobsDir, $job, ['percent' => 6, 'message' => 'Loaded ' . count($profiles) . ' profiles'], 'Loaded ' . count($profiles) . ' extraction profiles');
        
  job_update($jobsDir, $job, ['percent' => 8, 'message' => 'Calling OpenAI'], 'Calling OpenAI');
  job_wait_if_paused($jobsDir, $job);
        if (!$api_key) {
          job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'OPENAI_API_KEY not set'], 'OPENAI_API_KEY not set');
          header('Content-Type: application/json'); echo json_encode(['ok' => false]); exit;
        }
        $html_content = (string)file_get_contents($fileReal);
        
        // Detect profile based on URL and HTML content
        $fileUrl = ''; // Try to extract URL from filename or HTML
        if (preg_match('/https?:\/\/[^\s\'"]+/i', $html_content, $urlMatch)) {
          $fileUrl = $urlMatch[0];
        }
        $profile = detect_profile($html_content, $fileUrl, $profiles);
        $profileName = $profile['profile_name'] ?? 'default';
        job_update($jobsDir, $job, ['percent' => 9, 'message' => "Using profile: {$profileName}"], "Detected profile: {$profileName}");
        
        // Preprocess HTML using profile rules
        $html_content = preprocess_html_with_profile($html_content, $profile);
        
        // Strip attributes to reduce token usage
        $html_content = preg_replace('/\s+style=\"[^\"]*\"/', '', $html_content);
        $html_content = preg_replace('/\s+data-[a-z-]+=\"[^\"]*\"/', '', $html_content);
        $html_content = preg_replace('/\s+aria-[a-z-]+=\"[^\"]*\"/', '', $html_content);
        $html_content = preg_replace('/\s+role=\"[^\"]*\"/', '', $html_content);
        $html_content = preg_replace('/\s+tabindex=\"[^\"]*\"/', '', $html_content);
        $html_content = preg_replace('/<!--.*?-->/s', '', $html_content);
        $html_content = preg_replace('/\s{2,}/', ' ', $html_content);
        $html_content = preg_replace('/>\s+</', '><', $html_content);
        $maxChars = $availableModels[$model]['max_chars'];
        $maxTokens = $availableModels[$model]['max_tokens'];
        $originalLength = strlen($html_content);
        if ($originalLength > $maxChars) {
          $html_content = substr($html_content, 0, $maxChars) . "\n\n[TRUNCATED: Showing first {$maxChars} of {$originalLength} chars. Extract all visible listings.]";
        }
        // Build prompt using profile template
        $prompt = build_prompt_with_profile($html_content, $profile);
        $data = [
          'model' => $model,
          'messages' => [
            ['role' => 'system', 'content' => 'You are an expert at extracting structured data from apartment listing HTML pages. Always return valid JSON.'],
            ['role' => 'user', 'content' => $prompt]
          ],
          'temperature' => 0.2,
          'max_tokens' => $maxTokens
        ];
        $ch = curl_init('https://api.openai.com/v1/chat/completions');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
          'Content-Type: application/json',
          'Authorization: Bearer ' . $api_key
        ]);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        $response = curl_exec($ch);
        $curlErrNo = curl_errno($ch);
        $curlErr   = $curlErrNo ? curl_error($ch) : '';
        $httpCode  = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($curlErrNo || $httpCode < 200 || $httpCode >= 300) {
          job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'OpenAI error'], 'OpenAI error: ' . ($curlErrNo ? $curlErr : ('HTTP ' . $httpCode)));
          header('Content-Type: application/json'); echo json_encode(['ok' => false]); exit;
        }
        $jsonResp = json_decode($response, true);
        $modelContent = '';
        if (isset($jsonResp['choices'][0]['message']['content'])) {
          $modelContent = (string)$jsonResp['choices'][0]['message']['content'];
          if (preg_match('/^```(?:json)?\s*(.*)```\s*$/s', $modelContent, $m)) { $modelContent = $m[1]; }
        } else { $modelContent = (string)$response; }
        // Enrich with network_id and html_filename
        $decoded = json_decode($modelContent, true);
        if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
          $networkId = null; $baseHtml = basename($fileReal);
          if (preg_match('/networks_(\d+)/i', $baseHtml, $m)) { $networkId = (int)$m[1]; }
          foreach ($decoded as &$item) {
            if (!is_array($item)) continue;
            $item['network_id'] = $item['network_id'] ?? $networkId;
            $item['html_filename'] = $item['html_filename'] ?? $baseHtml;
          }
          unset($item);
          $modelContent = json_encode($decoded, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        }
        // Save JSON in the same directory as the HTML file (preserves Networks/Websites subfolder)
        $saveDir = dirname($fileReal);
        if ($saveDir === '' || !is_dir($saveDir)) { 
          $saveDir = __DIR__ . DIRECTORY_SEPARATOR . 'downloads'; 
        }
        if (!is_dir($saveDir)) { @mkdir($saveDir, 0777, true); }
        $baseHtml = basename($fileReal);
        $jsonName = preg_replace('/\.html?$/i', '.json', $baseHtml);
        if ($jsonName === $baseHtml) { $jsonName .= '.json'; }
        $savePath = rtrim($saveDir, "\\/") . DIRECTORY_SEPARATOR . $jsonName;
        @file_put_contents($savePath, $modelContent);
      }
  job_update($jobsDir, $job, ['percent' => 60, 'message' => 'Uploading JSON'], 'Uploading JSON via SFTP');
  job_wait_if_paused($jobsDir, $job);
  // Upload JSON via SFTP (use same basename as local JSON)
  $remoteName = basename($savePath) ?: 'chatgpt_extract.json';
      if ($sftpHost !== '' && $sftpUser !== '' && $sftpPass !== '' && $remoteJsonDir !== '' && is_file($savePath)) {
        $sftpResult = uploadFileViaSftpCurl($savePath, $remoteJsonDir, $remoteName, $sftpHost, $sftpPort, $sftpUser, $sftpPass);
      }
      if ($uploadEndpoint !== '' && is_file($savePath)) {
        $uploadResult = uploadFileToServer($savePath, $uploadEndpoint, $uploadAuthToken);
      }
  job_update($jobsDir, $job, ['percent' => 80, 'message' => 'Uploading source HTML'], 'Uploading source HTML via SFTP');
  job_wait_if_paused($jobsDir, $job);
      $selectedReal2 = $fileReal;
      if (is_file($selectedReal2) && $sftpHost && $remoteJsonDir) {
        $htmlUploadResult = uploadFileViaSftpCurl($selectedReal2, $remoteJsonDir, basename($selectedReal2), $sftpHost, $sftpPort, $sftpUser, $sftpPass);
      }
      // Done
      $cntStr = is_array($listings) ? (string)count($listings) : 'N/A';
      $sftpOk = ($sftpResult && is_array($sftpResult) && !empty($sftpResult['success'])) ? 'Success' : 'Skipped/Failed';
      $htmlOk = ($htmlUploadResult && is_array($htmlUploadResult) && !empty($htmlUploadResult['success'])) ? 'Success' : 'Skipped/Failed';
      $summary = "Completed — Listings: {$cntStr}; JSON: {$savePath}; SFTP JSON: {$sftpOk}; SFTP HTML: {$htmlOk}";
      job_update($jobsDir, $job, [
        'status' => 'done',
        'percent' => 100,
        'message' => 'Completed',
        'result' => [
          'savePath' => $savePath,
          'sftp' => $sftpResult,
          'http' => $uploadResult,
          'htmlSftp' => $htmlUploadResult,
          'listingsCount' => is_array($listings) ? count($listings) : null,
          'method' => $method,
          'model' => $model
        ]
      ], $summary);
    } catch (Throwable $e) {
      job_update($jobsDir, $job, ['status' => 'error', 'percent' => 100, 'message' => 'Exception: ' . $e->getMessage()], 'Exception: ' . $e->getMessage());
    }
    header('Content-Type: application/json'); echo json_encode(['ok' => true, 'job' => $job]);
    exit;
  }
}

// Handle direct download request
if (isset($_GET['download'])) {
    $dlPath = (string)$_GET['download'];
    $dlReal = realpath($dlPath);
    if ($dlReal && is_file($dlReal)) {
        $dlName = basename($dlReal);
        header('Content-Type: application/json; charset=utf-8');
        header('Content-Disposition: attachment; filename="' . $dlName . '"');
        header('Content-Length: ' . filesize($dlReal));
        readfile($dlReal);
        exit;
    } else {
        http_response_code(404);
        echo "File not found for download.";
        exit;
    }
}

// ---------- Local parsing functions ----------
function parseListingsLocally(string $htmlFile): array {
  // Load profiles
  $profilesDir = getenv('PROFILES_DIR') ?: 'C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Extract Profiles\\Network';
  $profilesDirReal = realpath($profilesDir) ?: $profilesDir;
  $profiles = load_profiles($profilesDirReal);
  
  // Database connection for google_places lookup
  // Use same credentials as the poller (see th_poller/config_utils.py)
  $db_host = getenv('MYSQL_HOST') ?: '127.0.0.1';
  $db_user = getenv('MYSQL_USER') ?: 'local_uzr';
  $db_pass = getenv('MYSQL_PASSWORD') ?: 'fuck';
  $db_name = getenv('MYSQL_DB') ?: 'offta';
  $db_port = (int)(getenv('MYSQL_PORT') ?: '3306');
  $mysqli = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
  if ($mysqli->connect_errno) {
    error_log('DB connect error: ' . $mysqli->connect_error);
    $mysqli = null;
  }
  // Derive network_id from file name (e.g., networks_6.html -> 6)
  $networkId = null;
  $baseHtml = basename($htmlFile);
  if (preg_match('/networks_(\d+)/i', $baseHtml, $m)) {
    $networkId = (int)$m[1];
  }
  // Detect place-id column ONCE to avoid repeated SHOW COLUMNS calls per listing
  $placeIdCol = null;
  if ($mysqli) {
    foreach (['google_places_id','place_id','google_place_id','placeId','placeID'] as $cand) {
      if (db_has_column($mysqli, 'google_places', $cand)) { $placeIdCol = $cand; break; }
    }
  }
    $html = file_get_contents($htmlFile);
    if (!$html) return [];
    
    // Detect profile BEFORE stripping forms
    $fileUrl = '';
    if (preg_match('/https?:\/\/[^\s\'"]+/i', $html, $urlMatch)) {
      $fileUrl = $urlMatch[0];
    }
    $profile = detect_profile($html, $fileUrl, $profiles);
    $profileName = $profile['profile_name'] ?? 'default';
    error_log("parseListingsLocally: Using profile '{$profileName}' for {$baseHtml}");
    
    // CRITICAL: Strip out forms and select elements BEFORE parsing
    $html = preg_replace('/<form\b[^>]*>.*?<\/form>/si', '', $html);
    $html = preg_replace('/<select\b[^>]*>.*?<\/select>/si', '', $html);
    
    // Use DOMDocument for robust parsing
    libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    // Use proper HTML5 loading - don't use NOIMPLIED/NODEFDTD flags
    $dom->loadHTML($html);
    libxml_clear_errors();
    
  $xpath = new DOMXPath($dom);
    $listings = [];
    
    // Use profile's listing_selector if available
    $listingSelector = $profile['extraction']['listing_selector'] ?? '';
    $listingNodes = null;
    
    if ($listingSelector) {
      // Parse selector and try to build XPath query
      $selectorParts = array_map('trim', explode(',', $listingSelector));
      foreach ($selectorParts as $sel) {
        // Convert simple CSS selector to XPath
        $xpathQuery = '';
        if (preg_match('/^div\.([a-z0-9_-]+)$/i', $sel, $m)) {
          // div.class-name - match EXACT class token (not contains)
          // This prevents matching "js-listing-item-blurb" when looking for "js-listing-item"
          $className = $m[1];
          $xpathQuery = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {$className} ')]";
        } elseif (preg_match('/^div\.([a-z0-9_-]+)\.([a-z0-9_-]+)$/i', $sel, $m)) {
          // div.class1.class2 - match both exact class tokens
          $class1 = $m[1];
          $class2 = $m[2];
          $xpathQuery = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {$class1} ') and contains(concat(' ', normalize-space(@class), ' '), ' {$class2} ')]";
        } elseif (preg_match('/^div\[class="([^"]+)"\]$/i', $sel, $m)) {
          // div[class="exact-class"]
          $xpathQuery = "//div[@class='{$m[1]}']";
        } elseif (preg_match('/^div\[role="([^"]+)"\]$/i', $sel, $m)) {
          // div[role="listitem"]
          $xpathQuery = "//div[@role='{$m[1]}']";
        }
        
        if ($xpathQuery) {
          $listingNodes = $xpath->query($xpathQuery);
          if ($listingNodes && $listingNodes->length > 0) {
            error_log("parseListingsLocally: Profile selector '{$sel}' matched {$listingNodes->length} nodes with XPath: {$xpathQuery}");
            break;
          }
        }
      }
    }
    
    // Fallback to default selectors if profile didn't match
    // CRITICAL: Be VERY specific to match ONLY the top-level listing containers
    if (!$listingNodes || $listingNodes->length === 0) {
      // For AppFolio sites: Match divs with id starting with "listing_" - this is the most reliable
      $listingNodes = $xpath->query("//div[starts-with(@id, 'listing_')]");
    }
    
    if ($listingNodes->length === 0) {
      // Secondary: Match divs with class containing "js-listing-item" (exact class token)
      $listingNodes = $xpath->query("//div[contains(concat(' ', normalize-space(@class), ' '), ' js-listing-item ')]");
    }
    
    if ($listingNodes->length === 0) {
      // Tertiary: Match class with both "listing-item" and "result" and has an id attribute
      $listingNodes = $xpath->query("//div[@id and contains(@class, 'listing-item') and contains(@class, 'result')]");
    }
    
    if ($listingNodes->length === 0) {
      // Match Wix repeater items - these have "__item" in the class
      $listingNodes = $xpath->query("//div[contains(@class, 'wixui-repeater__item')]");
    }
    
    if ($listingNodes->length === 0) {
      $listingNodes = $xpath->query("//article | //li[@role='listitem'] | //div[@role='listitem']");
    }
    
    // Debug: log how many nodes were found
    error_log("parseListingsLocally: Found " . $listingNodes->length . " listing nodes in " . basename($htmlFile));
    
  $resultNumber = 1; // Track result number for each listing
  foreach ($listingNodes as $node) {
    $listing = [
      'result_number' => $resultNumber,
      'listing_website' => null,
      'title' => null,
      'network_id' => $networkId,
      'bedrooms' => null,
      'bathrooms' => null,
      'sqft' => null,
      'price' => null,
      'img_urls' => null,
      'image_filename' => null,
      'html_filename' => $baseHtml,
      'full_address' => null,
      'street' => null,
      'city' => null,
      'state' => null,
      'description' => null,
      'available_date' => null,
      'phone_contact' => null,
      'email_contact' => null,
      'apply_now_link' => null,
      'listing_id' => null,
      'unit' => null,
      'google_address' => null,
      'google_addresses_id' => null,
      'google_places_id' => null
    ];

    // SMART EXTRACTION: Try multiple strategies for each field
    
    // Extract title and listing_website - try multiple patterns
    $titleNode = $xpath->query(".//h2[contains(@class, 'listing-item__title')]//a", $node)->item(0);
    if (!$titleNode) $titleNode = $xpath->query(".//h2[@class='address']//a | .//h2[contains(@class, 'address')]//a", $node)->item(0);
    if (!$titleNode) $titleNode = $xpath->query(".//a[contains(@class, 'slider-link')]", $node)->item(0);
    if (!$titleNode) $titleNode = $xpath->query(".//a[contains(@href, '/listings/detail')]", $node)->item(0);
    if (!$titleNode) $titleNode = $xpath->query(".//a[contains(@href, '/properties/')]", $node)->item(0); // Milestone-style URLs
    if (!$titleNode) $titleNode = $xpath->query(".//a[1]", $node)->item(0); // First link as fallback
    
    if ($titleNode) {
      $listing['listing_website'] = $titleNode->getAttribute('href');
      // Try to get title from link text first
      $linkText = trim($titleNode->textContent);
      if ($linkText && strlen($linkText) > 3) {
        $listing['title'] = $linkText;
      }
    }
    
    // If no title from link, try h2 elements (Wix/Milestone pattern: h2 with property name)
    if (!isset($listing['title']) || !$listing['title']) {
      $h2Nodes = $xpath->query(".//h2", $node);
      $meaningfulH2s = [];
      foreach ($h2Nodes as $h2) {
        $h2Text = trim($h2->textContent);
        // Skip common non-title text like "Available", "Bed", "Bath"
        if ($h2Text && strlen($h2Text) > 3 && 
            !in_array(strtolower($h2Text), ['available', 'bed', 'bath', 'beds', 'baths'])) {
          $meaningfulH2s[] = $h2Text;
        }
      }
      // Use first meaningful h2 as title (building name)
      if (count($meaningfulH2s) > 0) {
        $listing['title'] = $meaningfulH2s[0];
      }
    }

    // Extract image - try multiple patterns
    $imgNode = $xpath->query(".//img[contains(@class, 'listing-item__image')]", $node)->item(0);
    if (!$imgNode) $imgNode = $xpath->query(".//img[contains(@class, 'slider-image')]", $node)->item(0);
    if (!$imgNode) $imgNode = $xpath->query(".//div[contains(@class, 'slider-image')]", $node)->item(0);
    if (!$imgNode) $imgNode = $xpath->query(".//img[1]", $node)->item(0); // First image as fallback
    
    if ($imgNode) {
      // Try various image URL attributes
      $imgUrl = $imgNode->getAttribute('data-background-image') 
             ?: $imgNode->getAttribute('data-original') 
             ?: $imgNode->getAttribute('src')
             ?: $imgNode->getAttribute('data-src');
      
      // If it's a div with background-image, extract from style
      if (!$imgUrl && $imgNode->nodeName === 'div') {
        $style = $imgNode->getAttribute('style');
        if (preg_match('/background-image:\s*url\(["\']?([^"\')]+)["\']?\)/i', $style, $m)) {
          $imgUrl = $m[1];
        }
      }
      
      $listing['img_urls'] = $imgUrl;
      
      // Generate image filename using network_id and result_number
      $ext = 'png'; // Default extension
      if ($imgUrl) {
        $urlPath = parse_url($imgUrl, PHP_URL_PATH);
        if ($urlPath) {
          $urlExt = pathinfo($urlPath, PATHINFO_EXTENSION);
          if ($urlExt && in_array(strtolower($urlExt), ['jpg','jpeg','png','gif','webp'])) {
            $ext = strtolower($urlExt);
          }
        }
      }
      // Format: network_{network_id}_{result_number}.{ext}
      $listing['image_filename'] = sprintf('network_%s_%03d.%s', $networkId ?: '1', $resultNumber, $ext);
    }

    // Extract address - try multiple patterns
    $addressNode = $xpath->query(".//span[contains(@class, 'js-listing-address')]", $node)->item(0);
    if (!$addressNode) $addressNode = $xpath->query(".//h2[contains(@class, 'address')]", $node)->item(0);
    if (!$addressNode) $addressNode = $xpath->query(".//span[contains(@class, 'address')]", $node)->item(0);
    if (!$addressNode) $addressNode = $xpath->query(".//*[contains(text(), ', WA ') or contains(text(), ', CA ') or contains(text(), ', OR ')]", $node)->item(0);
    
    if ($addressNode) {
      $fullAddr = trim($addressNode->textContent);
      $listing['full_address'] = $fullAddr;
      // Extract unit (e.g., '#02', 'Apt 5', 'Unit 3B', ' - 28') and remove from address for google_address
      $unit = null;
      $googleAddr = $fullAddr;
      // Try patterns: - 28, #02, Apt 5, Unit 3B, Ste 4, Suite 7, etc.
      // Match " - \d+" pattern (e.g., " - 28", " - 206") - must come before comma or end of string
      if (preg_match('/\s*-\s*(\d+)(?=\s*,|$)/i', $fullAddr, $m)) {
        $unit = $m[1];  // Just the number
        $googleAddr = preg_replace('/\s*-\s*\d+(?=\s*,|$)/i', '', $fullAddr);
      }
      // Then try other patterns: #02, Apt 5, Unit 3B, etc.
      elseif (preg_match('/,?\s*(#\w+|Apt\.?\s*\w+|Unit\s*\w+|Ste\.?\s*\w+|Suite\s*\w+)/i', $fullAddr, $m)) {
        $unit = trim($m[1]);
        $googleAddr = trim(str_replace($m[0], '', $fullAddr), ', ');
      }
      $listing['unit'] = $unit;
      $listing['google_address'] = trim($googleAddr);
      // Parse address components (from google_address)
      if (preg_match('/^(.+?),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})$/i', $googleAddr, $match)) {
        $listing['street'] = $match[1];
        $listing['city'] = $match[2];
        $listing['state'] = strtoupper($match[3]);
      }
    } else {
      // SPECIAL HANDLING: If no address found, try constructing from title + neighborhood
      // Common for sites like rentmilestone.com which show "1415 E John" + "Capitol Hill"
      $titleForAddr = $listing['title'] ?? null;
      
      // Get neighborhood from second h2 (skip the title h2)
      $neighborhood = null;
      $h2Nodes = $xpath->query(".//h2", $node);
      $meaningfulH2s = [];
      foreach ($h2Nodes as $h2) {
        $h2Text = trim($h2->textContent);
        // Skip common non-title text like "Available", "Bed", "Bath"
        if ($h2Text && strlen($h2Text) > 3 && 
            !in_array(strtolower($h2Text), ['available', 'bed', 'bath', 'beds', 'baths'])) {
          $meaningfulH2s[] = $h2Text;
        }
      }
      // Use second meaningful h2 as neighborhood (if exists)
      if (count($meaningfulH2s) > 1) {
        $neighborhood = $meaningfulH2s[1]; // Second h2 is the neighborhood
      }
      
      if ($titleForAddr && $neighborhood) {
        // Check if title looks like a street address (contains numbers)
        if (preg_match('/\d/', $titleForAddr)) {
          // Title has numbers - it's likely a street address like "1415 E John"
          $listing['street'] = $titleForAddr;
        }
        // Don't set city - neighborhood is not a city
        // Include neighborhood in address for geocoding to work
        $listing['full_address'] = $titleForAddr . ', ' . $neighborhood;
        $listing['google_address'] = $titleForAddr . ', ' . $neighborhood;
      } elseif ($titleForAddr) {
        // Only title available, no neighborhood
        if (preg_match('/\d/', $titleForAddr)) {
          $listing['street'] = $titleForAddr;
        }
        $listing['full_address'] = $titleForAddr;
        $listing['google_address'] = $titleForAddr;
      }
    }

    // Extract price - try multiple patterns
    $price = null;
    $priceNode = $xpath->query(".//dd[@class='detail-box__value'][preceding-sibling::dt[contains(text(), 'RENT')]]", $node)->item(0);
    if (!$priceNode) $priceNode = $xpath->query(".//div[contains(@class, 'js-listing-blurb-rent')]", $node)->item(0);
    if (!$priceNode) $priceNode = $xpath->query(".//h3[contains(@class, 'rent')]", $node)->item(0);
    if (!$priceNode) $priceNode = $xpath->query(".//*[contains(@class, 'price') or contains(@class, 'rent')]", $node)->item(0);
    if (!$priceNode) {
      // Look for any text containing $ followed by digits
      $allText = $node->textContent;
      if (preg_match('/\$[\d,]+/', $allText, $m)) {
        $price = $m[0];
      }
    } else {
      $price = trim($priceNode->textContent);
    }
    $listing['price'] = $price;

    // Extract bedrooms and bathrooms - try multiple patterns
    $bed = null; $bath = null;
    
    // Try specific patterns first
    $bedBathNode = $xpath->query(".//dd[@class='detail-box__value'][preceding-sibling::dt[contains(text(), 'Bed / Bath')]]", $node)->item(0);
    if (!$bedBathNode) $bedBathNode = $xpath->query(".//span[contains(@class, 'js-listing-blurb-bed-bath')]", $node)->item(0);
    if (!$bedBathNode) $bedBathNode = $xpath->query(".//div[contains(@class, 'beds') or contains(@class, 'amenities')]", $node)->item(0);
    
    if ($bedBathNode) {
      $bedBathText = trim($bedBathNode->textContent);
      // Accept formats like "1 bd / 1 ba", "2 bd / 1.5 ba", "Studio / 1 ba", "1 bed 1 bath"
      if (preg_match('/(\d+(?:\.\d+)?|Studio)\s*(?:bd|bed)?\s*[\/\s]+\s*(\d+(?:\.\d+)?)\s*(?:ba|bath)/i', $bedBathText, $m)) {
        $bed = stripos($m[1], 'studio') !== false ? 'Studio' : $m[1];
        $bath = $m[2];
      }
      // Fallback if only Studio mentioned without slash
      if (!$bed && preg_match('/\bStudio\b/i', $bedBathText)) {
        $bed = 'Studio';
      }
    }
    
    // If still not found, try individual lookups
    if (!$bed) {
      $bedNode = $xpath->query(".//*[contains(@class, 'beds') or contains(@class, 'feature beds')]", $node)->item(0);
      if ($bedNode) {
        $bedText = trim($bedNode->textContent);
        if (preg_match('/(\d+)\s*bed/i', $bedText, $m)) {
          $bed = $m[1];
        } elseif (preg_match('/Studio/i', $bedText)) {
          $bed = 'Studio';
        }
      }
    }
    
    if (!$bath) {
      $bathNode = $xpath->query(".//*[contains(@class, 'baths') or contains(@class, 'feature baths')]", $node)->item(0);
      if ($bathNode) {
        $bathText = trim($bathNode->textContent);
        if (preg_match('/(\d+(?:\.\d+)?)\s*bath/i', $bathText, $m)) {
          $bath = $m[1];
        }
      }
    }
    // Normalize 0 bedrooms to Studio if encountered
    if ($bed !== null && is_numeric($bed) && (float)$bed === 0.0) {
      $bed = 'Studio';
    }
    $listing['bedrooms'] = $bed;
    $listing['bathrooms'] = $bath;

    // Extract sqft - try multiple patterns
    $sqftNode = $xpath->query(".//dd[@class='detail-box__value'][preceding-sibling::dt[contains(text(), 'Square Feet')]]", $node)->item(0);
    if (!$sqftNode) $sqftNode = $xpath->query(".//span[contains(@class, 'js-listing-square-feet')]", $node)->item(0);
    if (!$sqftNode) $sqftNode = $xpath->query(".//*[contains(@class, 'sqft') or contains(@class, 'square')]", $node)->item(0);
    if (!$sqftNode) $sqftNode = $xpath->query(".//*[contains(@class, 'feature sqft')]", $node)->item(0);
    
    if ($sqftNode) {
      $sqftText = trim($sqftNode->textContent);
      if (preg_match('/(\d[\d,]*)\s*sqft/i', $sqftText, $m)) {
        $listing['sqft'] = (int)str_replace(',', '', $m[1]);
      } elseif (preg_match('/(\d[\d,]*)/', $sqftText, $m)) {
        $listing['sqft'] = (int)str_replace(',', '', $m[1]);
      }
    }

    // Extract description
    $descNode = $xpath->query(".//p[contains(@class, 'js-listing-description')]", $node)->item(0);
    if ($descNode) {
      $listing['description'] = trim($descNode->textContent);
    }

    // Extract available date - try multiple patterns
    $availNode = $xpath->query(".//dd[@class='detail-box__value'][preceding-sibling::dt[contains(text(), 'Available')]]", $node)->item(0);
    if (!$availNode) $availNode = $xpath->query(".//span[contains(@class, 'js-listing-available')]", $node)->item(0);
    if (!$availNode) $availNode = $xpath->query(".//*[contains(@class, 'available') or contains(@class, 'date')]", $node)->item(0);
    if (!$availNode) $availNode = $xpath->query(".//span[contains(@class, 'feature date')]", $node)->item(0);
    
    if ($availNode) {
      $dateText = trim($availNode->textContent);
      // Look for date patterns: "Now", "Available: 1/15/2024", "Jan 15, 2024"
      if (preg_match('/now|immediate/i', $dateText)) {
        $listing['available_date'] = date('Y-m-d');
      } elseif (preg_match('/(\d{1,2}\/\d{1,2}\/\d{4})/', $dateText, $m)) {
        $listing['available_date'] = date('Y-m-d', strtotime($m[1]));
      } elseif (preg_match('/([A-Za-z]+\s+\d{1,2},?\s+\d{4})/', $dateText, $m)) {
        $listing['available_date'] = date('Y-m-d', strtotime($m[1]));
      } else {
        $listing['available_date'] = $dateText;
      }
    }

    // Apply link
    $applyNode = $xpath->query(".//a[contains(@href, 'rental_applications')]", $node)->item(0);
    if ($applyNode) {
      $listing['apply_now_link'] = $applyNode->getAttribute('href');
    }

    // Listing ID: try to extract from URL or node id
    $listing['listing_id'] = null;
    if (!empty($listing['listing_website']) && preg_match('/([a-f0-9\-]{8,})/', $listing['listing_website'], $m)) {
      $listing['listing_id'] = $m[1];
    } elseif ($node->hasAttributes() && $node->attributes->getNamedItem('id')) {
      $listing['listing_id'] = $node->attributes->getNamedItem('id')->nodeValue;
    }

    // Lookup google_address in google_places table (use pre-detected $placeIdCol)
    if ($mysqli && !empty($listing['google_address'])) {
      $addr = $mysqli->real_escape_string($listing['google_address']);
      $sql = $placeIdCol
        ? "SELECT id, {$placeIdCol} AS google_places_id, Fulladdress, Street FROM google_places WHERE Fulladdress = '$addr' OR Street = '$addr' LIMIT 1"
        : "SELECT id, Fulladdress, Street FROM google_places WHERE Fulladdress = '$addr' OR Street = '$addr' LIMIT 1";
      try {
        $res = $mysqli->query($sql);
        if ($res && $row = $res->fetch_assoc()) {
          $listing['google_addresses_id'] = $row['id'];
          $listing['google_places_id'] = $row['google_places_id'] ?? null;
        }
        if ($res) $res->free();
      } catch (Throwable $e) {
        error_log('DB lookup failed: ' . $e->getMessage());
      }
    }

    $listings[] = $listing;
    $resultNumber++; // Increment for next listing
  }
  if ($mysqli) $mysqli->close();
  return $listings;
}

// ---------- Process request ----------
if ($shouldProcess) {
  // Switch to async progress page that starts the processing in another request and polls status
  $jobId = bin2hex(random_bytes(8));
  job_init($jobsDir, $jobId, ['message' => 'Queued']);
  $fileForJob = realpath($selected) ?: $selected;
  $methodForJob = $parseMethod;
  $modelForJob = $selectedModel;
  ?><!doctype html>
  <html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Processing…</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #222; }
      .box { border: 1px solid #ddd; padding: 12px; border-radius: 6px; margin-top: 16px; background: #f9f9f9; }
      .path { font-family: Consolas, Menlo, monospace; background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
      .bar { width: 100%; height: 10px; background: #eee; border-radius: 4px; overflow: hidden; }
      .bar > div { height: 100%; width: 0%; background: #1a73e8; transition: width 0.5s ease; }
      pre { background: #f7f7f7; padding: 12px; overflow: auto; max-height: 400px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h2>Working… (<?php echo h($methodForJob === 'local' ? 'Local Parser' : ('AI: ' . $availableModels[$modelForJob]['name'])); ?>)</h2>
    <div class="box">
      <p><strong>Selected file:</strong> <span class="path"><?php echo h($fileForJob); ?></span></p>
      <div class="bar"><div id="pbar"></div></div>
      <p id="pmsg" class="muted">Starting…</p>
    </div>

    <div class="box">
      <h3>Live log</h3>
      <pre id="plog"></pre>
    </div>

    <div class="box" id="resultBox" style="display:none">
      <h3>Result</h3>
      <div id="resultContent"></div>
    </div>

    <div style="margin-top: 16px;">
      <a href="<?php echo h(basename(__FILE__)); ?>">
        <button type="button">Cancel / Back</button>
      </a>
    </div>

    <script>
      const job = <?php echo json_encode($jobId); ?>;
      const file = <?php echo json_encode($fileForJob); ?>;
      const method = <?php echo json_encode($methodForJob); ?>;
      const model = <?php echo json_encode($modelForJob); ?>;
      const pbar = document.getElementById('pbar');
      const pmsg = document.getElementById('pmsg');
      const plog = document.getElementById('plog');
      const resultBox = document.getElementById('resultBox');
      const resultContent = document.getElementById('resultContent');
      let started = false;

      function startProcess() {
        // Fire the processing request in parallel; we don't await it
        fetch(`<?php echo basename(__FILE__); ?>?action=process&job=${encodeURIComponent(job)}&file=${encodeURIComponent(file)}&method=${encodeURIComponent(method)}&model=${encodeURIComponent(model)}`)
          .catch(() => {});
      }

      async function poll() {
        try {
          const r = await fetch(`<?php echo basename(__FILE__); ?>?action=status&job=${encodeURIComponent(job)}`, { cache: 'no-store' });
          if (!r.ok) throw new Error('status http ' + r.status);
          const s = await r.json();
          const pct = Math.max(0, Math.min(100, parseInt(s.percent || 0, 10)));
          pbar.style.width = pct + '%';
          pmsg.textContent = s.message || '';
          if (Array.isArray(s.log)) {
            plog.textContent = s.log.join('\n');
            plog.scrollTop = plog.scrollHeight;
          }
          if (s.status === 'done') {
            resultBox.style.display = '';
            const res = s.result || {};
            const savePath = res.savePath ? String(res.savePath) : '';
            const listingsCount = res.listingsCount != null ? String(res.listingsCount) : 'N/A';
            const sftp = res.sftp && res.sftp.success ? 'Success' : 'Skipped/Failed';
            const htmlUp = res.htmlSftp && res.htmlSftp.success ? 'Success' : 'Skipped/Failed';
            const dlLink = savePath ? `<?php echo basename(__FILE__); ?>?download=${encodeURIComponent(savePath)}` : '';
            resultContent.innerHTML = `
              <p><strong>Listings extracted:</strong> ${listingsCount}</p>
              <p><strong>JSON file:</strong> <code>${savePath || '[n/a]'}</code> ${dlLink ? ` — <a href="${dlLink}">Download</a>` : ''}</p>
              <p><strong>SFTP JSON:</strong> ${sftp}</p>
              <p><strong>SFTP HTML:</strong> ${htmlUp}</p>
            `;
            return; // stop polling
          }
          if (s.status === 'error') {
            resultBox.style.display = '';
            resultContent.textContent = 'Error: ' + (s.message || 'Unknown error');
            return;
          }
        } catch (e) {
          // ignore transient errors
        } finally {
          setTimeout(poll, 1000);
        }
      }

      if (!started) { started = true; startProcess(); poll(); }
    </script>
  </body>
  </html>
  <?php
  exit;
}

// ---------- Render selection page ----------
?><!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Process HTML with OpenAI</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #222; }
    .row { margin-bottom: 12px; }
    select { width: 100%; max-width: 900px; padding: 6px; }
    button { padding: 8px 14px; cursor: pointer; }
    .muted { color: #666; }
    .error { color: #b00020; }
    .box { border: 1px solid #ddd; padding: 12px; border-radius: 6px; margin-top: 16px; }
    .path { font-family: Consolas, Menlo, monospace; }
  </style>
</head>
<body>
  <h2>Process HTML with OpenAI</h2>

  <div class="row">
    <div><strong>Captures folder:</strong> <span class="path"><?php echo h(realpath($capturesBaseReal) ?: $capturesBaseReal); ?></span></div>
    <?php if (!is_dir($capturesBaseReal)): ?>
      <div class="error">Captures folder not found. Set CAPTURES_DIR environment variable or edit the path in this script.</div>
    <?php endif; ?>
  </div>

  <form method="get" class="box">
    <div class="row">
      <label for="file"><strong>Select HTML file</strong> (newest first):</label><br>
      <select name="file" id="file" required>
        <?php if (!$files): ?>
          <option value="">No .html files found</option>
        <?php else: ?>
          <?php foreach ($files as $item): 
            $p = $item['path'];
            $isSelected = $selected && (realpath($p) === realpath($selected));
            $label = relLabel($p, $capturesBaseReal);
            $time = fmtTime($item['mtime']);
          ?>
            <option value="<?php echo h($p); ?>" <?php echo $isSelected ? 'selected' : ''; ?>>
              <?php echo h($label . "  [" . $time . "]"); ?>
            </option>
          <?php endforeach; ?>
        <?php endif; ?>
      </select>
    </div>
    
    <div class="row">
      <label for="model"><strong>Select AI Model:</strong></label><br>
      <select name="model" id="model" style="max-width: 600px;">
        <?php foreach ($availableModels as $modelKey => $modelInfo): 
          $isSelected = ($modelKey === $selectedModel);
        ?>
          <option value="<?php echo h($modelKey); ?>" <?php echo $isSelected ? 'selected' : ''; ?>>
            <?php echo h($modelInfo['name']); ?> — <?php echo h($modelInfo['context']); ?> 
            (In: <?php echo h($modelInfo['input_price']); ?> | Out: <?php echo h($modelInfo['output_price']); ?>)
          </option>
        <?php endforeach; ?>
      </select>
      <div class="muted" style="margin-top: 4px; font-size: 0.9em;">
        💡 <strong>Recommended:</strong> GPT-4o Mini (best value, 128k context, handles full HTML files)
      </div>
    </div>
    
    <div class="row">
      <label><strong>Parsing Method:</strong></label><br>
      <label style="margin-right: 16px;">
        <input type="radio" name="method" value="local" <?php echo ($parseMethod === 'local') ? 'checked' : ''; ?>>
        Local Parser (Free, Fast, All 178 listings) ⭐ Recommended
      </label>
      <label>
        <input type="radio" name="method" value="ai" <?php echo ($parseMethod === 'ai') ? 'checked' : ''; ?>>
        AI Parser (Uses OpenAI, ~80-100 listings max due to token limits)
      </label>
      <div class="muted" style="margin-top: 4px; font-size: 0.9em;">
        Local parser uses PHP DOMDocument + XPath to extract all listings instantly without API costs.
      </div>
    </div>
    
    <div class="row">
  <button type="submit" name="process" value="1">Process and Upload JSON</button>
    </div>
    <div class="row muted">
  The JSON will be saved locally and uploaded via SFTP (if SFTP_* vars are set) or HTTP (if UPLOAD_ENDPOINT is set).
    </div>
  </form>

  <div class="row muted">Tip: Provide OPENAI_API_KEY as an environment variable or create an <code>openai_key.txt</code> next to this script.</div>

</body>
</html>
