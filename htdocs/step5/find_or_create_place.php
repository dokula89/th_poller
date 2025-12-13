<?php
require_once __DIR__ . '/db_config.php';

///////////////
// DEBUG SETUP
///////////////
$__FOP_T0 = microtime(true);
$DEBUG_ON = (isset($_GET['debug']) && ($_GET['debug'] === '1' || strtolower($_GET['debug']) === 'true'))
            || (getenv('FOP_DEBUG') === '1');
$DEBUG_LOG = [];
function dbg($msg) {
  global $DEBUG_ON, $DEBUG_LOG;
  if ($DEBUG_ON) {
    $line = '['.date('H:i:s').'] '.$msg;
    $DEBUG_LOG[] = $line;
    error_log('[FOP DEBUG] '.$line);
  }
}
/**
 * find_or_create_place.php  (TEST MODE — may update king_county_parcels.google_addresses_id if safe, but no inserts)
 *
 * Goal:
 *   1) Force Google PLACES (Find Place from Text) lookup for the incoming address.
 *   2) If PLACES returns a place_id, check if that place_id exists in `google_places`. If yes → return its id.
 *      If not → DO NOT INSERT; return a test-only preview with would_insert_into='google_places'.
 *   3) If PLACES finds nothing, fallback to Google GEOCODING for place_id, check `google_addresses`. If not found → NO INSERT;
 *      return a test-only preview with would_insert_into='google_addresses'.
 *   4) Also return near candidates from existing tables for manual review. NO WRITES are performed here, except that
 *      king_county_parcels.google_addresses_id may be updated if it is empty/null and a safe match is found.
 *   5) OPTIMIZATION: If data exists in google_addresses and is less than 24 hours old, skip Google API calls
 *      and return existing data with data_fresh=true and data_age_hours fields.
 *
 * Usage:
 *   GET /find_or_create_place.php?address=427%20Bellevue%20Way%20SE%20%2366,%20Bellevue,%20WA%2098004
 *   Optional: &region=us  (two-letter ccTLD region bias)
 *
 * Response (JSON):
 * {
 *   "ok": true,
 *   "result": {
 *     "source": "google_places" | "google_addresses" | "places_api_preview" | "geocode_api_preview",
 *     "id": 1234,                             // only when matched in DB
 *     "place_id": "ChIJ…",                    // when available from API
 *     "name": "Building",                     // PLACES
 *     "full_address": "raw Fulladdress",      // from google_places table
 *     "formatted_address": "…",               // from Geocode or GA json_dump
 *     "lat": 47.6, "lng": -122.3,             // when available
 *     "normalized_input": "…",
 *     "normalized_match": "…",
 *     "similarity": 100,                      // when applicable
 *     "would_insert_into": "google_places" | "google_addresses" | null,
 *     "data_fresh": true,                     // when data is less than 24 hours old
 *     "data_age_hours": 12.5                  // age of data in hours
 *   },
 *   "near_candidates": [
 *     {"source":"google_places","id":1,"addr":"…","score":82},
 *     {"source":"google_addresses","id":9,"formatted_address":"…","score":78}
 *   ],
 *   "skipped_api_calls": true,               // when fresh data was found
 *   "reason": "Fresh data found (less than 24 hours old)"
 * }
 */

//////////////////////
// DB CONFIG
//////////////////////
$DB_HOST = '172.104.206.182';
$DB_USER = 'seattlelisted_usr';
$DB_PASS = 'T@5z6^pl}';
$DB_NAME = 'offta';
$DB_PORT = 3306;

dbg('DB config loaded (host='.$DB_HOST.' name='.$DB_NAME.' port='.$DB_PORT.')');

/** Create API call log table if missing. */
function ensure_api_call_log_table(mysqli $db): void {
  $sql = "CREATE TABLE IF NOT EXISTS api_call_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    endpoint VARCHAR(64) NOT NULL,
    status VARCHAR(64) NULL,
    url TEXT NULL,
    address TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_endpoint (endpoint),
    INDEX idx_status (status)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
  $db->query($sql);
}

/** Redact API key in URL if present. */
function redact_url_api_key(string $url): string {
  return preg_replace('~(key=)[^&]+~', '$1REDACTED', $url);
}

/** Insert a row into api_call_log. */
function log_api_call(mysqli $db, string $endpoint, string $url, ?string $status, ?string $address = null): void {
  try {
    ensure_api_call_log_table($db);
    $safeUrl = redact_url_api_key($url);
    if ($stmt = $db->prepare("INSERT INTO api_call_log (endpoint, status, url, address, created_at) VALUES (?, ?, ?, ?, NOW())")) {
      $stmt->bind_param('ssss', $endpoint, $status, $safeUrl, $address);
      $stmt->execute();
      $stmt->close();
    }
  } catch (Throwable $e) {
    // Swallow logging errors to avoid breaking main flow
  }
}

/** Get aggregate API call counts: today, last 7 days, last 30 days. */
function get_api_call_stats(mysqli $db): array {
  try {
    ensure_api_call_log_table($db);
    $stats = ['today' => 0, 'last_week' => 0, 'last_month' => 0];
    // Today
    if ($res = $db->query("SELECT COUNT(*) c FROM api_call_log WHERE created_at >= CURDATE()")) {
      $row = $res->fetch_assoc();
      $stats['today'] = (int)($row['c'] ?? 0);
      $res->free();
    }
    // Last 7 days (including today)
    if ($res = $db->query("SELECT COUNT(*) c FROM api_call_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")) {
      $row = $res->fetch_assoc();
      $stats['last_week'] = (int)($row['c'] ?? 0);
      $res->free();
    }
    // Last 30 days (including today)
    if ($res = $db->query("SELECT COUNT(*) c FROM api_call_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")) {
      $row = $res->fetch_assoc();
      $stats['last_month'] = (int)($row['c'] ?? 0);
      $res->free();
    }
    return $stats;
  } catch (Throwable $e) {
    return ['today' => 0, 'last_week' => 0, 'last_month' => 0];
  }
}

//////////////////////
// GOOGLE CONFIG
//////////////////////
// Load .env file if present
if (file_exists(__DIR__ . '/.env')) {
    foreach (file(__DIR__ . '/.env', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        if (strpos($line, '=') !== false) {
            list($k, $v) = explode('=', $line, 2);
            putenv(trim($k) . '=' . trim($v));
        }
    }
}

// Google API Key
$GOOGLE_API_KEY = getenv('GOOGLE_API_KEY') ?: 'AIzaSyDEej4ev5Yg1NvKKZhedRAY6RRpJa3HOEw';

dbg('API key '.($GOOGLE_API_KEY ? 'present' : 'missing'));

// Include API tracking
require_once __DIR__ . '/track_api_usage.php';

//////////////////////
// ACTION HANDLER: sync_place_ids
// Match google_places.Place_Id to google_addresses.place_id using google_addresses_id reference
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'sync_place_ids') {
  $mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
  if ($mysqli->connect_errno) {
    out_json(['ok'=>false, 'error'=>'DB connection failed: '.$mysqli->connect_error], 500);
  }
  $mysqli->set_charset('utf8mb4');
  dbg('ACTION sync_place_ids');

  $q = $mysqli->query("
    UPDATE google_addresses ga
    JOIN google_places gp ON gp.google_addresses_id = ga.id
    SET ga.place_id = gp.place_id
    WHERE (ga.place_id IS NULL OR ga.place_id = '')
      AND gp.place_id IS NOT NULL
      AND gp.place_id <> ''
  ");

  if (!$q) {
    out_json(['ok'=>false, 'error'=>'Update failed: '.$mysqli->error], 500);
  }

  out_json([
    'ok' => true,
    'action' => 'sync_place_ids',
    'updated_rows' => $mysqli->affected_rows
  ]);
}

//////////////////////
// ACTION HANDLER: reset_apartment_ga_ids_form (HTML confirmation UI)
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'reset_apartment_ga_ids_form') {
  header_remove('Content-Type');
  header('Content-Type: text/html; charset=utf-8');
  $self = htmlspecialchars(basename(__FILE()), ENT_QUOTES, 'UTF-8');
  echo "<!doctype html>\n<html><head><meta charset='utf-8'><title>Reset apartment_listings.google_addresses_id</title>";
  echo "<style>body{font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#0f1115;color:#e8eaed;padding:24px} .card{background:#181b21;border:1px solid #2a2f35;border-radius:8px;padding:18px;max-width:680px} .btn{background:#e74c3c;border:none;color:#0f1115;font-weight:700;padding:10px 16px;border-radius:6px;cursor:pointer} .btn:hover{background:#ff6b5a} a{color:#58a6ff;text-decoration:none} a:hover{text-decoration:underline}</style></head><body>";
  echo "<div class='card'>";
  echo "<h2>Reset apartment_listings.google_addresses_id</h2>";
  echo "<p>This will set <code>google_addresses_id</code> to <strong>NULL</strong> for <code>ALL</code> rows in <code>apartment_listings</code>. Use this only for debugging address matching.</p>";
  echo "<form method='post' action='{$self}?action=reset_apartment_ga_ids'>";
  echo "<input type='hidden' name='confirm' value='YES'>";
  echo "<button type='submit' class='btn'>Reset Now</button> &nbsp; <a href='{$self}?debug=1'>Cancel</a>";
  echo "</form>";
  echo "<p style='margin-top:16px'>API alternative: <code>{$self}?action=reset_apartment_ga_ids&amp;confirm=YES</code></p>";
  echo "</div></body></html>";
  exit;
}

//////////////////////
// ACTION HANDLER: reset_apartment_ga_ids
// Danger: Resets ALL apartment_listings.google_addresses_id to NULL/empty for debugging address matching
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'reset_apartment_ga_ids') {
  // Require explicit confirmation to avoid accidental mass update
  $confirm = isset($_POST['confirm']) ? trim((string)$_POST['confirm']) : (isset($_GET['confirm']) ? trim((string)$_GET['confirm']) : '');
  if (!in_array(strtoupper($confirm), ['YES', '1', 'TRUE'], true)) {
    out_json([
      'ok' => false,
      'action' => 'reset_apartment_ga_ids',
      'error' => 'Confirmation required. Pass confirm=YES to proceed.',
      'how_to' => basename(__FILE__) . '?action=reset_apartment_ga_ids&confirm=YES'
    ], 400);
  }

  $mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
  if ($mysqli->connect_errno) {
    out_json(['ok'=>false, 'error'=>'DB connection failed: '.$mysqli->connect_error], 500);
  }
  $mysqli->set_charset('utf8mb4');
  dbg('ACTION reset_apartment_ga_ids (confirmed)');

  // Normalize to NULL for any non-null/empty string values
  $sql = "UPDATE apartment_listings SET google_addresses_id = NULL WHERE google_addresses_id IS NOT NULL AND google_addresses_id <> ''";
  $ok = $mysqli->query($sql);
  if (!$ok) {
    out_json(['ok'=>false, 'action'=>'reset_apartment_ga_ids', 'error'=>'Update failed: '.$mysqli->error], 500);
  }

  out_json([
    'ok' => true,
    'action' => 'reset_apartment_ga_ids',
    'updated_rows' => $mysqli->affected_rows
  ]);
}

//////////////////////
// ACTION HANDLER: fill_ga_json
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'fill_ga_json') {
  // Validate ga_id (required) and place_id (optional)
  $ga_id = isset($_GET['ga_id']) && is_numeric($_GET['ga_id']) ? (int)$_GET['ga_id'] : null;
  $place_id = isset($_GET['place_id']) ? trim($_GET['place_id']) : null;
  if (!$ga_id) {
    out_json([
      'ok' => false,
      'error' => 'Missing required parameter: ga_id (int). Optionally provide place_id; if absent we will use google_addresses.place_id.'
    ], 400);
  }
  // Use only GOOGLE_API_KEY
  $api_key = $GOOGLE_API_KEY;
  if (!$api_key) {
    out_json([
      'ok' => false,
      'error' => 'Missing Google API key (set env GOOGLE_API_KEY)'
    ], 400);
  }
  // DB connect (reuse config)
  $mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
  if ($mysqli->connect_errno) {
    out_json(['ok'=>false, 'error'=>'DB connection failed: '.$mysqli->connect_error], 500);
  }
  $mysqli->set_charset('utf8mb4');
  dbg('ACTION fill_ga_json: ga_id='.$ga_id.', place_id='.($place_id ?: '[none]').' (debug='.($DEBUG_ON?'on':'off').')');
  dbg('DB connected OK; charset set to utf8mb4');
  // If place_id wasn't provided, try to get it from google_addresses
  if (!$place_id) {
    $rowPI = db_get_google_addresses_place_id_and_dump($mysqli, $ga_id);
    $place_id = $rowPI['place_id'] ?? null;
  }
  if (!$place_id) {
    out_json([
      'ok' => false,
      'error' => 'place_id is not provided and not found for this google_addresses row'
    ], 400);
  }
  // Check if already has json_dump
  $existing_json = db_get_google_addresses_json_dump($mysqli, $ga_id);
  if ($existing_json && trim($existing_json) !== '') {
    // Even if json_dump exists, ensure latitude/longitude are filled from it
    $latlng_result = fill_ga_latlng_if_missing($mysqli, $ga_id);
    dbg('fill_ga_latlng_if_missing (fill_ga_json early-exit): '.json_encode($latlng_result));
    out_json([
      'ok' => true,
      'action' => 'fill_ga_json',
      'google_addresses_id' => $ga_id,
      'place_id' => $place_id,
      'updated' => false,
      'reason' => 'already had json_dump',
      'latlng_autofill' => $latlng_result
    ]);
  }
  // Call Google Places Details API (FULL payload — ALL fields)
  $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
  $url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($place_id)
       .'&key='.rawurlencode($api_key)
       .'&language=en'
       .'&fields='.rawurlencode($all_fields);
  dbg('Calling Places Details (FULL): '.preg_replace('~key=[^&]+~','key=REDACTED',$url));
  $detailsJson = http_get_json($url);
  dbg('Places Details status='.( $detailsJson['status'] ?? 'null'));
  
  // Track API usage
  if (($detailsJson['status'] ?? '') === 'OK') {
    try {
      log_google_api_call($mysqli, 'places_details', 1, [
        'place_id' => $place_id,
        'ga_id' => $ga_id
      ]);
    } catch (Exception $e) {
      error_log("[API Track] Failed to log Places Details call: " . $e->getMessage());
    }
  }
  
  if (!$detailsJson) {
    out_json([
      'ok'=>false,
      'error'=>'Failed to fetch from Google Places Details API'
    ], 502);
  }
  if (($detailsJson['status'] ?? '') !== 'OK') {
    out_json([
      'ok'=>false,
      'error'=>'Google Places Details API error: '.($detailsJson['status'] ?? 'unknown'),
      'google_response'=>$detailsJson
    ], 502);
  }
  // Set json_dump if still empty
  $json_dump_payload = json_encode($detailsJson, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
  $update_result = db_set_google_addresses_json_dump_if_empty($mysqli, $ga_id, $json_dump_payload);
  dbg('db_set_google_addresses_json_dump_if_empty: updated='.(int)$update_result['updated'].' reason='.( $update_result['reason'] ?? 'null'));
  if (!$update_result['updated']) {
    // Check if the current value is whitespace-only and force an update in that case.
    $chk = $mysqli->prepare("SELECT json_dump FROM google_addresses WHERE id = ? LIMIT 1");
    if ($chk) {
      $chk->bind_param('i', $ga_id);
      $chk->execute();
      $rs = $chk->get_result();
      $rw = $rs?->fetch_assoc();
      $chk->close();
      $cur = $rw['json_dump'] ?? null;
      if ($cur !== null && trim($cur) === '') {
        $force = $mysqli->prepare("UPDATE google_addresses SET json_dump = ? WHERE id = ?");
        if ($force) {
          $force->bind_param('si', $json_dump_payload, $ga_id);
          $force->execute();
          $forced_rows = $force->affected_rows;
          $force->close();
          if ($forced_rows > 0) {
            $update_result = ['updated' => true, 'reason' => 'whitespace-only fixed by force update'];
          }
        }
      }
    }
  }
  // Auto-fill latitude/longitude from json_dump if missing
  $latlng_result = fill_ga_latlng_if_missing($mysqli, $ga_id);
  dbg('fill_ga_latlng_if_missing: '.json_encode($latlng_result));
  out_json([
    'ok'=>true,
    'action'=>'fill_ga_json',
    'google_addresses_id'=>$ga_id,
    'place_id'=>$place_id,
    'updated'=>$update_result['updated'],
    'reason'=>$update_result['reason'] ?? null,
    'mysql_error'=>isset($update_result['mysql_error']) ? $update_result['mysql_error'] : null
  ]);
}



//////////////////////
// ACTION HANDLER: refresh_ga_details_rated
// Updates json_dump (FULL Places Details) and latitude/longitude for ALL google_addresses rows
// that have a non-empty place_id AND non-null initial_review_rating AND non-null initial_review_count.
// This overwrites existing json_dump and coordinates with the latest Google data.
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'refresh_ga_details_rated') {
  if (!$GOOGLE_API_KEY) {
    out_json(['ok'=>false, 'error'=>'Missing Google API key (set env GOOGLE_API_KEY)'], 400);
  }

  $mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
  if ($mysqli->connect_errno) {
    out_json(['ok'=>false, 'error'=>'DB connection failed: '.$mysqli->connect_error], 500);
  }
  $mysqli->set_charset('utf8mb4');
  dbg('ACTION refresh_ga_details_rated');

  // Pull ALL candidates (no batching)
  $sql = "
    SELECT id, place_id
    FROM google_addresses
    WHERE place_id IS NOT NULL AND place_id <> ''
      AND initial_review_rating IS NOT NULL
      AND initial_review_count IS NOT NULL
    ORDER BY id ASC
  ";
  $res = $mysqli->query($sql);
  if (!$res) {
    out_json(['ok'=>false, 'error'=>'Select failed: '.$mysqli->error], 500);
  }

  // Prepare update statements (overwrite json_dump; set coords)
  $updDump = $mysqli->prepare("UPDATE google_addresses SET json_dump = ? WHERE id = ?");
  $updLL   = $mysqli->prepare("UPDATE google_addresses SET latitude = ?, longitude = ? WHERE id = ?");

  $processed = 0;
  $updated   = 0;
  $coord_upd = 0;
  $errors    = 0;
  $items     = [];

  while ($row = $res->fetch_assoc()) {
    $processed++;
    $ga_id = (int)$row['id'];
    $pid   = (string)$row['place_id'];

    // Fetch FULL Places Details (ALL fields)
    $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
    $url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid)
       .'&key='.rawurlencode($GOOGLE_API_KEY)
       .'&language=en'
       .'&fields='.rawurlencode($all_fields);
    dbg('refresh_ga_details_rated: GA='.$ga_id.' PID='.$pid.' URL='.preg_replace('~key=[^&]+~', 'key=REDACTED', $url));
    $details = http_get_json($url);
    $status  = $details['status'] ?? 'null';
    if (!$details || $status !== 'OK') {
      $errors++;
      $items[] = ['id'=>$ga_id,'place_id'=>$pid,'error'=>'google_details_'.$status];
      continue;
    }

    // Overwrite json_dump with full payload
    $payload = json_encode($details, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
    if ($updDump) {
      $updDump->bind_param('si', $payload, $ga_id);
      $updDump->execute();
      if ($updDump->affected_rows >= 0) { // treat as success even if contents identical
        $updated++;
      }
    } else {
      $errors++;
      $items[] = ['id'=>$ga_id,'place_id'=>$pid,'error'=>'prepare_update_dump_failed'];
      continue;
    }

    // Extract coords and overwrite latitude/longitude
    $lat = null; $lng = null;
    if (isset($details['result']['geometry']['location'])) {
      $lat = $details['result']['geometry']['location']['lat'] ?? null;
      $lng = $details['result']['geometry']['location']['lng'] ?? null;
    }
    if ($lat !== null && $lng !== null && $updLL) {
      $lat_d = (float)$lat;
      $lng_d = (float)$lng;
      $updLL->bind_param('ddi', $lat_d, $lng_d, $ga_id);
      $updLL->execute();
      if ($updLL->affected_rows >= 0) {
        $coord_upd++;
      }
    }

    $items[] = ['id'=>$ga_id,'place_id'=>$pid,'status'=>'ok','lat'=>$lat,'lng'=>$lng];
  }

  if ($updDump) $updDump->close();
  if ($updLL)   $updLL->close();
  $res->free();

  out_json([
    'ok' => true,
    'action' => 'refresh_ga_details_rated',
    'processed' => $processed,
    'json_dump_overwritten' => $updated,
    'coords_overwritten' => $coord_upd,
    'errors' => $errors,
    'items_sample' => array_slice($items, 0, 25)
  ]);
}

//////////////////////
// ACTION HANDLER: compare_place_ids
//////////////////////
if (isset($_GET['action']) && $_GET['action'] === 'compare_place_ids') {
  $pid1 = isset($_GET['pid1']) ? trim((string)$_GET['pid1']) : '';
  $pid2 = isset($_GET['pid2']) ? trim((string)$_GET['pid2']) : '';
  if ($pid1 === '' || $pid2 === '') {
    out_json(['ok'=>false, 'error'=>'Missing required params pid1 and pid2'], 400);
  }
  if (!$GOOGLE_API_KEY) {
    out_json(['ok'=>false, 'error'=>'Missing Google API key (set env GOOGLE_API_KEY)'], 400);
  }

  // FULL payloads for compare (ALL fields)
  $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
  $url1 = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid1)
       .'&key='.rawurlencode($GOOGLE_API_KEY)
       .'&language=en'
       .'&fields='.rawurlencode($all_fields);
  $url2 = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid2)
       .'&key='.rawurlencode($GOOGLE_API_KEY)
       .'&language=en'
       .'&fields='.rawurlencode($all_fields);
  dbg('COMPARE pid1 details (FULL): '.preg_replace('~key=[^&]+~','key=REDACTED',$url1));
  dbg('COMPARE pid2 details (FULL): '.preg_replace('~key=[^&]+~','key=REDACTED',$url2));

  $d1 = http_get_json($url1);
  $d2 = http_get_json($url2);
  $s1 = $d1['status'] ?? 'null';
  $s2 = $d2['status'] ?? 'null';
  dbg('COMPARE statuses: pid1='.$s1.' pid2='.$s2);
  if (!$d1 || !$d2 || $s1 !== 'OK' || $s2 !== 'OK') {
    out_json([
      'ok'=>false,
      'error'=>'Google Places Details error',
      'pid1_status'=>$s1,
      'pid2_status'=>$s2,
      'pid1_response'=>$d1,
      'pid2_response'=>$d2
    ], 502);
  }

  $r1 = $d1['result'] ?? [];
  $r2 = $d2['result'] ?? [];
  $obj1 = [
    'place_id'          => $r1['place_id'] ?? $pid1,
    'name'              => $r1['name'] ?? null,
    'formatted_address' => $r1['formatted_address'] ?? null,
    'lat'               => $r1['geometry']['location']['lat'] ?? null,
    'lng'               => $r1['geometry']['location']['lng'] ?? null,
    'types'             => $r1['types'] ?? [],
    'rating'            => isset($r1['rating']) ? (float)$r1['rating'] : null,
    'user_ratings_total'=> isset($r1['user_ratings_total']) ? (int)$r1['user_ratings_total'] : null,
    'url'               => $r1['url'] ?? null
  ];
  $obj2 = [
    'place_id'          => $r2['place_id'] ?? $pid2,
    'name'              => $r2['name'] ?? null,
    'formatted_address' => $r2['formatted_address'] ?? null,
    'lat'               => $r2['geometry']['location']['lat'] ?? null,
    'lng'               => $r2['geometry']['location']['lng'] ?? null,
    'types'             => $r2['types'] ?? [],
    'rating'            => isset($r2['rating']) ? (float)$r2['rating'] : null,
    'user_ratings_total'=> isset($r2['user_ratings_total']) ? (int)$r2['user_ratings_total'] : null,
    'url'               => $r2['url'] ?? null
  ];

  // Compare basics
  $same_name = (is_string($obj1['name']) && is_string($obj2['name']))
    ? (strcasecmp($obj1['name'], $obj2['name']) === 0)
    : null;
  $same_addr = (is_string($obj1['formatted_address']) && is_string($obj2['formatted_address']))
    ? (strcasecmp($obj1['formatted_address'], $obj2['formatted_address']) === 0)
    : null;

  // Distance (meters) if both coords exist
  $distance_m = null;
  if (is_numeric($obj1['lat']) && is_numeric($obj1['lng']) && is_numeric($obj2['lat']) && is_numeric($obj2['lng'])) {
    $distance_m = (int)round(haversine_km((float)$obj1['lat'], (float)$obj1['lng'], (float)$obj2['lat'], (float)$obj2['lng']) * 1000);
  }

  // Types overlap/diff
  $t1 = is_array($obj1['types']) ? $obj1['types'] : [];
  $t2 = is_array($obj2['types']) ? $obj2['types'] : [];
  $overlap = array_values(array_intersect($t1, $t2));
  $only1   = array_values(array_diff($t1, $t2));
  $only2   = array_values(array_diff($t2, $t1));

  $compare = [
    'same_name'             => $same_name,
    'same_formatted_address'=> $same_addr,
    'distance_meters'       => $distance_m,
    'rating_diff'           => ($obj1['rating'] !== null && $obj2['rating'] !== null) ? round($obj1['rating'] - $obj2['rating'], 2) : null,
    'user_ratings_diff'     => ($obj1['user_ratings_total'] !== null && $obj2['user_ratings_total'] !== null) ? ($obj1['user_ratings_total'] - $obj2['user_ratings_total']) : null,
    'types_overlap'         => $overlap,
    'types_only_pid1'       => $only1,
    'types_only_pid2'       => $only2
  ];

  out_json([
    'ok'      => true,
    'action'  => 'compare_place_ids',
    'pid1'    => $obj1,
    'pid2'    => $obj2,
    'compare' => $compare
  ]);
}


//////////////////////
// Helpers
//////////////////////
/**
 * Check if data is less than 24 hours old based on timestamp
 * @param int $timestamp Unix timestamp
 * @return bool True if data is less than 24 hours old
 */
function is_data_fresh(int $timestamp): bool {
  $current_time = time();
  $twenty_four_hours = 24 * 60 * 60; // 24 hours in seconds
  return ($current_time - $timestamp) < $twenty_four_hours;
}

/**
 * Check if google_addresses record exists and is fresh (less than 24 hours old)
 * @param mysqli $db Database connection
 * @param string $place_id Google place ID
 * @return array|null Returns record data if fresh, null if not found or stale
 */
function get_fresh_google_addresses_record(mysqli $db, string $place_id): ?array {
  $q = $db->prepare("SELECT id, place_id, source, building_name, latitude, longitude, initial_review_rating, initial_review_count, time, json_dump FROM google_addresses WHERE place_id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('s', $place_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  
  if (!$row) return null;
  
  // Check if data is fresh (less than 24 hours old)
  $record_time = (int)($row['time'] ?? 0);
  if (!is_data_fresh($record_time)) {
    dbg('Record found but data is stale (older than 24 hours): place_id='.$place_id.' time='.$record_time);
    return null;
  }
  
  dbg('Found fresh record (less than 24 hours old): place_id='.$place_id.' time='.$record_time);
  return $row;
}

/**
 * Haversine distance in kilometers between two lat/lng points.
 */
function haversine_km(float $lat1, float $lon1, float $lat2, float $lon2): float {
  $R = 6371.0088; // mean Earth radius (km)
  $dLat = deg2rad($lat2 - $lat1);
  $dLon = deg2rad($lon2 - $lon1);
  $a = sin($dLat/2) * sin($dLat/2) +
       cos(deg2rad($lat1)) * cos(deg2rad($lat2)) *
       sin($dLon/2) * sin($dLon/2);
  $c = 2 * atan2(sqrt($a), sqrt(1-$a));
  return $R * $c;
}

/**
 * If google_addresses.latitude/longitude are NULL/empty, parse from json_dump and update.
 * Supports Places Details (result.geometry.location) and Geocoding (geometry.location).
 * Returns ['updated'=>bool, 'lat'=>?float, 'lng'=>?float, 'reason'=>?string]
 */
function fill_ga_latlng_if_missing(mysqli $db, int $ga_id): array {
  dbg('fill_ga_latlng_if_missing:start ga_id='.$ga_id);
  $q = $db->prepare("SELECT latitude, longitude, json_dump FROM google_addresses WHERE id = ? LIMIT 1");
  if (!$q) return ['updated'=>false,'reason'=>'db prepare error'];
  $q->bind_param('i', $ga_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return ['updated'=>false,'reason'=>'not found'];

  $lat = $row['latitude'] ?? null;
  $lng = $row['longitude'] ?? null;
  if ($lat !== null && $lat !== '' && $lng !== null && $lng !== '') {
    return ['updated'=>false,'reason'=>'already has latitude/longitude'];
  }

  $json = $row['json_dump'] ?? '';
  if (!$json || trim($json) === '') return ['updated'=>false,'reason'=>'no json_dump'];
  $data = json_decode($json, true);
  if (!is_array($data)) return ['updated'=>false,'reason'=>'invalid json'];

  // Extract geometry.location from either Places Details or Geocode payload
  $loc = null;
  if (isset($data['result']['geometry']['location'])) {
    $loc = $data['result']['geometry']['location'];
  } elseif (isset($data['geometry']['location'])) {
    $loc = $data['geometry']['location'];
  }
  $lat_new = is_array($loc) && isset($loc['lat']) ? (float)$loc['lat'] : null;
  $lng_new = is_array($loc) && isset($loc['lng']) ? (float)$loc['lng'] : null;
  if ($lat_new === null || $lng_new === null) {
    return ['updated'=>false,'reason'=>'no geometry.location in json_dump'];
  }

  $u = $db->prepare("UPDATE google_addresses SET latitude = ?, longitude = ? WHERE id = ? AND (latitude IS NULL OR latitude='' OR longitude IS NULL OR longitude='')");
  if (!$u) return ['updated'=>false,'reason'=>'db prepare error'];
  $u->bind_param('ddi', $lat_new, $lng_new, $ga_id);
  $u->execute();
  $affected = $u->affected_rows;
  $u->close();

  dbg('fill_ga_latlng_if_missing:end ga_id='.$ga_id.' updated='.(int)($affected>0));
  return $affected > 0
    ? ['updated'=>true,'lat'=>$lat_new,'lng'=>$lng_new]
    : ['updated'=>false,'reason'=>'predicate false (columns not NULL/empty)'];
}
/**
 * If king_county_parcels.google_addresses_id is NULL/empty for $kc_id,
 * set it to $ga_id. Returns ['updated'=>bool, 'mysql_error'=>?string]
 */
function db_set_kc_google_addresses_if_empty(mysqli $db, int $kc_id, int $ga_id): array {
  $q = $db->prepare("UPDATE king_county_parcels SET google_addresses_id = ? WHERE id = ? AND (google_addresses_id IS NULL OR google_addresses_id = '')");
  if (!$q) return ['updated' => false, 'mysql_error' => $db->error ?: null];
  $q->bind_param('ii', $ga_id, $kc_id);
  $q->execute();
  $affected = $q->affected_rows;
  $err = $db->error;
  $q->close();
  return ['updated' => $affected > 0, 'mysql_error' => $err ?: null];
}

/**
 * Fetch json_dump for a google_addresses row by id.
 * @return ?string
 */
function db_get_google_addresses_json_dump(mysqli $db, int $ga_id): ?string {
  $q = $db->prepare("SELECT json_dump FROM google_addresses WHERE id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('i', $ga_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  return $row && isset($row['json_dump']) ? $row['json_dump'] : null;
}

/**
 * Fetch place_id and json_dump for a google_addresses row by id.
 * @return ?array{place_id:?string,json_dump:?string}
 */
function db_get_google_addresses_place_id_and_dump(mysqli $db, int $ga_id): ?array {
  $q = $db->prepare("SELECT place_id, json_dump FROM google_addresses WHERE id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('i', $ga_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return null;
  return [
    'place_id' => $row['place_id'] ?? null,
    'json_dump' => $row['json_dump'] ?? null,
  ];
}

/**
 * Set json_dump for google_addresses.id = $ga_id if json_dump is NULL or empty.
 * Returns ['updated'=>bool, 'reason'=>?string]
 */
function db_set_google_addresses_json_dump_if_empty(mysqli $db, int $ga_id, string $payload): array {
  // Check if already set
  $q = $db->prepare("SELECT json_dump FROM google_addresses WHERE id = ? LIMIT 1");
  if (!$q) return ['updated'=>false, 'reason'=>'db error'];
  $q->bind_param('i', $ga_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return ['updated'=>false, 'reason'=>'not found'];
  $existing = $row['json_dump'];
  if ($existing !== null && trim($existing) !== '') {
    return ['updated'=>false, 'reason'=>'already had json_dump'];
  }
  // Update
  $q2 = $db->prepare("UPDATE google_addresses SET json_dump = ? WHERE id = ? AND (json_dump IS NULL OR TRIM(json_dump) = '')");
  if (!$q2) return ['updated'=>false, 'reason'=>'db error'];
  $q2->bind_param('si', $payload, $ga_id);
  $q2->execute();
  $affected = $q2->affected_rows;
  $mysql_err = $db->error;
  $q2->close();
  return $affected > 0
    ? ['updated'=>true, 'reason'=>null]
    : ['updated'=>false, 'reason'=>'already had json_dump or predicate false', 'mysql_error' => $mysql_err ?: null];
}

/**
 * If google_addresses.json_dump is empty/whitespace for $ga_id, fetch Place Details by $place_id
 * and set json_dump. Returns ['attempted'=>bool,'updated'=>bool,'reason'=>?string].
 */
function fill_ga_json_if_missing(mysqli $db, int $ga_id, string $place_id, string $api_key): array {
  if (!$api_key) {
    return ['attempted' => false, 'updated' => false, 'reason' => 'no_api_key'];
  }
  
  // Check if we have fresh data (less than 24 hours old) for this place_id
  $fresh_record = get_fresh_google_addresses_record($db, $place_id);
  if ($fresh_record && $fresh_record['id'] == $ga_id) {
    return ['attempted' => false, 'updated' => false, 'reason' => 'data_is_fresh_less_than_24_hours'];
  }
  
  // If already filled, skip quickly
  $existing = db_get_google_addresses_json_dump($db, $ga_id);
  if ($existing !== null && trim($existing) !== '') {
    return ['attempted' => false, 'updated' => false, 'reason' => 'already_had_json_dump'];
  }
  // FULL payload — ALL fields
  $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
  $url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($place_id)
       .'&key='.rawurlencode($api_key)
       .'&language=en'
       .'&fields='.rawurlencode($all_fields);
  dbg('fill_ga_json_if_missing(ga_id='.$ga_id.', pid='.$place_id.')');
  dbg('Calling Places Details (helper FULL): '.preg_replace('~key=[^&]+~','key=REDACTED',$url));
  $details = http_get_json($url);
  dbg('Helper details status='.( $details['status'] ?? 'null'));
  if (!$details || ($details['status'] ?? '') !== 'OK') {
    return ['attempted' => true, 'updated' => false, 'reason' => 'google_details_error'];
  }
  $payload = json_encode($details, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
  $upd = db_set_google_addresses_json_dump_if_empty($db, $ga_id, $payload);
  dbg('Helper update result: '.json_encode($upd));
  if (!$upd['updated']) {
    // As in fill_ga_json action, force update on whitespace-only
    $chk = $db->prepare("SELECT json_dump FROM google_addresses WHERE id = ? LIMIT 1");
    if ($chk) {
      $chk->bind_param('i', $ga_id);
      $chk->execute();
      $rs = $chk->get_result();
      $rw = $rs?->fetch_assoc();
      $chk->close();
      $cur = $rw['json_dump'] ?? null;
      if ($cur !== null && trim($cur) === '') {
        $force = $db->prepare("UPDATE google_addresses SET json_dump = ? WHERE id = ?");
        if ($force) {
          $force->bind_param('si', $payload, $ga_id);
          $force->execute();
          $forced = $force->affected_rows > 0;
          $force->close();
          if ($forced) {
            // Auto-fill latitude/longitude from json_dump if missing (after force update)
            $latlng_result = fill_ga_latlng_if_missing($db, $ga_id);
            dbg('fill_ga_latlng_if_missing: '.json_encode($latlng_result));
            return ['attempted' => true, 'updated' => true, 'reason' => 'whitespace_force_update'];
          }
        }
      }
    }
  }
  // Auto-fill latitude/longitude from json_dump if missing
  $latlng_result = fill_ga_latlng_if_missing($db, $ga_id);
  dbg('fill_ga_latlng_if_missing: '.json_encode($latlng_result));
  return ['attempted' => true, 'updated' => (bool)$upd['updated'], 'reason' => $upd['reason'] ?? null];
}

/**
 * Returns google_addresses_id from google_places.id, or null if not found or column missing.
 * If column not found (SQL error 1054), catch and return null.
 */
function find_google_addresses_id_by_gp_id(mysqli $db, int $gpId): ?int {
  try {
    $q = $db->prepare("SELECT google_addresses_id FROM google_places WHERE id = ? LIMIT 1");
    if (!$q) return null;
    $q->bind_param('i', $gpId);
    $q->execute();
    $res = $q->get_result();
    $row = $res?->fetch_assoc();
    $q->close();
    if (!$row || !isset($row['google_addresses_id'])) return null;
    $val = $row['google_addresses_id'];
    if ($val === null) return null;
    return (int)$val;
  } catch (mysqli_sql_exception $ex) {
    if (isset($ex->getCode) && $ex->getCode() == 1054) return null;
    // Try to match error code for unknown column
    if (strpos($ex->getMessage(), 'Unknown column') !== false) return null;
    return null;
  }
}

/**
 * Returns id from google_addresses where place_id = ? LIMIT 1.
 */
function find_google_addresses_id_by_place_id(mysqli $db, string $placeId): ?int {
  $q = $db->prepare("SELECT id FROM google_addresses WHERE place_id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('s', $placeId);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  return $row ? (int)$row['id'] : null;
}

/**
 * Get king_county_parcels_id for a google_addresses row.
 * Returns int id or null if empty/missing.
 */
function db_get_kc_parcel_for_ga(mysqli $db, int $ga_id): ?int {
  $q = $db->prepare("SELECT king_county_parcels_id FROM google_addresses WHERE id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('i', $ga_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return null;
  $val = $row['king_county_parcels_id'] ?? null;
  if ($val === null || $val === '' ) return null;
  return (int)$val;
}

/**
 * Get king_county_parcels_id for a google_places row.
 * Returns int id or null if empty/missing.
 */
function db_get_kc_parcel_for_gp(mysqli $db, int $gp_id): ?int {
  $q = $db->prepare("SELECT king_county_parcels_id FROM google_places WHERE id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('i', $gp_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return null;
  $val = $row['king_county_parcels_id'] ?? null;
  if ($val === null || $val === '' ) return null;
  return (int)$val;
}

/**
 * Returns true if king_county_parcels.google_addresses_id is empty for the given KC row.
 * Returns null if the KC row is not found.
 */
function kc_google_addresses_empty(mysqli $db, int $kc_id): ?bool {
  $q = $db->prepare("SELECT google_addresses_id FROM king_county_parcels WHERE id = ? LIMIT 1");
  if (!$q) return null;
  $q->bind_param('i', $kc_id);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  if (!$row) return null;
  $val = $row['google_addresses_id'] ?? null;
  return ($val === null || $val === '');
}

/**
 * Update apartment_listings table with google_addresses_id
 * Returns ['updated' => bool, 'mysql_error' => ?string]
 */
function update_apartment_listings_google_addresses_id(mysqli $db, int $apartment_listings_id, int $google_addresses_id): array {
  // First check current value so we can treat "already linked" as success
  $sel = $db->prepare("SELECT google_addresses_id FROM apartment_listings WHERE id = ? LIMIT 1");
  if (!$sel) {
    return ['updated' => false, 'mysql_error' => $db->error ?: 'prepare_failed'];
  }
  $sel->bind_param('i', $apartment_listings_id);
  $sel->execute();
  $res = $sel->get_result();
  $row = $res?->fetch_assoc();
  $sel->close();

  if (!$row) {
    return ['updated' => false, 'mysql_error' => null, 'not_found' => true];
  }

  $current = $row['google_addresses_id'] ?? null;
  // Normalize empty string to null
  if ($current === '') { $current = null; }
  $currentInt = is_null($current) ? null : (int)$current;

  if ($currentInt !== null && $currentInt === (int)$google_addresses_id) {
    // Already set to this GA id — report as success so UI can show green check
    return [
      'updated' => true,
      'already_linked' => true,
      'previous_google_addresses_id' => $currentInt,
      'mysql_error' => null
    ];
  }

  // Perform update when different or currently empty
  $q = $db->prepare("UPDATE apartment_listings SET google_addresses_id = ? WHERE id = ?");
  if (!$q) return ['updated' => false, 'mysql_error' => $db->error ?: 'prepare_failed'];
  $q->bind_param('ii', $google_addresses_id, $apartment_listings_id);
  $q->execute();
  $affected = $q->affected_rows;
  $err = $db->error;
  $q->close();
  return [
    'updated' => $affected > 0,
    'updated_now' => $affected > 0,
    'previous_google_addresses_id' => $currentInt,
    'mysql_error' => $err ?: null
  ];
}

/**
 * Ensure a queued job exists for King County parcels lookup.
 * Returns ['inserted' => bool, 'existing_id' => ?int]
 */
function ensure_kc_job(mysqli $db, string $source_table, int $source_id, string $address_hint = ''): array {
  try {
    // Avoid duplicates: keep only one queued/running per (source_table, source_id)
    $q = $db->prepare("SELECT id FROM queue_websites WHERE source_table = ? AND source_id = ? AND status IN ('queued','running') LIMIT 1");
    if ($q) {
      $q->bind_param('si', $source_table, $source_id);
      $q->execute();
      $res = $q->get_result();
      if ($row = ($res?->fetch_assoc() ?: null)) {
        $qid = (int)$row['id'];
        $q->close();
        return ['inserted' => false, 'existing_id' => $qid];
      }
      $q->close();
    }
  } catch (mysqli_sql_exception $e) {
    // Table doesn't exist - skip queue job creation
    error_log("queue_websites table doesn't exist, skipping job creation: " . $e->getMessage());
    return ['inserted' => false, 'existing_id' => null];
  }

  // Insert a minimal job; parser can interpret link/the_css/address as needed
  $status = 'queued';
  $priority = 5;
  $link = $address_hint !== '' ? $address_hint : ('KC lookup for source_id='.$source_id);
  $the_css = 'king_county_parcels';

  try {
    $ins = $db->prepare("
      INSERT INTO queue_websites
        (status, link, the_css, priority, source_table, source_id, created_at, updated_at)
      VALUES
        (?, ?, ?, ?, ?, ?, NOW(), NOW())
    ");
    if ($ins) {
      $ins->bind_param('sssisi', $status, $link, $the_css, $priority, $source_table, $source_id);
      $ok = $ins->execute();
      $id = $ok ? (int)$ins->insert_id : null;
      $ins->close();
      return ['inserted' => (bool)$ok, 'existing_id' => $id];
    }
  } catch (mysqli_sql_exception $e) {
    // Table doesn't exist - skip queue job creation
    error_log("queue_websites table doesn't exist, skipping job insert: " . $e->getMessage());
    return ['inserted' => false, 'existing_id' => null];
  }
  return ['inserted' => false, 'existing_id' => null];
}
function out_json($arr, $code = 200) {
  global $DEBUG_ON, $DEBUG_LOG, $__FOP_T0;
  if (is_array($arr) && $DEBUG_ON) {
    $arr['_debug'] = [
      'elapsed_ms' => (int)round((microtime(true) - $__FOP_T0) * 1000),
      'log' => $DEBUG_LOG,
    ];
  }
  // Enrich with API call stats (today, last_week, last_month) if possible
  try {
    if (is_array($arr)) {
      $db = get_db_connection();
      $arr['api_call_stats'] = get_api_call_stats($db);
    }
  } catch (Throwable $e) {
    // ignore, keep original payload
  }
  $json = json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
  http_response_code($code);
  header_remove('Content-Type');
  header('Content-Type: application/json; charset=utf-8');
  echo $json;
  exit;
}

function fail($msg, $code = 400) {
  out_json(['ok' => false, 'error' => $msg], $code);
}

function ok($result_data, $final_ids = []) {
  $response = [
    'ok' => true,
    'result' => $result_data,
    'final_ids' => $final_ids
  ];
  out_json($response);
}

/**
 * Normalize addresses for loose matching:
 * - lowercase, trim
 * - remove unit/apt/suite numbers (#66, Apt 5, Unit B, Ste 210)
 * - expand a few common street abbreviations
 * - remove punctuation and spaces
 */
function normalize_address_strict(string $s): string {
  // Lowercase and trim
  $s = strtolower(trim($s));

  // Remove unit/apt/suite numbers (e.g., "#66", "Apt 5", "Unit B", "Ste 210")
  $s = preg_replace('~\b(?:apt|apartment|unit|ste|suite|#)\s*[a-z0-9\-]+~i', '', $s);

  // Remove country tokens that often appear in formatted addresses
  // e.g., ", United States", "USA", "U.S.", "US"
  $s = preg_replace('~\b(united\s*states|u\.s\.a\.|u\.s\.|usa|us)\b~', '', $s);

  // Normalize numeric ordinals to plain numbers (e.g., 9th -> 9, 21st -> 21)
  $s = preg_replace('~\b(\d+)(st|nd|rd|th)\b~', '$1', $s);

  // Normalize word ordinals to numbers (first->1, second->2, ...)
  // Keep common ones used in street names (1..20)
  $wordOrd = [
    'first'=>'1','second'=>'2','third'=>'3','fourth'=>'4','fifth'=>'5','sixth'=>'6','seventh'=>'7','eighth'=>'8','ninth'=>'9','tenth'=>'10',
    'eleventh'=>'11','twelfth'=>'12','thirteenth'=>'13','fourteenth'=>'14','fifteenth'=>'15','sixteenth'=>'16','seventeenth'=>'17','eighteenth'=>'18','nineteenth'=>'19','twentieth'=>'20'
  ];
  foreach ($wordOrd as $w => $n) {
    $s = preg_replace('~\b'.$w.'\b~', $n, $s);
  }

  // Expand common street abbreviations
  $map = [
    '~\bave\b~'  => 'avenue',
    '~\bav\b~'   => 'avenue',
    '~\bblvd\b~' => 'boulevard',
    '~\bst\b~'   => 'street',
    '~\brd\b~'   => 'road',
    '~\bdr\b~'   => 'drive',
    '~\bln\b~'   => 'lane',
    '~\bct\b~'   => 'court',
    '~\bter\b~'  => 'terrace',
    '~\bhwy\b~'  => 'highway',
    '~\bpkwy\b~' => 'parkway',
    '~\bpl\b~'   => 'place'
  ];
  foreach ($map as $k => $v) { $s = preg_replace($k, $v, $s); }

  // Remove punctuation and spaces
  $s = preg_replace('~[\s\.,#-]+~', '', $s);

  return $s;
}

/**
 * Additional normalization layer used only for similarity scoring.
 * Intent: ignore neutral differences like full street suffix words
 * ("street", "avenue", ...) and country tokens ("united states", "states").
 * Works safely on either raw or already-normalized strings.
 */
function normalize_for_similarity(string $s): string {
  // Base normalization first (safe to call even if already normalized)
  $s = normalize_address_strict($s);

  // Remove neutral tokens that inflate length without adding address signal
  // Note: normalize_address_strict() has already removed spaces/punctuation
  // and expanded common abbreviations, so we remove the long forms here.
  $neutral = [
    // Street-type words
    'street','avenue','road','boulevard','drive','lane','court','terrace','highway','parkway','place',
    // Country artifacts
    'unitedstates','states'
  ];
  $s = str_replace($neutral, '', $s);

  return $s;
}

function sim_score(string $a, string $b): int {
  // CRITICAL: Street numbers must match exactly - different numbers = different buildings!
  $num_a = extract_house_number($a);
  $num_b = extract_house_number($b);
  
  // If both have street numbers and they differ, return 0% similarity
  if ($num_a !== null && $num_b !== null && $num_a !== $num_b) {
    dbg("sim_score: REJECTING - Different street numbers: '$num_a' vs '$num_b' (from '$a' vs '$b')");
    return 0;
  }
  
  // Debias similarity by removing neutral tokens on both sides
  $a2 = normalize_for_similarity($a);
  $b2 = normalize_for_similarity($b);
  similar_text($a2, $b2, $pct);
  // Clamp to [0, 100]
  $pct = max(0.0, min(100.0, $pct));
  $result = (int)round($pct);
  
  if ($num_a !== null && $num_b !== null) {
    dbg("sim_score: street numbers match ('$num_a'), similarity={$result}% (from '$a' vs '$b')");
  }
  
  return $result;
}

/** Extract 5-digit ZIP code from an address string, if present */
function extract_zip_from_address(string $s): ?string {
  if (preg_match('~\b(\d{5})(?:-\d{4})?\b~', $s, $m)) {
    return $m[1];
  }
  return null;
}

/** Extract leading house number from an address string, if present */
function extract_house_number(string $s): ?string {
  if (preg_match('~^\s*(\d+)\b~', $s, $m)) {
    return $m[1];
  }
  return null;
}

/** Map various street suffixes to a canonical short form */
function canonical_suffix(string $s): string {
  $s = strtolower($s);
  $map = [
    'avenue' => 'ave', 'ave' => 'ave', 'av' => 'ave',
    'street' => 'st', 'st' => 'st',
    'boulevard' => 'blvd', 'blvd' => 'blvd',
    'road' => 'rd', 'rd' => 'rd',
    'drive' => 'dr', 'dr' => 'dr',
    'lane' => 'ln', 'ln' => 'ln',
    'court' => 'ct', 'ct' => 'ct',
    'terrace' => 'ter', 'ter' => 'ter',
    'highway' => 'hwy', 'hwy' => 'hwy',
    'parkway' => 'pkwy', 'pkwy' => 'pkwy',
    'place' => 'pl', 'pl' => 'pl'
  ];
  return $map[$s] ?? $s;
}

/** Normalize ordinal tokens (e.g., 9th->9, third->3) for route key */
function normalize_ordinal_token(string $tok): string {
  $t = strtolower($tok);
  if (preg_match('~^(\d+)(st|nd|rd|th)$~i', $t, $m)) {
    return $m[1];
  }
  $wordOrd = [
    'first'=>'1','second'=>'2','third'=>'3','fourth'=>'4','fifth'=>'5','sixth'=>'6','seventh'=>'7','eighth'=>'8','ninth'=>'9','tenth'=>'10',
    'eleventh'=>'11','twelfth'=>'12','thirteenth'=>'13','fourteenth'=>'14','fifteenth'=>'15','sixteenth'=>'16','seventeenth'=>'17','eighteenth'=>'18','nineteenth'=>'19','twentieth'=>'20'
  ];
  return $wordOrd[$t] ?? $t;
}

/** Extract N/E/S/W direction letter when present (before or after suffix) */
function extract_direction_letter(string $s): ?string {
  // Prefer standalone single-letter tokens
  if (preg_match('~\b([NnEeSsWw])\b~', $s, $m)) {
    return strtoupper($m[1]);
  }
  // Spell-outs
  if (preg_match('~\b(north|south|east|west)\b~i', $s, $m)) {
    $map = ['north'=>'N','south'=>'S','east'=>'E','west'=>'W'];
    $k = strtolower($m[1]);
    return $map[$k] ?? null;
  }
  return null;
}

/** Extract a simple route key like "13 ave" or "james st" from an address */
function extract_route_key(string $s): ?string {
  $str = trim($s);
  // Remove leading number for easier patterning
  $str_wo_num = preg_replace('~^\s*\d+\s+~', '', $str);

  // Try pattern: <name> <suffix> [direction?]
  if (preg_match('~^([A-Za-z0-9]+)\s+([A-Za-z\.]+)\b~', $str_wo_num, $m)) {
    $name = normalize_ordinal_token($m[1]);
    $suf  = canonical_suffix($m[2]);
    return strtolower($name.' '.$suf);
  }
  return null;
}

/** Extract "formatted_address" quick from google_addresses.json_dump */
function extract_formatted_address_from_json_dump(?string $jsonDump): ?string {
  if (!$jsonDump) return null;
  if (preg_match('~"formatted_address"\s*:\s*"([^"]+)"~i', $jsonDump, $m)) {
    return $m[1];
  }
  return null;
}

/**
 * Search google_addresses.json_dump for a potential close match to the given address
 * and return the row if the record is fresh (less than 24 hours old) and similar.
 * Returns the DB row array or null.
 */
function find_potential_fresh_record_by_address(mysqli $db, string $address, string $needleNorm): ?array {
  // Short prefix to search within json_dump
  $short = $address;
  if (strpos($short, ',') !== false) $short = substr($short, 0, strpos($short, ','));
  $short = trim($short);
  if ($short === '') $short = $address;

  $best = null; // will hold the freshest candidate (smallest age)
  $best_age_hours = PHP_FLOAT_MAX;

  // Extract constraints from the input address
  $input_zip = extract_zip_from_address($address);
  $input_house = extract_house_number($address);
  $input_dir = extract_direction_letter($address);
  $input_route = extract_route_key($address);

  if ($selGA = $db->prepare("SELECT id, place_id, source, building_name, latitude, longitude, initial_review_rating, initial_review_count, time, json_dump FROM google_addresses WHERE json_dump LIKE CONCAT('%', ?, '%') LIMIT 200")) {
    $selGA->bind_param("s", $short);
    if ($selGA->execute()) {
      $res = $selGA->get_result();
      while ($row = ($res ? $res->fetch_assoc() : null)) {
        $fmt = extract_formatted_address_from_json_dump($row['json_dump'] ?? null);
        if (!$fmt) continue;
        // Hard constraints: ZIP, house number, direction, and route must match when present on both sides
        $fmt_zip = extract_zip_from_address($fmt);
        if ($input_zip !== null && $fmt_zip !== null && $input_zip !== $fmt_zip) {
          continue;
        }
        $fmt_house = extract_house_number($fmt);
        if ($input_house !== null && $fmt_house !== null && $input_house !== $fmt_house) {
          continue;
        }
        $fmt_dir = extract_direction_letter($fmt);
        if ($input_dir !== null && $fmt_dir !== null && $input_dir !== $fmt_dir) {
          continue;
        }
        $fmt_route = extract_route_key($fmt);
        if ($input_route !== null && $fmt_route !== null && $input_route !== $fmt_route) {
          continue;
        }
        $fmtNorm = normalize_address_strict($fmt);
        $score = sim_score($needleNorm, $fmtNorm);

        // require high similarity to consider it a match
        if ($score < 90) continue;

        $record_time = (int)($row['time'] ?? 0);
        $age_seconds = time() - $record_time;
        if ($age_seconds < 0) $age_seconds = 0; // future timestamps guard
        $age_hours = $age_seconds / 3600.0;

        // Only accept records younger than 24 hours
        if ($age_hours <= 24.0) {
          if ($age_hours < $best_age_hours) {
            $best_age_hours = $age_hours;
            $row['_data_age_hours'] = round($age_hours, 2);
            $row['_similarity_score'] = $score;
            $best = $row;
          }
        }
      }
      $res?->free();
    }
    $selGA->close();
  }
  // If we picked a candidate from the quick prefix-LIKE pass, return it now.
  if ($best) {
    dbg('find_potential_fresh_record_by_address: selected place_id=' . ($best['place_id'] ?? 'null') . ' age_hours=' . ($best['_data_age_hours'] ?? 'null') . ' score=' . ($best['_similarity_score'] ?? 'null'));
    return $best;
  }

  // SECOND PASS: If the LIKE-based search found nothing, scan recent google_addresses rows (last 24h)
  // and compute similarity against their extracted formatted_address. This catches cases where
  // the json_dump doesn't contain the short prefix used above but the record is still a close match.
  dbg('find_potential_fresh_record_by_address: no candidate from prefix-LIKE; performing recent-rows second-pass');
  $recent_limit = 500; // cap to avoid scanning entire table
  $cutoff_ts = time() - 24 * 3600;
  if ($sel2 = $db->prepare("SELECT id, place_id, source, building_name, latitude, longitude, initial_review_rating, initial_review_count, time, json_dump FROM google_addresses WHERE time >= ? ORDER BY time DESC LIMIT ?")) {
    $sel2->bind_param('ii', $cutoff_ts, $recent_limit);
    if ($sel2->execute()) {
      $res2 = $sel2->get_result();
      while ($row = ($res2 ? $res2->fetch_assoc() : null)) {
        $fmt = extract_formatted_address_from_json_dump($row['json_dump'] ?? null);
        if (!$fmt) continue;
        // Hard constraints: ZIP, house number, direction, and route must match when present on both sides
        $fmt_zip = extract_zip_from_address($fmt);
        if ($input_zip !== null && $fmt_zip !== null && $input_zip !== $fmt_zip) {
          continue;
        }
        $fmt_house = extract_house_number($fmt);
        if ($input_house !== null && $fmt_house !== null && $input_house !== $fmt_house) {
          continue;
        }
        $fmt_dir = extract_direction_letter($fmt);
        if ($input_dir !== null && $fmt_dir !== null && $input_dir !== $fmt_dir) {
          continue;
        }
        $fmt_route = extract_route_key($fmt);
        if ($input_route !== null && $fmt_route !== null && $input_route !== $fmt_route) {
          continue;
        }
        $fmtNorm = normalize_address_strict($fmt);
        $score = sim_score($needleNorm, $fmtNorm);
        if ($score < 90) continue; // require high similarity in second pass too
        $record_time = (int)($row['time'] ?? 0);
        $age_seconds = time() - $record_time;
        if ($age_seconds < 0) $age_seconds = 0;
        $age_hours = $age_seconds / 3600.0;
        if ($age_hours <= 24.0) {
          if ($age_hours < $best_age_hours) {
            $best_age_hours = $age_hours;
            $row['_data_age_hours'] = round($age_hours, 2);
            $row['_similarity_score'] = $score;
            $best = $row;
          }
        }
      }
      $res2?->free();
    }
    $sel2->close();
  }
  if ($best) {
    dbg('find_potential_fresh_record_by_address (second-pass): selected place_id=' . ($best['place_id'] ?? 'null') . ' age_hours=' . ($best['_data_age_hours'] ?? 'null') . ' score=' . ($best['_similarity_score'] ?? 'null'));
  }
  return $best;
}

function http_get_json(string $url): ?array {
  $ch = curl_init($url);
  curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => 1,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT => 20,
  ]);
  $raw = curl_exec($ch);
  $err = curl_error($ch);
  // Gather info before closing
  $info = @curl_getinfo($ch);
  curl_close($ch);
  if ($raw === false || $raw === null) {
    // Log a failed attempt with status null
    try {
      $db = get_db_connection();
      // Derive endpoint and address from URL
      $endpoint = (strpos($url, 'findplacefromtext') !== false) ? 'findplacefromtext'
        : ((strpos($url, 'place/details') !== false) ? 'place_details'
          : ((strpos($url, 'geocode') !== false) ? 'geocode' : 'unknown'));
      $addr = null;
      if ($parts = parse_url($url)) {
        $qs = [];
        if (isset($parts['query'])) parse_str($parts['query'], $qs);
        $addr = $qs['input'] ?? ($qs['address'] ?? null);
        if (is_string($addr)) $addr = urldecode($addr);
      }
      log_api_call($db, $endpoint, $url, null, $addr);
    } catch (Throwable $e) { /* ignore */ }
    return null;
  }
  $j = json_decode($raw, true);
  // Log API call (success or error status)
  try {
    $db = get_db_connection();
    $endpoint = (strpos($url, 'findplacefromtext') !== false) ? 'findplacefromtext'
      : ((strpos($url, 'place/details') !== false) ? 'place_details'
        : ((strpos($url, 'geocode') !== false) ? 'geocode' : 'unknown'));
    $status = is_array($j) ? ($j['status'] ?? null) : null;
    $addr = null;
    if ($parts = parse_url($url)) {
      $qs = [];
      if (isset($parts['query'])) parse_str($parts['query'], $qs);
      $addr = $qs['input'] ?? ($qs['address'] ?? null);
      if (is_string($addr)) $addr = urldecode($addr);
    }
    log_api_call($db, $endpoint, $url, is_string($status) ? $status : null, $addr);
  } catch (Throwable $e) { /* ignore logging errors */ }
  return is_array($j) ? $j : null;
}

/**
 * Score a Places "Find Place From Text" candidate.
 * Priority:
 *  - types contains BOTH point_of_interest AND establishment (+100)
 *  - types contains point_of_interest (+50)
 *  - rating >= 4.0 (+10)
 *  - user_ratings_total bucket (min(40, floor(ln(n+1)*10))) to nudge popular places
 */
function score_places_candidate(array $c): int {
  $score = 0;
  $types = isset($c['types']) && is_array($c['types']) ? $c['types'] : [];
  $hasPoi  = in_array('point_of_interest', $types, true);
  $hasEst  = in_array('establishment', $types, true);

  if ($hasPoi && $hasEst) {
    $score += 100;
  } elseif ($hasPoi) {
    $score += 50;
  }

  if (isset($c['rating']) && is_numeric($c['rating']) && (float)$c['rating'] >= 4.0) {
    $score += 10;
  }

  $urt = isset($c['user_ratings_total']) ? (int)$c['user_ratings_total'] : 0;
  if ($urt > 0) {
    // Gentle bump for popularity
    $score += (int)min(40, floor(log($urt + 1) * 10));
  }

  return $score;
}

function find_existing_google_places_id(mysqli $db, string $placeId): ?int {
  $q = $db->prepare("SELECT id FROM google_places WHERE place_id = ? LIMIT 1");
  if (!$q) throw new RuntimeException("Prepare failed: ".$db->error);
  $q->bind_param('s', $placeId);
  $q->execute();
  $res = $q->get_result();
  $row = $res?->fetch_assoc();
  $q->close();
  return $row ? (int)$row['id'] : null;
}

function find_existing_google_addresses_id(mysqli $db, string $placeId): ?int {
  $fresh_record = get_fresh_google_addresses_record($db, $placeId);
  return $fresh_record ? (int)$fresh_record['id'] : null;
}


//////////////////////
// Helper: Insert into google_addresses with full payload
//////////////////////
/**
 * Insert a new row into google_addresses with full Places/Geocode payload.
 * $src should be 'places' or 'geocode'.
 * Returns ['ok'=>bool,'id'=>?int,'mysql_error'=>?string]
 */
function db_insert_google_addresses(mysqli $db, string $place_id, string $src, ?string $building_name, ?float $lat, ?float $lng, ?float $initial_rating, ?int $initial_count, array $full_payload): array {
  // Check if place_id already exists
  $check_stmt = $db->prepare("SELECT id FROM google_addresses WHERE place_id = ?");
  if ($check_stmt) {
    $check_stmt->bind_param('s', $place_id);
    $check_stmt->execute();
    $check_stmt->bind_result($existing_id);
    if ($check_stmt->fetch()) {
      // Place ID already exists, return existing ID
      $check_stmt->close();
      return ['ok'=>true, 'id'=>$existing_id, 'mysql_error'=>null, 'already_exists'=>true];
    }
    $check_stmt->close();
  }
  
  $ts = time();
  $json = json_encode($full_payload, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
  $stmt = $db->prepare("
    INSERT INTO google_addresses
      (place_id, source, king_county_parcels_id, time, building_name, initial_review_rating, initial_review_count, latitude, longitude, json_dump)
    VALUES
      (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
  ");
  if (!$stmt) {
    return ['ok'=>false, 'id'=>null, 'mysql_error'=>$db->error ?: 'prepare_failed'];
  }
  // Bind types: s (place_id), s (source), i (time), s (building_name), d (initial_rating), i (initial_count), d (lat), d (lng), s (json_dump)
  $stmt->bind_param(
    'ssisdidds',
    $place_id,
    $src,
    $ts,
    $building_name,
    $initial_rating,
    $initial_count,
    $lat,
    $lng,
    $json
  );
  $ok = $stmt->execute();
  $err = $db->error;
  $newId = $ok ? (int)$stmt->insert_id : null;
  $stmt->close();
  return ['ok'=>(bool)$ok, 'id'=>$newId, 'mysql_error'=>$ok ? null : ($err ?: 'insert_failed')];
}

//////////////////////
// Main
//////////////////////
$address = isset($_GET['address']) ? trim((string)$_GET['address']) : '';
$place_id_hint = isset($_GET['place_id']) ? trim((string)$_GET['place_id']) : '';
$existing_google_places_id = isset($_GET['google_places_id']) && is_numeric($_GET['google_places_id']) ? (int)$_GET['google_places_id'] : null;

if ($address === '' && $place_id_hint === '') {
  fail("Missing required query param: address or place_id");
}

$region = isset($_GET['region']) ? trim((string)$_GET['region']) : 'us';
$apartment_listings_id = isset($_GET['apartment_listings_id']) && is_numeric($_GET['apartment_listings_id']) ? (int)$_GET['apartment_listings_id'] : null;

if ($existing_google_places_id) {
  dbg('INPUT existing_google_places_id='.$existing_google_places_id.' (will link new google_addresses to this)');
}
$needleNorm = $address !== '' ? normalize_address_strict($address) : '';
$near = [];
$gaNear = [];

if ($place_id_hint !== '') {
  dbg('INPUT place_id="'.$place_id_hint.'"'.($address !== '' ? ', address="'.$address.'"' : ''));
} else {
  dbg('INPUT address="'.$address.'", region="'.$region.'"');
}

$mysqli = get_db_connection();

$mysqli->set_charset('utf8mb4');
dbg('Main DB connected OK');

//////////////////////////////
// (A0) PLACE ID DIRECT LOOKUP (if provided)
//////////////////////////////
// If a place_id is provided, skip address matching and go directly to lookup/refresh
if ($place_id_hint !== '') {
  // Check if we already have this place_id in google_addresses
  $stmt = $mysqli->prepare("SELECT id, place_id, json_dump, NULL as ts FROM google_addresses WHERE place_id = ? ORDER BY id DESC LIMIT 1");
  $stmt->bind_param("s", $place_id_hint);
  $stmt->execute();
  $res = $stmt->get_result();
  $existing = $res->fetch_assoc();
  $stmt->close();
  
  if ($existing) {
    $age_hours = (time() - (int)$existing['ts']) / 3600.0;
    $ga_id = (int)$existing['id'];
    
    // If data is fresh (< 24 hours), return it
    if ($age_hours < 24) {
      dbg("Found fresh place_id data (age={$age_hours}h), returning existing record ga_id={$ga_id}");
      $json_dump = $existing['json_dump'];
      if ($json_dump) {
        $data = json_decode($json_dump, true);
        if ($data) {
          // Always update apartment_listings.google_addresses_id if apartment_listings_id is provided
          $apartment_listings_update = null;
          if ($apartment_listings_id && $ga_id) {
            $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $ga_id);
            dbg('apartment_listings update (place_id direct): '.json_encode($apartment_listings_update));
          }
          ok([
            'source' => 'google_addresses',
            'id' => $ga_id,
            'place_id' => $existing['place_id'],
            'name' => $data['name'] ?? null,
            'formatted_address' => $data['formatted_address'] ?? null,
            'lat' => $data['geometry']['location']['lat'] ?? null,
            'lng' => $data['geometry']['location']['lng'] ?? null,
            'rating' => isset($data['rating']) ? number_format($data['rating'], 2) : null,
            'user_ratings_total' => $data['user_ratings_total'] ?? null,
            'data_fresh' => true,
            'data_age_hours' => round($age_hours, 1),
            'apartment_listings_id' => $apartment_listings_id,
          ], [
            'google_addresses_id' => $ga_id,
            'google_places_id' => null,
            'king_county_parcels_id' => null,
            'apartment_listings_update' => $apartment_listings_update,
            'apartment_listings_id' => $apartment_listings_id,
          ]);
        }
      }
    }
    
    // Data exists but is stale, refresh it
    dbg("Found stale place_id data (age={$age_hours}h), refreshing via Place Details API");
    $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
    $url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($place_id_hint)
         .'&key='.rawurlencode($GOOGLE_API_KEY)
         .'&language=en'
         .'&fields='.rawurlencode($all_fields);
    dbg('Calling Places Details (stale refresh): '.preg_replace('~key=[^&]+~','key=REDACTED',$url));
    $details = http_get_json($url);
    dbg('Places Details status='.( $details['status'] ?? 'null'));
    
    if ($details && isset($details['result'])) {
      $result = $details['result'];
      // Update the existing record
      $json_enc = json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
      $update = $mysqli->prepare("UPDATE google_addresses SET json_dump = ? WHERE id = ?");
      $update->bind_param("si", $json_enc, $ga_id);
      $update->execute();
      $update->close();
      
      dbg("Updated google_addresses id={$ga_id} with fresh Place Details data");
      
      ok([
        'source' => 'google_addresses',
        'id' => $ga_id,
        'place_id' => $place_id_hint,
        'name' => $result['name'] ?? null,
        'formatted_address' => $result['formatted_address'] ?? null,
        'lat' => $result['geometry']['location']['lat'] ?? null,
        'lng' => $result['geometry']['location']['lng'] ?? null,
        'rating' => isset($result['rating']) ? number_format($result['rating'], 2) : null,
        'user_ratings_total' => $result['user_ratings_total'] ?? null,
        'data_fresh' => true,
        'data_age_hours' => 0,
      ], [
        'google_addresses_id' => $ga_id,
        'google_places_id' => null,
        'king_county_parcels_id' => null,
      ]);
    }
  } else {
    // No existing record, fetch from Place Details and insert
    dbg("No existing record for place_id={$place_id_hint}, fetching from Place Details API");
    $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
    $url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($place_id_hint)
         .'&key='.rawurlencode($GOOGLE_API_KEY)
         .'&language=en'
         .'&fields='.rawurlencode($all_fields);
    dbg('Calling Places Details (new record): '.preg_replace('~key=[^&]+~','key=REDACTED',$url));
    $details = http_get_json($url);
    dbg('Places Details status='.( $details['status'] ?? 'null'));
    
    if ($details && isset($details['result'])) {
      $result = $details['result'];
      $json_enc = json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
      
      $insert = $mysqli->prepare("INSERT INTO google_addresses (place_id, json_dump) VALUES (?, ?)");
      $insert->bind_param("ss", $place_id_hint, $json_enc);
      $insert->execute();
      $new_ga_id = $insert->insert_id;
      $insert->close();
      
      dbg("Inserted new google_addresses id={$new_ga_id} for place_id={$place_id_hint}");
      
      ok([
        'source' => 'google_addresses',
        'id' => $new_ga_id,
        'place_id' => $place_id_hint,
        'name' => $result['name'] ?? null,
        'formatted_address' => $result['formatted_address'] ?? null,
        'lat' => $result['geometry']['location']['lat'] ?? null,
        'lng' => $result['geometry']['location']['lng'] ?? null,
        'rating' => isset($result['rating']) ? number_format($result['rating'], 2) : null,
        'user_ratings_total' => $result['user_ratings_total'] ?? null,
        'data_fresh' => true,
        'data_age_hours' => 0,
      ], [
        'google_addresses_id' => $new_ga_id,
        'google_places_id' => null,
        'king_county_parcels_id' => null,
      ]);
    } else {
      fail("Place Details API returned no result for place_id={$place_id_hint}");
    }
  }
  
  // If we get here, something went wrong
  fail("Failed to process place_id={$place_id_hint}");
}

//////////////////////////////
// (A0) DB-FIRST EXACT MATCH (no API needed)
//////////////////////////////
// A "real match" is when the address text matches an existing row and we can return an
// existing google_places or google_addresses id. We attempt exact equality on a normalized
// address basis (lowercased, unit numbers removed, street abbrev expanded, punctuation removed).

$exactFound = null;

// 1) Try google_places.Fulladdress
if ($sel = $mysqli->prepare("SELECT id, place_id, Fulladdress FROM google_places WHERE Fulladdress LIKE CONCAT('%', ?, '%') LIMIT 200")) {
  $prefix = substr($address, 0, 20);
  $sel->bind_param("s", $prefix);
  if ($sel->execute()) {
    $res = $sel->get_result();
    while ($row = ($res ? $res->fetch_assoc() : null)) {
      $fa = $row['Fulladdress'] ?? '';
      if ($fa === '') continue;
      if (normalize_address_strict($fa) === $needleNorm) {
        $exactFound = [
          'source'            => 'google_places',
          'id'                => (int)$row['id'],
          'full_address'      => $fa,
          'normalized_input'  => $needleNorm,
          'normalized_match'  => normalize_address_strict($fa),
          'similarity'        => 100
        ];
        // Attach google_addresses linkage + json_dump status if available
        $gp_id_for_link = (int)$row['id'];
        $ga_id_link = find_google_addresses_id_by_gp_id($mysqli, $gp_id_for_link);
        if ($ga_id_link === null && isset($row['place_id']) && $row['place_id'] !== '') {
          $ga_id_link = find_google_addresses_id_by_place_id($mysqli, $row['place_id']);
        }
        dbg('Exact match via google_places id='.$row['id'].' place_id='.($row['place_id'] ?? ''));
        if ($ga_id_link !== null) {
          dbg('Linked GA id='.($ga_id_link ?? 'null'));
          $ga_info = db_get_google_addresses_place_id_and_dump($mysqli, $ga_id_link) ?: ['place_id'=>null,'json_dump'=>null];
          $ga_place_id = $ga_info['place_id'] ?? null;
          $dump = $ga_info['json_dump'] ?? null;
          $exactFound['google_addresses'] = [
            'google_addresses_id' => $ga_id_link,
            'place_id'            => $ga_place_id,
            'has_json_dump'       => (bool)($dump !== null && trim($dump) !== '')
          ];

          // Auto-fill google_addresses.json_dump if missing and we have API key; prefer GA place_id
          if ($GOOGLE_API_KEY) {
            $pid_for_fill = $ga_place_id ?: ($row['place_id'] ?? '');
            if ($pid_for_fill && !$exactFound['google_addresses']['has_json_dump']) {
              $autoFill = fill_ga_json_if_missing($mysqli, $ga_id_link, $pid_for_fill, $GOOGLE_API_KEY);
              dbg('Auto-filled GA json_dump for id='.$ga_id_link.' updated='.(int)($autoFill['updated'] ?? 0).' reason='.($autoFill['reason'] ?? ''));
              $dump2 = db_get_google_addresses_json_dump($mysqli, $ga_id_link);
              $exactFound['google_addresses']['has_json_dump'] = (bool)($dump2 !== null && trim($dump2) !== '');
              $exactFound['google_addresses_autofill'] = $autoFill;
            }
          }
          // Ensure latitude/longitude are filled from json_dump if missing
          $latlng_result = fill_ga_latlng_if_missing($mysqli, (int)$ga_id_link);
          dbg('fill_ga_latlng_if_missing (A0 GP path): '.json_encode($latlng_result));
        }
        // King County parcels: check GP first, then GA; enqueue job if missing
        $kc_id_gp = db_get_kc_parcel_for_gp($mysqli, $gp_id_for_link);
        $kc_id_ga = ($ga_id_link !== null) ? db_get_kc_parcel_for_ga($mysqli, $ga_id_link) : null;
        $kc_id = $kc_id_gp ?? $kc_id_ga;

        $enq = null;
        if ($kc_id === null) {
          $use_source_id = ($ga_id_link !== null) ? $ga_id_link : $gp_id_for_link;
          $enq = ensure_kc_job($mysqli, 'king_county_parcels', $use_source_id, $fa);
        }
        if ($kc_id !== null) {
          $exactFound['king_county_parcels'] = (int)$kc_id;
        } else {
          $exactFound['king_county_parcels'] = (object)[];
        }
        // If KC row exists but has empty google_addresses_id, set it to the matched GA id
        if ($kc_id !== null && isset($ga_id_link) && $ga_id_link !== null) {
          dbg('Attempt KC link update: kc_id='.(int)$kc_id.' set GA='.(int)$ga_id_link);
          $kc_empty = kc_google_addresses_empty($mysqli, $kc_id);
          if ($kc_empty === true) {
            $kcUpd = db_set_kc_google_addresses_if_empty($mysqli, (int)$kc_id, (int)$ga_id_link);
            dbg('KC update result: '.json_encode($kcUpd));
            $exactFound['king_county_parcels_google_addresses_update'] = $kcUpd;
            // Recheck after update
            $kc_empty = kc_google_addresses_empty($mysqli, $kc_id);
          }
          if ($kc_empty === true) {
            $exactFound['king_county_parcels_google_addresses_empty'] = true;
          }
        }
        break;
      }
    }
    $res?->free();
  }
  $sel->close();
}

// 2) If not found, try google_addresses by formatted_address in json_dump
if (
  !$exactFound &&
  ($selGA = $mysqli->prepare("SELECT id, place_id, json_dump FROM google_addresses WHERE json_dump LIKE CONCAT('%', ?, '%') LIMIT 300"))
) {
  $short = $address;
  if (strpos($short, ',') !== false) $short = substr($short, 0, strpos($short, ','));
  $short = trim($short);
  if ($short === '') $short = $address;

  $selGA->bind_param("s", $short);
  if ($selGA->execute()) {
    $res = $selGA->get_result();
    while ($row = ($res ? $res->fetch_assoc() : null)) {
      $fmt = extract_formatted_address_from_json_dump($row['json_dump'] ?? null);
      if (!$fmt) continue;
      if (normalize_address_strict($fmt) === $needleNorm) {
        $exactFound = [
          'source'            => 'google_addresses',
          'id'                => (int)$row['id'],
          'formatted_address' => $fmt,
          'normalized_input'  => $needleNorm,
          'normalized_match'  => normalize_address_strict($fmt),
          'similarity'        => 100
        ];
        // Report json_dump status and add inline filler if empty
        $ga_id_for_link = (int)$row['id'];
        $dump_now = $row['json_dump'] ?? null;
        $ga_place_id = $row['place_id'] ?? null;
        $exactFound['google_addresses'] = [
          'google_addresses_id' => $ga_id_for_link,
          'place_id'            => $ga_place_id,
          'has_json_dump'       => (bool)($dump_now !== null && trim($dump_now) !== '')
        ];
        // Auto-fill google_addresses.json_dump if missing using its own place_id
        if ($GOOGLE_API_KEY && $ga_place_id) {
          if (!$exactFound['google_addresses']['has_json_dump']) {
            dbg('Exact match via google_addresses id='.$row['id'].' has_json='.(int)$exactFound['google_addresses']['has_json_dump']);
            $autoFill = fill_ga_json_if_missing($mysqli, $ga_id_for_link, $ga_place_id, $GOOGLE_API_KEY);
            dbg('Auto-filled GA json_dump (GA search) id='.$ga_id_for_link.' updated='.(int)($autoFill['updated'] ?? 0).' reason='.($autoFill['reason'] ?? ''));
            $dump2 = db_get_google_addresses_json_dump($mysqli, $ga_id_for_link);
            $exactFound['google_addresses']['has_json_dump'] = (bool)($dump2 !== null && trim($dump2) !== '');
            $exactFound['google_addresses_autofill'] = $autoFill;
          }
        }
        // Ensure latitude/longitude are filled from json_dump if missing
        $latlng_result = fill_ga_latlng_if_missing($mysqli, (int)$ga_id_for_link);
        dbg('fill_ga_latlng_if_missing (A0 GA path): '.json_encode($latlng_result));
        // King County parcels: check GA; enqueue job if missing
        $kc_id_ga = db_get_kc_parcel_for_ga($mysqli, $ga_id_for_link);
        $enq = null;
        if ($kc_id_ga === null) {
          $enq = ensure_kc_job($mysqli, 'king_county_parcels', $ga_id_for_link, $fmt);
        }
        if ($kc_id_ga !== null) {
          $exactFound['king_county_parcels'] = (int)$kc_id_ga;
        } else {
          $exactFound['king_county_parcels'] = (object)[];
        }
        // If KC row exists but GA link is empty, set it to this GA id
        if ($kc_id_ga !== null) {
          dbg('Attempt KC link update: kc_id='.(int)$kc_id_ga.' set GA='.(int)$ga_id_for_link);
          $kc_empty = kc_google_addresses_empty($mysqli, $kc_id_ga);
          if ($kc_empty === true) {
            $kcUpd = db_set_kc_google_addresses_if_empty($mysqli, (int)$kc_id_ga, (int)$ga_id_for_link);
            dbg('KC update result: '.json_encode($kcUpd));
            $exactFound['king_county_parcels_google_addresses_update'] = $kcUpd;
            $kc_empty = kc_google_addresses_empty($mysqli, $kc_id_ga);
          }
          if ($kc_empty === true) {
            $exactFound['king_county_parcels_google_addresses_empty'] = true;
          }
        }
        break;
      }
    }
    $res?->free();
  }
  $selGA->close();
}

// BEFORE ANY API CALLS: Check if we have fresh data for this address
// Use the robust helper that searches for the freshest close match by normalized address
if (!$exactFound && $GOOGLE_API_KEY) {
  $early_fresh_global = find_potential_fresh_record_by_address($mysqli, $address, $needleNorm);
  if ($early_fresh_global) {
    dbg('Using fresh data (global early check) instead of making any API calls: place_id=' . ($early_fresh_global['place_id'] ?? 'null'));

    $final_ids = [
      'google_addresses_id'     => (int)$early_fresh_global['id'],
      'google_places_id'        => null,
      'king_county_parcels_id'  => null,
    ];

    // Always update apartment_listings.google_addresses_id if apartment_listings_id is provided
    $apartment_listings_update = null;
    if ($apartment_listings_id && $final_ids['google_addresses_id']) {
      $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
      dbg('apartment_listings update (fresh global): '.json_encode($apartment_listings_update));
    }

    $fmt_addr = extract_formatted_address_from_json_dump($early_fresh_global['json_dump'] ?? null) ?? $address;

    $response = [
      'ok' => true,
      'result' => [
        'source'             => 'google_addresses',
        'id'                 => (int)$early_fresh_global['id'],
        'place_id'           => $early_fresh_global['place_id'] ?? null,
        'name'               => $early_fresh_global['building_name'] ?? null,
        'formatted_address'  => $fmt_addr,
        'lat'                => $early_fresh_global['latitude'] ?? null,
        'lng'                => $early_fresh_global['longitude'] ?? null,
        'rating'             => $early_fresh_global['initial_review_rating'] ?? null,
        'user_ratings_total' => $early_fresh_global['initial_review_count'] ?? null,
        'normalized_input'   => $needleNorm,
        'normalized_match'   => normalize_address_strict($fmt_addr),
        'searched_address'   => $address,
        'data_fresh'         => true,
        'data_age_hours'     => $early_fresh_global['_data_age_hours'] ?? null,
        'similarity_score'   => $early_fresh_global['_similarity_score'] ?? null,
        'apartment_listings_id' => $apartment_listings_id,
      ],
      'final_ids' => $final_ids,
      'tries' => [], // No API calls made
      'skipped_api_calls' => true,
        'reason' => 'Fresh data found (less than 24 hours old)',
        'apartment_listings_update' => $apartment_listings_update,
        'apartment_listings_id' => $apartment_listings_id,
      ];
    out_json($response);
  }
}

// If we found an exact match in DB, return it now (no API calls, no inserts)
if ($exactFound) {
  $include_details = true;
  if (isset($_GET['include_full_details'])) {
    $val = strtolower((string)$_GET['include_full_details']);
    $include_details = ($val === '1' || $val === 'true' || $val === 'yes');
  }

  // Build base final_ids
  $final_ids = [
    'google_addresses_id'     => $exactFound['source'] === 'google_addresses' ? ($exactFound['id'] ?? null) : ($exactFound['google_addresses']['google_addresses_id'] ?? null),
    'google_places_id'        => $exactFound['source'] === 'google_places' ? ($exactFound['id'] ?? null) : null,
    'king_county_parcels_id'  => isset($exactFound['king_county_parcels']) && is_int($exactFound['king_county_parcels']) ? $exactFound['king_county_parcels'] : null,
  ];

  // Always update apartment_listings.google_addresses_id if apartment_listings_id is provided
  $apartment_listings_update = null;
  if ($apartment_listings_id && $final_ids['google_addresses_id']) {
    $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
    dbg('apartment_listings update (exactFound): '.json_encode($apartment_listings_update));
  }

  // Attach extra result blobs
  $extra = [];
  // Always include apartment_listings_id in extra/meta for debugging
  $extra['apartment_listings_id'] = $apartment_listings_id;

  // 1) Google Places Details (fields=*) when we have a place_id & API key
  $pid_for_details = null;
  if ($exactFound['source'] === 'google_places') {
    $pid_for_details = $exactFound['google_addresses']['place_id'] ?? null;
    if (!$pid_for_details && isset($exactFound['id'])) {
      // We do not store gp.place_id in exactFound aside from above, so try to look it up quickly from DB
      if ($stmt = $mysqli->prepare('SELECT place_id FROM google_places WHERE id = ? LIMIT 1')) {
        $gp_id_lookup = (int)$exactFound['id'];
        $stmt->bind_param('i', $gp_id_lookup);
        $stmt->execute();
        $rs = $stmt->get_result();
        if ($rw = ($rs?->fetch_assoc() ?: null)) {
          $pid_for_details = $rw['place_id'] ?? null;
        }
        $stmt->close();
      }
    }
  } else {
    // source is google_addresses
    $pid_for_details = $exactFound['google_addresses']['place_id'] ?? null;
    if (!$pid_for_details && isset($exactFound['id'])) {
      if ($stmt = $mysqli->prepare('SELECT place_id FROM google_addresses WHERE id = ? LIMIT 1')) {
        $ga_id_lookup = (int)$exactFound['id'];
        $stmt->bind_param('i', $ga_id_lookup);
        $stmt->execute();
        $rs = $stmt->get_result();
        if ($rw = ($rs?->fetch_assoc() ?: null)) {
          $pid_for_details = $rw['place_id'] ?? null;
        }
        $stmt->close();
      }
    }
  }

  if ($include_details && $GOOGLE_API_KEY && $pid_for_details) {
    $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
    $url_det = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid_for_details)
             .'&key='.rawurlencode($GOOGLE_API_KEY)
             .'&language=en'
             .'&fields='.rawurlencode($all_fields);
    dbg('ExactFound attach details: '.preg_replace('~key=[^&]+~','key=REDACTED',$url_det));
    $det = http_get_json($url_det);
    if (is_array($det) && isset($det['status']) && $det['status'] === 'OK') {
      $extra['places_details'] = $det;
    } else {
      $extra['places_details_error'] = $det['status'] ?? 'unknown';
    }
  }

  // 2) Attach google_addresses row if we have its id
  $ga_attach_id = $final_ids['google_addresses_id'] ?? null;
  if ($ga_attach_id) {
    if ($stmt = $mysqli->prepare('SELECT id, place_id, source, building_name, latitude, longitude, initial_review_rating, initial_review_count FROM google_addresses WHERE id = ? LIMIT 1')) {
      $stmt->bind_param('i', $ga_attach_id);
      $stmt->execute();
      $rs = $stmt->get_result();
      if ($rw = ($rs?->fetch_assoc() ?: null)) {
        $extra['google_addresses_row'] = $rw;
      }
      $stmt->close();
    }
  }

  $response = [
    'ok' => true,
    'result' => $exactFound,
    'final_ids' => $final_ids,
    'extras' => $extra,
    'similarity_score' => $exactFound['similarity'] ?? 100,
    'apartment_listings_update' => $apartment_listings_update
  ];
  out_json($response);
}

//////////////////////////////
// (A) FORCE GOOGLE PLACES FIRST
//////////////////////////////
$resultPlaces = null;
// Early global check: avoid any FindPlaceFromText calls if a fresh google_addresses record
// closely matches this address by similarity and is less than 24 hours old.
if ($GOOGLE_API_KEY) {
  $early_fresh_global = find_potential_fresh_record_by_address($mysqli, $address, $needleNorm);
  if ($early_fresh_global) {
    dbg('Using fresh data (global early check) instead of making any API calls: place_id=' . ($early_fresh_global['place_id'] ?? 'null'));
    $final_ids = [
      'google_addresses_id'     => (int)$early_fresh_global['id'],
      'google_places_id'        => null,
      'king_county_parcels_id'  => null,
    ];
    $apartment_listings_update = null;
    if ($apartment_listings_id && $final_ids['google_addresses_id']) {
      $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
      dbg('apartment_listings update: '.json_encode($apartment_listings_update));
    }
    $fmt_addr = extract_formatted_address_from_json_dump($early_fresh_global['json_dump'] ?? null) ?? $address;
    $response = [
      'ok' => true,
      'result' => [
        'source'             => 'google_addresses',
        'id'                 => (int)$early_fresh_global['id'],
        'place_id'           => $early_fresh_global['place_id'] ?? null,
        'name'               => $early_fresh_global['building_name'] ?? null,
        'formatted_address'  => $fmt_addr,
        'lat'                => $early_fresh_global['latitude'] ?? null,
        'lng'                => $early_fresh_global['longitude'] ?? null,
        'rating'             => $early_fresh_global['initial_review_rating'] ?? null,
        'user_ratings_total' => $early_fresh_global['initial_review_count'] ?? null,
        'normalized_input'   => $needleNorm,
        'normalized_match'   => normalize_address_strict($fmt_addr),
        'searched_address'   => $address,
        'data_fresh'         => true,
        'data_age_hours'     => $early_fresh_global['_data_age_hours'] ?? null,
        'similarity_score'   => $early_fresh_global['_similarity_score'] ?? null
      ],
      'final_ids' => $final_ids,
      'tries' => [], // No API calls made
      'skipped_api_calls' => true,
        'reason' => 'Fresh data found (less than 24 hours old)',
        'apartment_listings_update' => $apartment_listings_update
      ];
    out_json($response);
  }
}
$placesTries = [];
if ($GOOGLE_API_KEY) {
  // Try establishment first (but only exact matches), then fall back to regular address
  // Never accept nearby businesses - only exact address matches
  $queryVariants = [
    ['label' => 'establishment',       'q' => $address . ' establishment'],
    ['label' => 'property_management', 'q' => $address . ' property management'],
    ['label' => 'business',            'q' => $address . ' business'],
    ['label' => 'exact_address',       'q' => $address],  // Fall back to plain address
    ['label' => 'premise',             'q' => $address . ' premise'],  // Then premise/building
  ];

  $fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types';
  $allCandidates = []; // collect all candidates across variants

  foreach ($queryVariants as $variant) {
    $url_places = sprintf(
      'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input=%s&inputtype=textquery&fields=%s&key=%s&language=en&region=%s',
      rawurlencode($variant['q']),
      rawurlencode($fields),
      rawurlencode($GOOGLE_API_KEY),
      rawurlencode($region)
    );
    dbg('Calling FindPlaceFromText ['.$variant['label'].']: '.preg_replace('~key=[^&]+~','key=REDACTED',$url_places));
    $pj = http_get_json($url_places);
    $status = $pj['status'] ?? 'null';
    $candCount = is_array($pj['candidates'] ?? null) ? count($pj['candidates']) : 0;
    dbg('FindPlaceFromText ['.$variant['label'].'] status='.$status.' candidates='.$candCount);

    // Always record raw reply in tries (user asked to see "the whole reply")
    $placesTries[] = [
      'label'   => $variant['label'],
      'query'   => $variant['q'],
      'response'=> $pj,
    ];

    if ($pj && ($pj['status'] ?? '') === 'OK' && !empty($pj['candidates'])) {
      foreach ($pj['candidates'] as $idx => $cand) {
        // Validate that the returned address actually matches the input address
        $returned_address = $cand['formatted_address'] ?? '';
        $similarity = sim_score($address, $returned_address);
        
        dbg('Candidate validation: input="'.$address.'" returned="'.$returned_address.'" similarity='.$similarity.'%');
        
        // Only accept candidates with high similarity (95%+) or exact street number match
        // This prevents accepting nearby businesses when we want the exact address
        if ($similarity >= 95) {
          $allCandidates[] = [
            'variant'    => $variant['label'],
            'candidate'  => $cand,
            'score'      => score_places_candidate($cand),
            'rank_in_variant' => $idx,
            'similarity' => $similarity
          ];
        } else {
          dbg('REJECTED candidate due to low similarity ('.$similarity.'%): '.$returned_address);
        }
      }
      // Only break if we found valid candidates with good similarity
      // Otherwise continue to next variant (fallback to plain address, etc.)
      if (!empty($allCandidates)) {
        break;
      }
    }
  }

  // Choose the best-scoring candidate. If tie, prefer lower rank_in_variant, then earlier variant order.
  $chosen = null;
  if (!empty($allCandidates)) {
    usort($allCandidates, function($a, $b) {
      if ($b['score'] !== $a['score']) return $b['score'] <=> $a['score'];
      if ($a['rank_in_variant'] !== $b['rank_in_variant']) return $a['rank_in_variant'] <=> $b['rank_in_variant'];
      // keep original variant order by not changing relative position if above are equal
      return 0;
    });
    $chosen = $allCandidates[0];
  }

  if ($chosen) {
    $c   = $chosen['candidate'];
    $pid = $c['place_id'] ?? null;
    $name= $c['name'] ?? null;
    $fa  = $c['formatted_address'] ?? null;
    $lat = $c['geometry']['location']['lat'] ?? null;
    $lng = $c['geometry']['location']['lng'] ?? null;
    $rating = isset($c['rating']) ? (float)$c['rating'] : null;
    $urc    = isset($c['user_ratings_total']) ? (int)$c['user_ratings_total'] : null;

    if ($pid) {
      // Check if we already have fresh data (less than 24 hours old) for this place_id
      $fresh_record = get_fresh_google_addresses_record($mysqli, $pid);
      if ($fresh_record) {
        dbg('Found fresh data for place_id='.$pid.' (less than 24 hours old), skipping API calls');
        
        $final_ids = [
          'google_addresses_id'     => (int)$fresh_record['id'],
          'google_places_id'        => null,
          'king_county_parcels_id'  => null,
        ];

        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        // If no apartment_listings_id, try to find by normalized address and update linkage
        if (!$apartment_listings_id && $final_ids['google_addresses_id']) {
          // Try to find a matching apartment_listings row by normalized address
          // Fetch all candidate rows and compare normalized addresses in PHP
          $sel = $mysqli->prepare("SELECT id, full_address FROM apartment_listings WHERE full_address IS NOT NULL AND full_address != ''");
          if ($sel) {
            $sel->execute();
            $res = $sel->get_result();
            while ($row = $res->fetch_assoc()) {
              $db_norm = normalize_address_strict($row['full_address']);
              if ($db_norm === $needleNorm) {
                $found_id = (int)$row['id'];
                $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $found_id, $final_ids['google_addresses_id']);
                dbg('apartment_listings update (auto by address, robust): '.json_encode($apartment_listings_update));
                break;
              }
            }
            $sel->close();
          }
          // Optionally, insert a new row if not found (commented for safety)
          // if (!$apartment_listings_update) {
          //   $ins = $mysqli->prepare("INSERT INTO apartment_listings (full_address, google_addresses_id, active) VALUES (?, ?, 'yes')");
          //   if ($ins) {
          //     $ins->bind_param('si', $fa, $final_ids['google_addresses_id']);
          //     $ins->execute();
          //     $new_id = $ins->insert_id;
          //     $ins->close();
          //     $apartment_listings_update = ['inserted' => true, 'id' => $new_id];
          //     dbg('apartment_listings insert (auto): '.json_encode($apartment_listings_update));
          //   }
          // }
        } else if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }

        // Compute a real similarity based on address text
        $similarity_match = is_string($fa)
          ? sim_score($needleNorm, normalize_address_strict($fa))
          : 100;

        $response = [
          'ok' => true,
          'result' => [
            'source'             => 'google_addresses',
            'id'                 => (int)$fresh_record['id'],
            'place_id'           => $pid,
            'name'               => $fresh_record['building_name'] ?? $name,
            'formatted_address'  => $fa,
            'lat'                => $fresh_record['latitude'] ?? $lat,
            'lng'                => $fresh_record['longitude'] ?? $lng,
            'rating'             => $fresh_record['initial_review_rating'] ?? $rating,
            'user_ratings_total' => $fresh_record['initial_review_count'] ?? $urc,
            'normalized_input'   => $needleNorm,
            'normalized_match'   => normalize_address_strict($fa ?? ''),
            'query_variant_used' => $chosen['variant'] ?? null,
            'data_fresh'         => true,
            'data_age_hours'     => round((time() - (int)$fresh_record['time']) / 3600, 1)
          ],
          'final_ids' => $final_ids,
          'tries' => $placesTries,
          'skipped_api_calls' => true,
          'reason' => 'Fresh data found (less than 24 hours old)',
            'similarity_score' => $similarity_match,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      }
      // Fetch FULL Places Details so we can show the entire response (ALL fields)
      $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
      $url_det_full = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid)
                    .'&key='.rawurlencode($GOOGLE_API_KEY)
                    .'&language=en'
                    .'&fields='.rawurlencode($all_fields);
      dbg('Chosen candidate details (FULL): '.preg_replace('~key=[^&]+~','key=REDACTED',$url_det_full));
      $detailsFull = http_get_json($url_det_full);

      // Build a harvest object with commonly useful fields
      $harvest = null;
      if (is_array($detailsFull) && isset($detailsFull['status']) && $detailsFull['status'] === 'OK') {
        $r = $detailsFull['result'] ?? [];
        $harvest = [
          'name'                   => $r['name'] ?? null,
          'formatted_address'      => $r['formatted_address'] ?? null,
          'address_components'     => $r['address_components'] ?? null,
          'business_status'        => $r['business_status'] ?? null,
          'types'                  => $r['types'] ?? null,
          'rating'                 => isset($r['rating']) ? (float)$r['rating'] : null,
          'user_ratings_total'     => isset($r['user_ratings_total']) ? (int)$r['user_ratings_total'] : null,
          'international_phone_number' => $r['international_phone_number'] ?? ($r['formatted_phone_number'] ?? null),
          'website'                => $r['website'] ?? null,
          'url'                    => $r['url'] ?? null,
          'opening_hours'          => $r['opening_hours'] ?? null,
          'geometry'               => $r['geometry'] ?? null,
          'place_id'               => $r['place_id'] ?? $pid,
        ];
      }

      $existing_gp_id = find_existing_google_places_id($mysqli, $pid);
      if ($existing_gp_id) {
        dbg('Found existing google_places.id='.$existing_gp_id.' for pid='.$pid);
        // Try to link to google_addresses if present
        $ga_id = find_google_addresses_id_by_gp_id($mysqli, $existing_gp_id) ?? find_google_addresses_id_by_place_id($mysqli, $pid);
        $ga_info = null;
        $ga_place_id = null;
        if ($ga_id !== null) {
          $rowGA = db_get_google_addresses_place_id_and_dump($mysqli, $ga_id) ?: ['place_id'=>null,'json_dump'=>null];
          $ga_place_id = $rowGA['place_id'] ?? null;
          $dump = $rowGA['json_dump'] ?? null;
          $ga_info = [
            'google_addresses_id' => $ga_id,
            'place_id'            => $ga_place_id,
            'has_json_dump'       => (bool)($dump !== null && trim($dump) !== ''),
          ];
        }
        // Auto-fill GA json_dump if missing
        if ($GOOGLE_API_KEY && $ga_id !== null) {
          $pid_for_fill = $ga_place_id ?: $pid;
          if ($pid_for_fill && (!$ga_info || (isset($ga_info['has_json_dump']) && !$ga_info['has_json_dump']))) {
            $autoFill = fill_ga_json_if_missing($mysqli, $ga_id, $pid_for_fill, $GOOGLE_API_KEY);
            $dump2 = db_get_google_addresses_json_dump($mysqli, $ga_id);
            $ga_info = [
              'google_addresses_id' => $ga_id,
              'place_id'            => $ga_place_id,
              'has_json_dump'       => (bool)($dump2 !== null && trim($dump2) !== ''),
            ];
            $result['google_addresses'] = $ga_info;
            $result['google_addresses_autofill'] = $autoFill;
          }
        }
        if ($ga_id !== null) {
          $latlng_result = fill_ga_latlng_if_missing($mysqli, (int)$ga_id);
          dbg('fill_ga_latlng_if_missing (PLACES existing_gp path): '.json_encode($latlng_result));
        }
        $result = [
          'source'             => 'google_places',
          'id'                 => $existing_gp_id,
          'place_id'           => $pid,
          'name'               => $name,
          'formatted_address'  => $fa,
          'lat'                => $lat,
          'lng'                => $lng,
          'rating'             => $rating,
          'user_ratings_total' => $urc,
          'normalized_input'   => $needleNorm,
          'normalized_match'   => normalize_address_strict($fa ?? ''),
          'searched_address'   => $address,
          'query_variant_used' => $chosen['variant'] ?? null,
        ];
        if ($ga_info !== null) $result['google_addresses'] = $ga_info;

        // KC lookup/update
        $kc_id_gp = db_get_kc_parcel_for_gp($mysqli, $existing_gp_id);
        $kc_id_ga = ($ga_id !== null) ? db_get_kc_parcel_for_ga($mysqli, $ga_id) : null;
        $kc_id = $kc_id_gp ?? $kc_id_ga;
        if ($kc_id === null) {
          $use_source_id = ($ga_id !== null) ? $ga_id : $existing_gp_id;
          ensure_kc_job($mysqli, 'king_county_parcels', $use_source_id, $fa ?? $address);
        }
        if ($kc_id !== null) {
          $result['king_county_parcels'] = (int)$kc_id;
        } else {
          $result['king_county_parcels'] = (object)[];
        }
        if (isset($kc_id) && $kc_id !== null && isset($ga_id) && $ga_id !== null) {
          dbg('Attempt KC link update: kc_id='.(int)$kc_id.' set GA='.(int)$ga_id);
          $kc_empty = kc_google_addresses_empty($mysqli, (int)$kc_id);
          if ($kc_empty === true) {
            $kcUpd = db_set_kc_google_addresses_if_empty($mysqli, (int)$kc_id, (int)$ga_id);
            dbg('KC update result: '.json_encode($kcUpd));
            $result['king_county_parcels_google_addresses_update'] = $kcUpd;
          }
        }
        $final_ids = [
          'google_addresses_id'     => $ga_id ?? null,
          'google_places_id'        => $existing_gp_id ?? null,
          'king_county_parcels_id'  => $kc_id ?? null,
        ];
        
        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }
        
        // Record which selection rule we used
        $result['selection'] = [
          'method' => 'best_score_by_types_rating_popularity',
          'score'  => $chosen['score'] ?? null,
          'variant_label' => $chosen['variant'] ?? null
        ];
        
        // Compute a real similarity based on address text, not ranking score
        $similarity_match = is_string($fa)
          ? sim_score($needleNorm, normalize_address_strict($fa))
          : 100;

        $response = [
          'ok' => true,
          'result' => $result,
          'final_ids' => $final_ids,
          'tries' => $placesTries,        // return all raw replies
          'places_details_full' => $detailsFull,      // FULL Google Places response
          'places_details_harvest' => $harvest,       // extracted useful fields
            'similarity_score' => $similarity_match,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      } else {
        dbg('No existing google_places for pid='.$pid.' -> checking if google_addresses exists before inserting');
        
        // Check if this place_id already exists in google_addresses to avoid duplicate key error
        $existing_ga_id = find_existing_google_addresses_id($mysqli, $pid);
        if ($existing_ga_id) {
          dbg('Found existing google_addresses.id='.$existing_ga_id.' for pid='.$pid.' -> updating instead of inserting');
          
          // Update existing record with fresh Places Details
          $payload_for_dump = (is_array($detailsFull) && ($detailsFull['status'] ?? null) === 'OK') ? $detailsFull : ['status'=>'FALLBACK','result'=>$c];
          $json_dump_payload = json_encode($payload_for_dump, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
          
          $update_stmt = $mysqli->prepare("UPDATE google_addresses SET json_dump = ?, building_name = ?, latitude = ?, longitude = ?, initial_review_rating = ?, initial_review_count = ? WHERE id = ?");
          if ($update_stmt) {
            $lat_val = is_numeric($lat) ? (float)$lat : null;
            $lng_val = is_numeric($lng) ? (float)$lng : null;
            $update_stmt->bind_param('ssdddii', $json_dump_payload, $name, $lat_val, $lng_val, $rating, $urc, $existing_ga_id);
            $update_stmt->execute();
            $update_stmt->close();
          }
          
          $final_ids = [
            'google_addresses_id'     => $existing_ga_id,
            'google_places_id'        => null,
            'king_county_parcels_id'  => null,
          ];

          // Update apartment_listings if apartment_listings_id provided
          $apartment_listings_update = null;
          if ($apartment_listings_id && $final_ids['google_addresses_id']) {
            $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
            dbg('apartment_listings update: '.json_encode($apartment_listings_update));
          }

          // Compute a real similarity based on address text, not ranking score
          $similarity_match = is_string($fa)
            ? sim_score($needleNorm, normalize_address_strict($fa))
            : 100;

          $response = [
            'ok' => true,
            'updated' => 'google_addresses',
            'google_addresses_id' => $existing_ga_id,
            'result' => [
              'source'             => 'google_addresses',
              'id'                 => $existing_ga_id,
              'place_id'           => $pid,
              'name'               => $name,
              'formatted_address'  => $fa,
              'lat'                => $lat,
              'lng'                => $lng,
              'rating'             => $rating,
              'user_ratings_total' => $urc,
              'normalized_input'   => $needleNorm,
              'normalized_match'   => normalize_address_strict($fa ?? ''),
              'query_variant_used' => $chosen['variant'] ?? null
            ],
            'final_ids' => $final_ids,
            'tries' => $placesTries,
            'places_details_full' => $detailsFull,
              'similarity_score' => $similarity_match,
              'apartment_listings_update' => $apartment_listings_update
            ];
          out_json($response);
        } else {
          dbg('No existing google_addresses for pid='.$pid.' -> inserting new record');
        }
        
        // Prefer full Places Details payload for json_dump; if not OK, fall back to candidate summary
        $payload_for_dump = (is_array($detailsFull) && ($detailsFull['status'] ?? null) === 'OK') ? $detailsFull : ['status'=>'FALLBACK','result'=>$c];
        $ins = db_insert_google_addresses(
          $mysqli,
          (string)$pid,
          'places',
          $name ?? null,
          is_numeric($lat) ? (float)$lat : null,
          is_numeric($lng) ? (float)$lng : null,
          isset($rating) ? (float)$rating : null,
          isset($urc) ? (int)$urc : null,
          $payload_for_dump
        );
        if (!$ins['ok']) {
          out_json(['ok'=>false, 'error'=>'Insert into google_addresses failed', 'mysql_error'=>$ins['mysql_error']], 500);
        }
        $new_ga_id = $ins['id'];

        // If existing_google_places_id was provided, link it to the new google_addresses record
        if ($existing_google_places_id && $new_ga_id) {
          dbg('Linking existing google_places.id='.$existing_google_places_id.' to new google_addresses.id='.$new_ga_id);
          $update = $mysqli->prepare("UPDATE google_places SET google_addresses_id = ? WHERE id = ?");
          if ($update) {
            $update->bind_param('ii', $new_ga_id, $existing_google_places_id);
            $update->execute();
            $rows_updated = $update->affected_rows;
            $update->close();
            dbg('Updated google_places: '.$rows_updated.' rows affected');
          }
        }

        // Ensure coords exist (already provided above), then build final response
        $final_ids = [
          'google_addresses_id'     => $new_ga_id,
          'google_places_id'        => $existing_google_places_id ?? null,
          'king_county_parcels_id'  => null,
        ];

        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }

        // Compute a real similarity based on address text, not ranking score
        $similarity_match = is_string($fa)
          ? sim_score($needleNorm, normalize_address_strict($fa))
          : 100;

        $response = [
          'ok' => true,
          'inserted' => 'google_addresses',
          'google_addresses_id' => $new_ga_id,
          'result' => [
            'source'             => 'google_addresses',
            'id'                 => $new_ga_id,
            'place_id'           => $pid,
            'name'               => $name,
            'formatted_address'  => $fa,
            'lat'                => $lat,
            'lng'                => $lng,
            'rating'             => $rating,
            'user_ratings_total' => $urc,
            'normalized_input'   => $needleNorm,
            'normalized_match'   => normalize_address_strict($fa ?? ''),
            'query_variant_used' => $chosen['variant'] ?? null
          ],
          'final_ids' => $final_ids,
          // Return the raw tries and the full details payload we stored so caller can verify
          'tries' => $placesTries,
          'places_details_full' => $detailsFull,
            'similarity_score' => $similarity_match,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      }
    }
  }
}

//////////////////////////////
// (B) FALLBACK: GOOGLE GEOCODING (only if PLACES not found/matched)
//////////////////////////////
$resultGeocode = null;
if (!$resultPlaces && $GOOGLE_API_KEY) {
  $url_geo = sprintf(
    'https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s&language=en&region=%s',
    rawurlencode($address),
    rawurlencode($GOOGLE_API_KEY),
    rawurlencode($region)
  );
  dbg('Calling Geocode: '.preg_replace('~key=[^&]+~','key=REDACTED',$url_geo));
  $gj = http_get_json($url_geo);
  dbg('Geocode status='.( $gj['status'] ?? 'null').' results='.( is_array($gj['results'] ?? null) ? count($gj['results']) : 0));
  
  // Track API usage
  if ($gj && ($gj['status'] ?? '') === 'OK') {
    try {
      log_google_api_call($mysqli, 'geocoding', 1, [
        'address' => substr($address, 0, 100),
        'region' => $region
      ]);
    } catch (Exception $e) {
      error_log("[API Track] Failed to log Geocoding call: " . $e->getMessage());
    }
  }

  if ($gj && ($gj['status'] ?? '') === 'OK' && !empty($gj['results'])) {
    $r = $gj['results'][0];
    $pid = $r['place_id'] ?? null;
    $fa  = $r['formatted_address'] ?? null;
    $lat = $r['geometry']['location']['lat'] ?? null;
    $lng = $r['geometry']['location']['lng'] ?? null;

    if ($pid) {
      // Check if we already have fresh data (less than 24 hours old) for this place_id
      $fresh_record = get_fresh_google_addresses_record($mysqli, $pid);
      if ($fresh_record) {
        dbg('Found fresh data for place_id='.$pid.' (less than 24 hours old), skipping API calls');
        
        $final_ids = [
          'google_addresses_id'     => (int)$fresh_record['id'],
          'google_places_id'        => null,
          'king_county_parcels_id'  => null,
        ];

        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }

        // Compute a real similarity based on address text
        $similarity_match = is_string($fa)
          ? sim_score($needleNorm, normalize_address_strict($fa))
          : 100;

        $response = [
          'ok' => true,
          'result' => [
            'source'             => 'google_addresses',
            'id'                 => (int)$fresh_record['id'],
            'place_id'           => $pid,
            'name'               => $fresh_record['building_name'] ?? null,
            'formatted_address'  => $fa,
            'lat'                => $fresh_record['latitude'] ?? $lat,
            'lng'                => $fresh_record['longitude'] ?? $lng,
            'rating'             => $fresh_record['initial_review_rating'] ?? null,
            'user_ratings_total' => $fresh_record['initial_review_count'] ?? null,
            'normalized_input'   => $needleNorm,
            'normalized_match'   => normalize_address_strict($fa ?? ''),
            'searched_address'   => $address,
            'data_fresh'         => true,
            'data_age_hours'     => round((time() - (int)$fresh_record['time']) / 3600, 1)
          ],
          'final_ids' => $final_ids,
          'skipped_api_calls' => true,
          'reason' => 'Fresh data found (less than 24 hours old)',
            'similarity_score' => $similarity_match,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      }
      $existing_ga_id = find_existing_google_addresses_id($mysqli, $pid);
      if ($existing_ga_id) {
        dbg('Found existing google_addresses.id='.$existing_ga_id.' for pid='.$pid);
        $gaRow = db_get_google_addresses_place_id_and_dump($mysqli, $existing_ga_id) ?: ['place_id'=>null,'json_dump'=>null];
        $ga_place_id = $gaRow['place_id'] ?? null;
        $dump = $gaRow['json_dump'] ?? null;
        $result = [
          'source'             => 'google_addresses',
          'id'                 => $existing_ga_id,
          'place_id'           => $pid,
          'formatted_address'  => $fa,
          'lat'                => $lat,
          'lng'                => $lng,
          'normalized_input'   => $needleNorm,
          'normalized_match'   => normalize_address_strict($fa ?? ''),
          'searched_address'   => $address,
          'google_addresses'   => [
            'google_addresses_id' => $existing_ga_id,
            'place_id'            => $ga_place_id,
            'has_json_dump'       => (bool)($dump !== null && trim($dump) !== '')
          ]
        ];
        // Auto-fill GA json_dump if missing; prefer GA's own place_id
        if ($GOOGLE_API_KEY) {
          $pid_for_fill = $ga_place_id ?: $pid;
          if ($pid_for_fill && !$result['google_addresses']['has_json_dump']) {
            $autoFill = fill_ga_json_if_missing($mysqli, $existing_ga_id, $pid_for_fill, $GOOGLE_API_KEY);
            $dump2 = db_get_google_addresses_json_dump($mysqli, $existing_ga_id);
            $result['google_addresses']['has_json_dump'] = (bool)($dump2 !== null && trim($dump2) !== '');
            $result['google_addresses_autofill'] = $autoFill;
          }
        }
        // Ensure latitude/longitude are filled from json_dump if missing
        $latlng_result = fill_ga_latlng_if_missing($mysqli, (int)$existing_ga_id);
        dbg('fill_ga_latlng_if_missing (GEOCODING existing_ga path): '.json_encode($latlng_result));
        // King County parcels: check GA; enqueue if missing
        $kc_id_ga = db_get_kc_parcel_for_ga($mysqli, $existing_ga_id);
        $enq = null;
        if ($kc_id_ga === null) {
          $enq = ensure_kc_job($mysqli, 'king_county_parcels', $existing_ga_id, $fa ?? $address);
        }
        if ($kc_id_ga !== null) {
          $result['king_county_parcels'] = (int)$kc_id_ga;
        } else {
          $result['king_county_parcels'] = (object)[];
        }
        // If KC row exists and GA link is empty, set it to this GA id
        if (isset($kc_id_ga) && $kc_id_ga !== null) {
          dbg('Attempt KC link update: kc_id='.(int)$kc_id_ga.' set GA='.(int)$existing_ga_id);
          $kc_empty = kc_google_addresses_empty($mysqli, (int)$kc_id_ga);
          if ($kc_empty === true) {
            $kcUpd = db_set_kc_google_addresses_if_empty($mysqli, (int)$kc_id_ga, (int)$existing_ga_id);
            dbg('KC update result: '.json_encode($kcUpd));
            $result['king_county_parcels_google_addresses_update'] = $kcUpd;
            $kc_empty = kc_google_addresses_empty($mysqli, (int)$kc_id_ga);
          }
          if ($kc_empty === true) {
            $result['king_county_parcels_google_addresses_empty'] = true;
          }
        }
        $final_ids = [
          'google_addresses_id'     => $existing_ga_id ?? null,
          'google_places_id'        => null,
          'king_county_parcels_id'  => $kc_id_ga ?? null,
        ];
        
        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }
        
        $response = [
          'ok' => true,
          'result' => $result,
          'final_ids' => $final_ids,
            'similarity_score' => 100,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      } else {
        dbg('No existing google_addresses for pid='.$pid.' -> checking if google_addresses exists before inserting via geocode path');
        
        // Double-check if this place_id already exists in google_addresses to avoid duplicate key error
        $existing_ga_id_check = find_existing_google_addresses_id($mysqli, $pid);
        if ($existing_ga_id_check) {
          dbg('Found existing google_addresses.id='.$existing_ga_id_check.' for pid='.$pid.' -> updating instead of inserting');
          
          // Update existing record with fresh Places Details
          $detailsFromPid = null;
          if ($GOOGLE_API_KEY && $pid) {
            $url_det_full = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid)
                          .'&key='.rawurlencode($GOOGLE_API_KEY)
                          .'&language=en'
                          .'&fields=*';
            dbg('Geocode path: fetch full Places Details for pid='.$pid);
            $detailsFromPid = http_get_json($url_det_full);
          }
          $payload_for_dump = (is_array($detailsFromPid) && ($detailsFromPid['status'] ?? null) === 'OK')
            ? $detailsFromPid
            : $gj; // store the Geocode response if Places Details isn't available

          $name_from_details = null;
          if (isset($detailsFromPid['result']['name'])) {
            $name_from_details = $detailsFromPid['result']['name'];
          }
          
          $json_dump_payload = json_encode($payload_for_dump, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
          
          $update_stmt = $mysqli->prepare("UPDATE google_addresses SET json_dump = ?, building_name = ?, latitude = ?, longitude = ?, initial_review_rating = ?, initial_review_count = ? WHERE id = ?");
          if ($update_stmt) {
            $rating_val = isset($detailsFromPid['result']['rating']) ? (float)$detailsFromPid['result']['rating'] : null;
            $count_val = isset($detailsFromPid['result']['user_ratings_total']) ? (int)$detailsFromPid['result']['user_ratings_total'] : null;
            $lat_val = is_numeric($lat) ? (float)$lat : null;
            $lng_val = is_numeric($lng) ? (float)$lng : null;
            $update_stmt->bind_param('ssdddii', $json_dump_payload, $name_from_details, $lat_val, $lng_val, $rating_val, $count_val, $existing_ga_id_check);
            $update_stmt->execute();
            $update_stmt->close();
          }
          
          $final_ids = [
            'google_addresses_id'     => $existing_ga_id_check,
            'google_places_id'        => null,
            'king_county_parcels_id'  => null,
          ];
          
          // Update apartment_listings if apartment_listings_id provided
          $apartment_listings_update = null;
          if ($apartment_listings_id && $final_ids['google_addresses_id']) {
            $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
            dbg('apartment_listings update: '.json_encode($apartment_listings_update));
          }
          
          $response = [
            'ok' => true,
            'updated' => 'google_addresses',
            'google_addresses_id' => $existing_ga_id_check,
            'result' => [
              'source'             => 'google_addresses',
              'id'                 => $existing_ga_id_check,
              'place_id'           => $pid,
              'formatted_address'  => $fa,
              'lat'                => $lat,
              'lng'                => $lng,
              'normalized_input'   => $needleNorm,
              'normalized_match'   => normalize_address_strict($fa ?? ''),
              'searched_address'   => $address
            ],
            'final_ids' => $final_ids,
            'geocode_full' => $gj,
            'places_details_full' => $detailsFromPid,
              'similarity_score' => 100,
              'apartment_listings_update' => $apartment_listings_update
            ];
          out_json($response);
        } else {
          dbg('No existing google_addresses for pid='.$pid.' -> inserting new record via geocode path');
        }
        
        // Try to fetch full Places Details for richer json_dump; if it fails, keep the Geocode payload
        $detailsFromPid = null;
        if ($GOOGLE_API_KEY && $pid) {
          $all_fields = 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,formatted_phone_number,international_phone_number,website,url,opening_hours,photos,reviews,price_level,address_components,business_status,vicinity,utc_offset,adr_address,editorial_summary,current_opening_hours,secondary_opening_hours,plus_code,icon,icon_background_color,icon_mask_base_uri';
          $url_det_full = 'https://maps.googleapis.com/maps/api/place/details/json?place_id='.rawurlencode($pid)
                        .'&key='.rawurlencode($GOOGLE_API_KEY)
                        .'&language=en'
                        .'&fields='.rawurlencode($all_fields);
          dbg('Geocode path: fetch full Places Details for pid='.$pid);
          $detailsFromPid = http_get_json($url_det_full);
        }
        $payload_for_dump = (is_array($detailsFromPid) && ($detailsFromPid['status'] ?? null) === 'OK')
          ? $detailsFromPid
          : $gj; // store the Geocode response if Places Details isn't available

        $name_from_details = null;
        if (isset($detailsFromPid['result']['name'])) {
          $name_from_details = $detailsFromPid['result']['name'];
        }

        $ins = db_insert_google_addresses(
          $mysqli,
          (string)$pid,
          'geocode',
          $name_from_details,
          is_numeric($lat) ? (float)$lat : null,
          is_numeric($lng) ? (float)$lng : null,
          isset($detailsFromPid['result']['rating']) ? (float)$detailsFromPid['result']['rating'] : null,
          isset($detailsFromPid['result']['user_ratings_total']) ? (int)$detailsFromPid['result']['user_ratings_total'] : null,
          $payload_for_dump
        );
        if (!$ins['ok']) {
          out_json(['ok'=>false, 'error'=>'Insert into google_addresses failed (geocode path)', 'mysql_error'=>$ins['mysql_error']], 500);
        }
        $new_ga_id = $ins['id'];

        $final_ids = [
          'google_addresses_id'     => $new_ga_id,
          'google_places_id'        => null,
          'king_county_parcels_id'  => null,
        ];
        
        // Update apartment_listings if apartment_listings_id provided
        $apartment_listings_update = null;
        if ($apartment_listings_id && $final_ids['google_addresses_id']) {
          $apartment_listings_update = update_apartment_listings_google_addresses_id($mysqli, $apartment_listings_id, $final_ids['google_addresses_id']);
          dbg('apartment_listings update: '.json_encode($apartment_listings_update));
        }
        
        $response = [
          'ok' => true,
          'inserted' => 'google_addresses',
          'google_addresses_id' => $new_ga_id,
          'result' => [
            'source'             => 'google_addresses',
            'id'                 => $new_ga_id,
            'place_id'           => $pid,
            'formatted_address'  => $fa,
            'lat'                => $lat,
            'lng'                => $lng,
            'normalized_input'   => $needleNorm,
            'normalized_match'   => normalize_address_strict($fa ?? ''),
            'searched_address'   => $address
          ],
          'final_ids' => $final_ids,
          // Include the payload we stored for verification
          'geocode_full' => $gj,
          'places_details_full' => $detailsFromPid,
            'similarity_score' => 100,
            'apartment_listings_update' => $apartment_listings_update
          ];
        out_json($response);
      }
    }
  }
}




//////////////////////////////
// (C) If we have an API preview, also compute near candidates then return
//////////////////////////////
/**
 * Regardless of API match, we present near-candidates from both tables to help manual triage.
 */
$nearAll = [];

// Near from google_places
if ($sel = $mysqli->prepare("SELECT id, Fulladdress FROM google_places WHERE Fulladdress LIKE CONCAT('%', ?, '%') LIMIT 50")) {
  $prefix = substr($address, 0, 20);
  $sel->bind_param("s", $prefix);
  if ($sel->execute()) {
    $res = $sel->get_result();
    while ($row = ($res ? $res->fetch_assoc() : null)) {
      $fa = $row['Fulladdress'] ?? '';
      if ($fa === '') continue;
      $faNorm = normalize_address_strict($fa);
      $score = sim_score($needleNorm, $faNorm);
      $nearAll[] = ['source' => 'google_places', 'id' => (int)$row['id'], 'addr' => $fa, 'score' => $score];
    }
    $res?->free();
  }
  $sel->close();
}

// Near from google_addresses
$short = $address;
if (strpos($short, ',') !== false) $short = substr($short, 0, strpos($short, ','));
$short = trim($short);
if ($short === '') $short = $address;

if ($selGA = $mysqli->prepare("SELECT id, json_dump FROM google_addresses WHERE json_dump LIKE CONCAT('%', ?, '%') LIMIT 100")) {
  $selGA->bind_param("s", $short);
  if ($selGA->execute()) {
    $res = $selGA->get_result();
    while ($row = ($res ? $res->fetch_assoc() : null)) {
      $jsonDump = $row['json_dump'] ?? null;
      $fmt = extract_formatted_address_from_json_dump($jsonDump);
      if (!$fmt) continue;
      $fmtNorm = normalize_address_strict($fmt);
      $score = sim_score($needleNorm, $fmtNorm);
      $nearAll[] = ['source' => 'google_addresses', 'id' => (int)$row['id'], 'formatted_address' => $fmt, 'score' => $score];
    }
    $res?->free();
  }
  $selGA->close();
}

usort($nearAll, fn($a,$b) => $b['score'] <=> $a['score']);

// No longer possible: resultPlaces/resultGeocode are always handled above with insert and out_json

//////////////////////////////
// (D) No API matches at all → return near candidates only (NO INSERTS)
//////////////////////////////
$final_ids = ['google_addresses_id'=>null,'google_places_id'=>null,'king_county_parcels_id'=>null];
out_json([
  'ok' => false,
  'error' => 'No match from Places or Geocoding; review near candidates',
  'near_candidates' => array_slice($nearAll, 0, 10),
  'normalized_input' => $needleNorm,
  'hint' => 'Provide GOOGLE_API_KEY environment variable to enable API lookups.',
  'final_ids' => $final_ids
], 404);

