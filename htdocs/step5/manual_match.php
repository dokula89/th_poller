<?php
// --- Lightweight AJAX endpoints for UI preview/apply ---
if (isset($_GET['ajax'])) {
  header_remove('Content-Type');

  // Minimal env/DB bootstrap (duplicates a tiny bit from below to keep this self-contained)
  if (file_exists(__DIR__.'/.env')) {
    foreach (file(__DIR__.'/.env', FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES) as $line) {
      if (strpos($line,'=')!==false){ list($k,$v)=explode('=',$line,2); putenv(trim($k).'='.trim($v)); }
    }
  }
  $DB_HOST = getenv('DB_HOST') ?: '127.0.0.1';
  $DB_USER = getenv('DB_USER') ?: 'seattlelisted_usr';
  $DB_PASS = getenv('DB_PASS') ?: 'T@5z6^pl}';
  $DB_NAME = getenv('DB_NAME') ?: 'offta';
  $DB_PORT = (int)(getenv('DB_PORT') ?: 3306);
  $db = @new mysqli($DB_HOST,$DB_USER,$DB_PASS,$DB_NAME,$DB_PORT);
  if ($db && !$db->connect_errno) { $db->set_charset('utf8mb4'); }

  function ajax_json($arr, $code = 200){
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($arr, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
    exit;
  }
  function http_get_json_ajax(string $url, int $timeout = 20): ?array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
      CURLOPT_RETURNTRANSFER => 1,
      CURLOPT_CONNECTTIMEOUT => 10,
      CURLOPT_TIMEOUT => $timeout,
      CURLOPT_SSL_VERIFYPEER => 0,
      CURLOPT_SSL_VERIFYHOST => 0,
      CURLOPT_USERAGENT => 'manual_match_ajax/1.0',
    ]);
    $raw = curl_exec($ch);
    curl_close($ch);
    if ($raw === false || $raw === null) return ['ok'=>false,'error'=>'curl_failed'];
    $j = json_decode($raw, true);
    if (is_array($j)) return $j;
    return ['ok'=>false, 'error'=>'non_json_response', 'sample'=>substr($raw,0,120)];
  }

  $ajax = $_GET['ajax'];

  if ($ajax === 'places_preview') {
    $addr   = trim((string)($_GET['addr'] ?? ''));
    $region = $_GET['region'] ?? 'us';
    $finder = $_GET['finder_url'] ?? ((isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https://' : 'http://')
                      . ($_SERVER['HTTP_HOST'] ?? 'localhost')
                      . '/find_or_create_place.php');
    $incDet = isset($_GET['include_full_details']) && in_array(strtolower((string)$_GET['include_full_details']), ['1','true','yes']) ? '1' : '0';
    $debug  = isset($_GET['debug']) && in_array(strtolower((string)$_GET['debug']), ['1','true','yes']) ? '1' : '0';

    if ($addr === '') ajax_json(['ok'=>false,'error'=>'Missing addr'],400);

    // Try ordered variants
    $variants = [
      ['q' => $addr.' apartment building',  'label' => 'apt_bldg'],
      ['q' => $addr.' property management', 'label' => 'prop_mgmt'],
      ['q' => $addr.' point of interest',   'label' => 'poi'],
      ['q' => $addr,                        'label' => 'plain'],
    ];
    $results = [];
    $best = null;

    foreach ($variants as $v) {
      $query = http_build_query([
        'address' => $v['q'],
        'region'  => $region,
        'include_full_details' => $incDet,
        'debug'   => $debug
      ]);
      $url = $finder.(str_contains($finder,'?') ? '&' : '?').$query;
      $resp = http_get_json_ajax($url);
      $results[] = ['label'=>$v['label'], 'query'=>$v['q'], 'response'=>$resp];
      if ($resp && !empty($resp['ok'])) {
        $src = $resp['result']['source'] ?? '';
        if ($src === 'google_places' || $src === 'google_addresses') {
          $best = $resp;
          break;
        }
        if ($best === null) $best = $resp;
      }
    }

    ajax_json([
      'ok' => true,
      'addr' => $addr,
      'finder' => $finder,
      'best' => $best,
      'tries' => $results
    ]);
  }

  if ($ajax === 'apply_match') {
    if (!$db || $db->connect_errno) ajax_json(['ok'=>false,'error'=>'DB unavailable'],500);
    $place_id   = trim((string)($_POST['place_id'] ?? $_GET['place_id'] ?? ''));
    $listing_id = (int)($_POST['listing_id'] ?? $_GET['listing_id'] ?? 0);
    if ($place_id === '' || $listing_id <= 0) ajax_json(['ok'=>false,'error'=>'Missing place_id or listing_id'],400);

    // Ensure GA exists (insert minimal if needed)
    $ga_id = null;
    if ($stmt = $db->prepare('SELECT id FROM google_addresses WHERE place_id = ? LIMIT 1')) {
      $stmt->bind_param('s', $place_id);
      $stmt->execute();
      $r = $stmt->get_result();
      if ($row = $r?->fetch_assoc()) $ga_id = (int)$row['id'];
      $stmt->close();
    }
    if ($ga_id === null) {
      // Minimal insert
      $ins = $db->prepare("INSERT INTO google_addresses (place_id, source, time) VALUES (?, 'manual_match', UNIX_TIMESTAMP())");
      if ($ins) {
        $ins->bind_param('s', $place_id);
        $ok = $ins->execute();
        if ($ok) $ga_id = (int)$ins->insert_id;
        $ins->close();
      }
      if ($ga_id === null) ajax_json(['ok'=>false,'error'=>'Failed to insert google_addresses','mysql_error'=>$db->error],500);
    }

    // Update apartment_listings
    $upd = $db->prepare("UPDATE apartment_listings SET google_addresses_id = ?, network_id = IFNULL(network_id,1) WHERE id = ?");
    if (!$upd) ajax_json(['ok'=>false,'error'=>'Prepare failed','mysql_error'=>$db->error],500);
    $upd->bind_param('ii', $ga_id, $listing_id);
    $upd->execute();
    $aff = $upd->affected_rows;
    $upd->close();

    ajax_json(['ok'=>true, 'listing_id'=>$listing_id, 'google_addresses_id'=>$ga_id, 'affected'=>$aff]);
  }

  ajax_json(['ok'=>false,'error'=>'Unknown ajax action'],400);
}
 $__MM_T0 = microtime(true);

// --- DB error bucket and helpers ---
$__DB_ERR = '';
function db_set_err(string $m){
  global $__DB_ERR; $__DB_ERR = $m;
}
function db_get_err(): string{
  global $__DB_ERR; return $__DB_ERR;
}
/**
 * manual_match_from_json.php
 *
 * Reads a JSON file of records, extracts addresses, calls find_or_create_place.php to match,
 * and produces a summary (browser output + JSON & CSV reports).
 *
 * UPDATED: Now properly extracts GA ID, GP ID, Listing ID, and KC from API responses.
 * Default limit is set to 5 results for testing.
 *
 * Default JSON path:
 *   /home/daniel/api/trustyhousing.com/manual_upload/json_uploads/chatgpt_extract.json
 *
 * URL params (optional):
 *   ?path=/custom/file.json
 *   &region=us
 *   &limit=5              (max items to process; default 5)
 *   &offset=0             (skip first N)
 *   &include_full_details=0|1  (pass-through to finder; default 0 here)
 *   &debug=0|1            (pass-through to finder; default 0 here)
 *   &finder_url=https://YOUR-HOST/find_or_create_place.php
 *
 * Output files are written alongside the input file:
 *   - {basename}.matches.json
 *   - {basename}.matches.csv
 */

//////////////////////
// Config (overridable by GET)
//////////////////////
$DEFAULT_JSON_PATH = '/home/daniel/api/trustyhousing.com/manual_upload/json_uploads/chatgpt_extract.json';

// Where your finder lives (absolute URL). Adjust host/path if needed.
$DEFAULT_FINDER_URL = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https://' : 'http://')
                    . ($_SERVER['HTTP_HOST'] ?? 'localhost')
                    . '/find_or_create_place.php';

// Inputs
$path    = $_GET['path']    ?? $DEFAULT_JSON_PATH;
$region  = $_GET['region']  ?? 'us';
$limit   = isset($_GET['limit'])  ? max(0, (int)$_GET['limit'])   : 5;   // Default to 5 results
$offset  = isset($_GET['offset']) ? max(0, (int)$_GET['offset'])  : 0;
$incDet  = isset($_GET['include_full_details']) ? (in_array(strtolower($_GET['include_full_details']), ['1','true','yes']) ? 1 : 0) : 0;
$debug   = isset($_GET['debug'])  ? (in_array(strtolower($_GET['debug']), ['1','true','yes']) ? 1 : 0) : 0;
$finder  = $_GET['finder_url'] ?? $DEFAULT_FINDER_URL;

// Basic HTML header
header('Content-Type: text/html; charset=utf-8');
echo "<!doctype html><meta charset='utf-8'><title>manual_match_from_json</title>";
echo "<style>
body{font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial}
code{background:#f6f8fa;padding:2px 4px;border-radius:4px}
pre{background:#f6f8fa;padding:10px;border-radius:6px;overflow:auto}
small.mono{font-family:ui-monospace,Consolas,Monaco,monospace;color:#666}
table{border-collapse:collapse;margin-top:10px;font-size:11px;width:100%;table-layout:auto}
td,th{border:1px solid #ddd;padding:4px 6px;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge{display:inline-block;padding:2px 6px;border-radius:12px;background:#eee;margin-left:6px}
.ok{color:#0a6}
.err{color:#b00}
tr[data-response]{cursor:help;position:relative}
tr[data-response]:hover{background:#f9f9f9}
tr[data-response]:hover::after{
  content:attr(data-response);
  position:absolute;
  left:100%;
  top:50%;
  transform:translateY(-50%);
  z-index:1000;
  background:#2d2d2d;
  color:#f8f8f2;
  padding:12px;
  border-radius:4px;
  font-family:ui-monospace,Consolas,Monaco,monospace;
  font-size:11px;
  line-height:1.4;
  white-space:pre;
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
  max-width:600px;
  max-height:500px;
  overflow:auto;
  margin-left:10px;
  pointer-events:none;
}
</style>";
echo "<script>
function mm_qs(k){return new URLSearchParams(window.location.search).get(k)||'';}
async function mm_preview(idx, addr){
  const row = document.getElementById('mm-row-'+idx);
  const out = document.getElementById('mm-preview-'+idx);
  out.textContent = 'Loading…';
  const params = new URLSearchParams({
    ajax:'places_preview',
    addr:addr,
    region:mm_qs('region')||'us',
    finder_url: mm_qs('finder_url') || '',
    include_full_details: '1',
    debug: mm_qs('debug')||'0'
  });
  const res = await fetch(location.pathname+'?'+params.toString());
  const js = await res.json();
  if(!js.ok){ out.textContent = 'Error: '+(js.error||'unknown'); return; }
  // Try to get a place_id to stage for apply
  let pid = '';
  if (js.best && js.best.result){
    pid = js.best.result.place_id || (js.best.best_place_id||'');
  }
  row.dataset.placeId = pid;

  // Populate GA / GP / Listing / KC cells from finder final_ids (if present)
  try {
    const best = js.best || null;
    if (best) {
      const f = best.final_ids || (best.result && best.result.final_ids) || null;
      const top_ga = best.google_addresses_id || (best.result && best.result.google_addresses_id) || null;
      const top_gp = best.google_places_id || (best.result && best.result.google_places_id) || null;
      const gaCell = document.getElementById('mm-ga-'+idx);
      const gpCell = document.getElementById('mm-gp-'+idx);
      const listCell = document.getElementById('mm-listing-'+idx);
      const kcCell = document.getElementById('mm-kc-'+idx);
      const gaVal = f && (f.google_addresses_id !== undefined) ? f.google_addresses_id : top_ga;
      const gpVal = f && (f.google_places_id !== undefined) ? f.google_places_id : top_gp;
      const listVal = f && (f.king_county_parcels_id !== undefined) ? f.king_county_parcels_id : (best.listing_id || (best.result && best.result.listing_id));
      if (gaCell) gaCell.textContent = gaVal !== null && gaVal !== undefined ? String(gaVal) : '';
      if (gpCell) gpCell.textContent = gpVal !== null && gpVal !== undefined ? String(gpVal) : '';
      if (listCell) listCell.textContent = listVal !== null && listVal !== undefined ? String(listVal) : '';
      if (kcCell) kcCell.textContent = (f && f.king_county_parcels_id !== undefined) ? String(f.king_county_parcels_id) : '';
    }
  } catch (e) { console.warn('mm_preview populate failed', e); }

  out.textContent = JSON.stringify(js, null, 2);
}
async function mm_apply(idx, listingId){
  const row = document.getElementById('mm-row-'+idx);
  const pid = row.dataset.placeId||'';
  const out = document.getElementById('mm-preview-'+idx);
  if(!pid){ out.textContent = 'No place_id staged. Click Preview first.'; return; }
  const form = new FormData();
  form.append('ajax','apply_match');
  form.append('place_id', pid);
  form.append('listing_id', String(listingId));
  const res = await fetch(location.pathname+'?ajax=apply_match', {method:'POST', body:form});
  const js = await res.json();
  if(!js.ok){ out.textContent = 'Apply failed: '+(js.error||''); return; }
  // Update GA/Action cells inline
  const gaCell = document.getElementById('mm-ga-'+idx);
  const actionCell = document.getElementById('mm-action-'+idx);
  if(gaCell) gaCell.textContent = String(js.google_addresses_id||'');
  if(actionCell) actionCell.textContent = 'linked GA '+(js.google_addresses_id||'')+' to listing #'+(js.listing_id||'');
  out.textContent = 'Applied OK. GA '+(js.google_addresses_id||'')+' linked.';
}
</script>";

///////////////////////
// DB Config (for google_addresses matching by place_id)
///////////////////////
// Load .env if present
if (file_exists(__DIR__.'/.env')) {
  foreach (file(__DIR__.'/.env', FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES) as $line) {
    if (strpos($line,'=')!==false){ list($k,$v)=explode('=',$line,2); putenv(trim($k).'='.trim($v)); }
  }
}
$DB_HOST = getenv('DB_HOST') ?: '127.0.0.1';
$DB_USER = getenv('DB_USER') ?: 'seattlelisted_usr';
$DB_PASS = getenv('DB_PASS') ?: 'T@5z6^pl}';
$DB_NAME = getenv('DB_NAME') ?: 'offta';
$DB_PORT = (int)(getenv('DB_PORT') ?: 3306);

// Open connection (best-effort; if it fails we still continue with web finder)
$ga_db = @new mysqli($DB_HOST,$DB_USER,$DB_PASS,$DB_NAME,$DB_PORT);
if (function_exists('mysqli_report')) { mysqli_report(MYSQLI_REPORT_OFF); }
if ($ga_db && !$ga_db->connect_errno) {
  $ga_db->set_charset('utf8mb4');
} else {
  $ga_db = null; // fallback to web-only
}

// ===== Apartment listings helpers =====
// Normalize an address for exact comparison (collapse case, punctuation, and common street words)
function norm_addr_exact(string $s): string {
  $u = strtoupper(trim($s));
  // Standardize common street suffixes and directionals
  $map = [
    ' STREET' => ' ST', ' AVENUE' => ' AVE', ' BOULEVARD' => ' BLVD', ' ROAD' => ' RD',
    ' DRIVE' => ' DR', ' LANE' => ' LN', ' COURT' => ' CT', ' TERRACE' => ' TER', ' PLACE' => ' PL',
    ' HIGHWAY' => ' HWY', ' PARKWAY' => ' PKWY', ' NORTH' => ' N', ' SOUTH' => ' S', ' EAST' => ' E', ' WEST' => ' W'
  ];
  foreach ($map as $k => $v) { $u = str_replace($k, $v, $u); }
  // Remove punctuation and spaces, normalize unit marker
  $u = str_replace(['#',',','.',"\n","\r","\t"," " ], '', $u);
  return $u;
}

function db_find_listing_id_by_full_address(?mysqli $db, string $fullAddr): ?int {
  if (!$db || $fullAddr==='') return null;
  $needle = norm_addr_exact($fullAddr);
  // Compare against a similarly normalized DB expression
  $sql = "SELECT id, full_address FROM apartment_listings WHERE 
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(full_address),'#',''),',',''),'.',''), ' ', ''), CHAR(10), ''), CHAR(13), '') = ?
          LIMIT 1";
  $stmt = $db->prepare($sql);
  if (!$stmt) return null;
  $stmt->bind_param('s', $needle);
  $stmt->execute();
  $res = $stmt->get_result();
  $row = $res?->fetch_assoc();
  $stmt->close();
  if ($row) return (int)$row['id'];
  // If not found via SQL expression, do a fallback scan on a small candidate set containing the numeric house number
  if (preg_match('~^\s*([0-9]+)~', $fullAddr, $m)) {
    $num = $m[1];
    $stmt2 = $db->prepare("SELECT id, full_address FROM apartment_listings WHERE full_address LIKE CONCAT(?,'%') LIMIT 50");
    if ($stmt2) {
      $stmt2->bind_param('s', $num);
      $stmt2->execute();
      $r2 = $stmt2->get_result();
      while ($cand = ($r2?->fetch_assoc() ?: null)) {
        if (norm_addr_exact($cand['full_address'] ?? '') === $needle) {
          $stmt2->close();
          return (int)$cand['id'];
        }
      }
      $stmt2->close();
    }
  }
  return null;
}
function norm_price_to_int($val): ?int {
  if ($val===null) return null;
  $s = preg_replace('~[^0-9]~','', (string)$val);
  return $s!=='' ? (int)$s : null;
}
function to_int_or_null($v): ?int { return ($v===null || $v==='') ? null : (int)$v; }
function to_float_or_null($v): ?float { return ($v===null || $v==='') ? null : (float)$v; }
function db_insert_apartment_listing(mysqli $db, array $d): ?int {
  $sql = 'INSERT INTO apartment_listings (
    user_id, active, propertyType, type, unit_number, deal, title, Lease_Length, Pool, Gym, MFTE, Managed,
    bedrooms, bathrooms, sqft, price, img_urls, floorplan_url, available, other_details, details, available_date,
    network, network_id, amenities, Balcony, Cats, Dogs, Parking, parking_fee, description, Building_Name, Latitude, Longitude,
    suburb, street, full_address, city, state, country, listing_website, apply_now_link, phone_contact, email_contact,
    name_contact, google_addresses_id, google_places_id, time_created, time_updated
  ) VALUES (
    0, "yes", NULL, "For-Rent", ?, NULL, ?, NULL, NULL, NULL, NULL, NULL,
    ?, ?, ?, ?, ?, NULL, "NOW", NULL, NULL, ?,
    NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL, NULL, NULL,
    NULL, ?, ?, ?, ?, "USA", ?, ?, NULL, NULL,
    NULL, ?, ?, NOW(), NOW()
  )';
  $st = $db->prepare($sql);
  if (!$st) { db_set_err('prepare: '.($db->error ?: 'unknown')); return null; }
  $st->bind_param(
    'sssssssssssssssss',
    $d['unit_number'], $d['title'],
    $d['bedrooms'], $d['bathrooms'], $d['sqft'], $d['price'], $d['img_urls'],
    $d['available_date'],
    $d['description'],
    $d['street'], $d['full_address'], $d['city'], $d['state'],
    $d['listing_website'], $d['apply_now_link'],
    $d['google_addresses_id'], $d['google_places_id']
  );
  // NOTE: Using s (string) for simplicity; MySQL will coerce. If you prefer strict types, adjust bind types accordingly.
  $ok = $st->execute();
  if (!$ok) { db_set_err('execute: '.($st->error ?: $db->error ?: 'unknown')); }
  $id = $ok ? $st->insert_id : null;
  $st->close();
  return $id ? (int)$id : null;
}
function db_update_apartment_listing(mysqli $db, int $id, array $d): bool {
  $sql = 'UPDATE apartment_listings SET
    unit_number=?, title=?, bedrooms=?, bathrooms=?, sqft=?, price=?, img_urls=?, available_date=?,
    description=?, street=?, full_address=?, city=?, state=?, listing_website=?, apply_now_link=?,
    network_id=1, google_addresses_id=?, google_places_id=?, time_updated=NOW()
    WHERE id=?';
  $st = $db->prepare($sql);
  if (!$st) { db_set_err('prepare: '.($db->error ?: 'unknown')); return false; }
  $st->bind_param(
    'ssssissssssssssssi',
    $d['unit_number'], $d['title'],
    $d['bedrooms'], $d['bathrooms'], $d['sqft'], $d['price'], $d['img_urls'], $d['available_date'],
    $d['description'], $d['street'], $d['full_address'], $d['city'], $d['state'],
    $d['listing_website'], $d['apply_now_link'],
    $d['google_addresses_id'], $d['google_places_id'], $id
  );
  $ok = $st->execute();
  if (!$ok) { db_set_err('execute: '.($st->error ?: $db->error ?: 'unknown')); }
  $st->close();
  return (bool)$ok;
}

// Helper: extract place_id from a generic JSON item
function extract_place_id(array $item): ?string {
  $keys = ['Place_Id','place_id','pid','google_place_id','PlaceID','PlaceId'];
  foreach ($keys as $k) {
    if (!empty($item[$k]) && is_string($item[$k])) {
      return trim($item[$k]);
    }
  }
  return null;
}
// Helper: GA id by place_id
function db_get_ga_id_by_place_id(?mysqli $db, string $pid): ?int {
  if (!$db) return null;
  $q = $db->prepare('SELECT id FROM google_addresses WHERE place_id = ? LIMIT 1');
  if (!$q) return null;
  $q->bind_param('s',$pid);
  $q->execute();
  $r = $q->get_result();
  $row = $r?->fetch_assoc();
  $q->close();
  return $row ? (int)$row['id'] : null;
}

//////////////////////
// Helpers
//////////////////////

function read_json_file(string $file) {
  if (!file_exists($file)) return [null, "File not found: $file"];
  $raw = file_get_contents($file);
  if ($raw === false) return [null, "Failed to read: $file"];
  $data = json_decode($raw, true);
  if (!is_array($data)) return [null, "Invalid JSON array in: $file"];
  return [$data, null];
}

/** Return the Google-derived address from JSON if present; otherwise fall back to prior heuristics. */
function extract_google_address(array $item): ?string {
  if (!empty($item['google_address']) && is_string($item['google_address'])) {
    return trim($item['google_address']);
  }
  // Fallbacks (kept from previous implementation)
  $google_keys = [
    'Google_Maps_Address','GoogleAddress','Google_Address','GoogleFormattedAddress',
    'Fulladdress','FullAddress','formatted_address','formattedAddress',
    'full_address'
  ];
  foreach ($google_keys as $k) {
    if (!empty($item[$k]) && is_string($item[$k])) {
      return trim($item[$k]);
    }
  }
  $generic_keys = ['address','Address','location','Location'];
  foreach ($generic_keys as $k) {
    if (!empty($item[$k]) && is_string($item[$k])) {
      return trim($item[$k]);
    }
  }
  $parts = [];
  foreach (['street','Street','line1','address1'] as $k) if (!empty($item[$k])) $parts[] = $item[$k];
  $city = $item['city'] ?? $item['City'] ?? null;
  $st   = $item['state'] ?? $item['State'] ?? null;
  $zip  = $item['zip'] ?? $item['Zip'] ?? $item['postal_code'] ?? null;
  if ($city || $st || $zip) {
    $csz = trim(trim(($city ?? '').', '.($st ?? '')), ', ');
    if ($zip) $csz = trim($csz.' '.$zip);
    if ($csz !== '') $parts[] = $csz;
  }
  $addr = trim(implode(', ', array_filter($parts, fn($v)=>trim((string)$v)!=='')));
  return $addr !== '' ? $addr : null;
}

/** Simple GET JSON via cURL */
function http_get_json(string $url, int $timeout = 20): ?array {
  $ch = curl_init($url);
  curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => 1,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT => $timeout,
    CURLOPT_SSL_VERIFYPEER => 0, // you may set to 1 if you have proper certs
    CURLOPT_SSL_VERIFYHOST => 0,
    CURLOPT_USERAGENT => 'manual_match_from_json/1.0',
  ]);
  $raw = curl_exec($ch);
  $err = curl_error($ch);
  curl_close($ch);
  if ($raw === false || $raw === null) return null;
  $j = json_decode($raw, true);
  return is_array($j) ? $j : null;
}

/** Build ordered text queries for Places: apt building → property management → point of interest → plain */
function build_place_search_variants(string $base): array {
  $base = trim($base);
  return [
    ['q' => $base.' apartment building',   'label' => 'apt_bldg'],
    ['q' => $base.' property management',  'label' => 'prop_mgmt'],
    ['q' => $base.' point of interest',    'label' => 'poi'],
    ['q' => $base,                         'label' => 'plain'],
  ];
}

/** Write CSV rows */
function write_csv(string $path, array $rows, array $headers): bool {
  $fp = fopen($path, 'w');
  if (!$fp) return false;
  fputcsv($fp, $headers);
  foreach ($rows as $r) {
    $line = [];
    foreach ($headers as $h) $line[] = $r[$h] ?? '';
    fputcsv($fp, $line);
  }
  fclose($fp);
  return true;
}

//////////////////////
// Load input JSON
//////////////////////
[$items, $err] = read_json_file($path);
if ($err) {
  echo "<p class='err'><b>Error:</b> ".htmlspecialchars($err)."</p>";
  exit;
}

$total = count($items);
$end   = $limit ? min($total, $offset + $limit) : $total;

echo "<h2>Manual match from JSON</h2>";
echo "<p>Source: <code>".htmlspecialchars($path)."</code><br>";
echo "Finder: <code>".htmlspecialchars($finder)."</code><br>";
echo "Region: <code>".htmlspecialchars($region)."</code> ";
echo "<span class='badge'>items: $total</span>";
if ($offset) echo " <span class='badge'>offset: $offset</span>";
if ($limit)  echo " <span class='badge'>limit: $limit</span>";
echo " <span class='badge'>include_full_details: $incDet</span>";
echo " <span class='badge'>debug: $debug</span></p>";

//////////////////////
// Process
//////////////////////
$summary = [
  'source_path' => $path,
  'finder_url'  => $finder,
  'region'      => $region,
  'started_at'  => date('c'),
  'count_total' => $total,
  'count_scanned'=> 0,
  'count_with_address' => 0,
  'ok_matches'  => 0,
  'preview_matches' => 0,
  'no_matches'  => 0,
  'errors'      => 0,
  'rows'        => [],
];

echo "<table style='width:100%;font-size:11px'><tr>"
  . "<th>#</th>"
  . "<th>Title</th>"
  . "<th>Unit</th>"
  . "<th>Bed</th>"
  . "<th>Bath</th>"
  . "<th>Sqft</th>"
  . "<th>Price</th>"
  . "<th>Street</th>"
  . "<th>City</th>"
  . "<th>State</th>"
  . "<th>Avail Date</th>"
  . "<th>Google Address</th>"
  . "<th>Place ID</th>"
  . "<th>Result</th>"
  . "<th>GA ID</th>"
  . "<th>GP ID</th>"
  . "<th>Listing ID</th>"
  . "<th>KC</th>"
  . "<th>Action</th>"
  . "</tr>";

for ($i = $offset; $i < $end; $i++) {
  $summary['count_scanned']++;
  $item = $items[$i];

  // Prefer matching via google_addresses by place_id if present in JSON
  $json_pid = extract_place_id($item);
  if ($json_pid) {
    $ga_match_id = db_get_ga_id_by_place_id($ga_db, $json_pid);
    if ($ga_match_id) {
      // Treat as a confirmed match; upsert apartment_listings using exact full_address from JSON if present
      $addr = extract_google_address($item) ?? '';
      $full_address_json = trim((string)($item['full_address'] ?? $addr));
      $listing_id = $full_address_json !== '' ? db_find_listing_id_by_full_address($ga_db, $full_address_json) : null;

      $gp_id = ''; // unknown in this path
      $kc_id = ''; // finder not called here

      $data = [
        'unit_number'        => (string)($item['unit'] ?? $item['unit_number'] ?? ''),
        'title'              => (string)($item['title'] ?? ''),
        'bedrooms'           => to_int_or_null($item['bedrooms'] ?? null),
        'bathrooms'          => to_int_or_null($item['bathrooms'] ?? null),
        'sqft'               => to_int_or_null($item['sqft'] ?? null),
        'price'              => norm_price_to_int($item['price'] ?? null),
        'img_urls'           => (string)($item['img_urls'] ?? ''),
        'available_date'     => (string)($item['available_date'] ?? ''),
        'description'        => (string)($item['description'] ?? ''),
        'street'             => (string)($item['street'] ?? ''),
        'full_address'       => $full_address_json,
        'city'               => (string)($item['city'] ?? ''),
        'state'              => (string)($item['state'] ?? ''),
        'listing_website'    => (string)($item['listing_website'] ?? ''),
        'apply_now_link'     => (string)($item['apply_now_link'] ?? ''),
        'google_addresses_id'=> (int)$ga_match_id,
        'google_places_id'   => $gp_id !== '' ? (int)$gp_id : null,
      ];

      $action = 'none';
      if ($ga_db) {
        if ($listing_id) {
          $ok = db_update_apartment_listing($ga_db, $listing_id, $data);
          $action = $ok ? ('updated #'.$listing_id) : ('update_failed: '.db_get_err());
        } else {
          $new_id = db_insert_apartment_listing($ga_db, $data);
          $action = $new_id ? ('inserted #'.$new_id) : ('insert_failed: '.db_get_err());
        }
      } else {
        $action = 'db_unavailable';
      }

      $listing_row_id = $listing_id ?: ($new_id ?? null);
      $summary['ok_matches']++;
      $summary['rows'][] = [
        'index'   => $i,
        'address' => $addr,
        'status'  => 'ga_match_by_place_id',
        'ga_id'   => $ga_match_id,
        'gp_id'   => $gp_id,
        'kc_id'   => $kc_id,
        'finder_url' => '',
        'place_id' => $json_pid,
        'action'  => $action,
        'listing_id' => $listing_row_id,
      ];

      echo "<tr id='mm-row-".$i."'><td>".($i+1)."</td>"
        . "<td>".htmlspecialchars((string)($item['title'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['unit'] ?? $item['unit_number'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['bedrooms'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['bathrooms'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['sqft'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['price'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['street'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['city'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['state'] ?? ''))."</td>"
        . "<td>".htmlspecialchars((string)($item['available_date'] ?? ''))."</td>"
        . "<td>".htmlspecialchars($addr)."</td>"
        . "<td>".htmlspecialchars($json_pid)."</td>"
        . "<td class='ok'>ga_match_by_place_id</td>"
        . "<td id='mm-ga-".$i."'>".htmlspecialchars((string)$ga_match_id)."</td>"
        . "<td id='mm-gp-".$i."'>".htmlspecialchars((string)$gp_id)."</td>"
        . "<td id='mm-listing-".$i."'>".htmlspecialchars($listing_row_id !== null ? (string)$listing_row_id : '')."</td>"
        . "<td id='mm-kc-".$i."'>".htmlspecialchars((string)$kc_id)."</td>"
        . "<td id='mm-action-".$i."'>".htmlspecialchars($action)."</td>"
         . "</tr>";
      continue;
    }
    // If place_id present but not found in GA, we'll still try the finder below
  }

  $addr = extract_google_address($item);
  if (!$addr) {
    $summary['rows'][] = [
      'index' => $i,
      'address' => '',
      'status' => 'no_address',
      'ga_id' => '',
      'gp_id' => '',
      'kc_id' => '',
      'message' => 'No address fields found',
      'place_id' => $json_pid ?? ''
    ];
  echo "<tr id='mm-row-".$i."'><td>".($i+1)."</td>"
      . "<td>".htmlspecialchars((string)($item['title'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['unit'] ?? $item['unit_number'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['bedrooms'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['bathrooms'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['sqft'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['price'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['street'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['city'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['state'] ?? ''))."</td>"
      . "<td>".htmlspecialchars((string)($item['available_date'] ?? ''))."</td>"
      . "<td><i class='err'>[no address]</i></td>"
      . "<td>".htmlspecialchars($json_pid ?? '')."</td>"
      . "<td class='err'>skip</td>"
      . "<td id='mm-ga-".$i."'></td>"
      . "<td id='mm-gp-".$i."'></td>"
      . "<td id='mm-listing-".$i."'></td>"
      . "<td id='mm-kc-".$i."'></td>"
      . "<td id='mm-action-".$i."'></td>"
      . "</tr>";
    continue;
  }
  $summary['count_with_address']++;

  // === EARLY UPSERT by exact full_address (skip finder if we can) ===
  $full_address_json = trim((string)($item['full_address'] ?? $addr));
  $listing_id_pre = $full_address_json !== '' ? db_find_listing_id_by_full_address($ga_db, $full_address_json) : null;

  if ($listing_id_pre) {
    // Call the finder API even for existing listings
    $query = http_build_query([
      'address' => $addr,
      'region'  => $region,
      'include_full_details' => $incDet ? '1' : '0',
      'debug'   => $debug ? '1' : '0',
      'apartment_listings_id' => $listing_id_pre,
    ]);
    $url = $finder.(str_contains($finder,'?') ? '&' : '?').$query;
    $resp = http_get_json($url);

    $ga_id = $gp_id = $kc_id = '';
    $statusTxt = 'error'; $class = 'err';
    $json_pid_pre = '';
    
    if (is_array($resp) && !empty($resp['ok'])) {
      $result_src = $resp['result']['source'] ?? '';
      $final = $resp['final_ids'] ?? [];
      $ga_id = $final['google_addresses_id'] ?? '';
      $gp_id = $final['google_places_id'] ?? '';
      $kc_id = $final['king_county_parcels_id'] ?? '';
      $json_pid_pre = $resp['result']['place_id'] ?? '';
      
      $skipped = $resp['skipped_api_calls'] ?? false;
      $tries_count = count($resp['tries'] ?? []);
      $data_fresh = $resp['result']['data_fresh'] ?? false;
      
      $statusTxt = $result_src . ($skipped ? ' (fresh, no API)' : ' (API:'.$tries_count.')');
      $class = ($result_src === 'google_places' || $result_src === 'google_addresses') ? 'ok' : '';
      
      $summary['ok_matches']++;
    } else {
      $summary['no_matches']++;
    }
    
    $action_pre = $resp['apartment_listings_update']['updated'] ?? false ? 'updated #'.$listing_id_pre : 'no update';

    $formatted_json = json_encode($resp ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    
    echo "<tr id='mm-row-".$i."' data-response='".htmlspecialchars($formatted_json, ENT_QUOTES)."'><td>".($i+1)."</td>"
       . "<td>".htmlspecialchars((string)($item['title'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['unit'] ?? $item['unit_number'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['bedrooms'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['bathrooms'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['sqft'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['price'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['street'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['city'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['state'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['available_date'] ?? ''))."</td>"
       . "<td>".htmlspecialchars($addr)."</td>"
       . "<td>".htmlspecialchars($json_pid_pre)."</td>"
       . "<td class='".$class."'>".htmlspecialchars($statusTxt)."</td>"
  . "<td id='mm-ga-".$i."'>".htmlspecialchars((string)$ga_id)."</td>"
  . "<td id='mm-gp-".$i."'>".htmlspecialchars((string)$gp_id)."</td>"
  . "<td id='mm-listing-".$i."'>".htmlspecialchars((string)$listing_id_pre)."</td>"
  . "<td id='mm-kc-".$i."'>".htmlspecialchars((string)$kc_id)."</td>"
       . "<td id='mm-action-".$i."'>".htmlspecialchars($action_pre)."</td>"
       . "</tr>";

    continue;
  } else {
    // No existing listing → call finder first, then insert
    $query = http_build_query([
      'address' => $addr,
      'region'  => $region,
      'include_full_details' => $incDet ? '1' : '0',
      'debug'   => $debug ? '1' : '0',
    ]);
    $url = $finder.(str_contains($finder,'?') ? '&' : '?').$query;
    $resp = http_get_json($url);

    $ga_id = $gp_id = $kc_id = '';
    $statusTxt = 'error'; $class = 'err';
    $json_pid_pre = '';
    
    if (is_array($resp) && !empty($resp['ok'])) {
      $result_src = $resp['result']['source'] ?? '';
      $final = $resp['final_ids'] ?? [];
      $ga_id = $final['google_addresses_id'] ?? '';
      $gp_id = $final['google_places_id'] ?? '';
      $kc_id = $final['king_county_parcels_id'] ?? '';
      $json_pid_pre = $resp['result']['place_id'] ?? '';
      
      $skipped = $resp['skipped_api_calls'] ?? false;
      $tries_count = count($resp['tries'] ?? []);
      
      $statusTxt = $result_src . ($skipped ? ' (fresh, no API)' : ' (API:'.$tries_count.')');
      $class = ($result_src === 'google_places' || $result_src === 'google_addresses') ? 'ok' : '';
      
      $summary['ok_matches']++;
    } else {
      $summary['no_matches']++;
    }

    // Insert new listing with finder results
    $data_insert_pre = [
      'unit_number'        => (string)($item['unit'] ?? $item['unit_number'] ?? ''),
      'title'              => (string)($item['title'] ?? ''),
      'bedrooms'           => to_int_or_null($item['bedrooms'] ?? null),
      'bathrooms'          => to_int_or_null($item['bathrooms'] ?? null),
      'sqft'               => to_int_or_null($item['sqft'] ?? null),
      'price'              => norm_price_to_int($item['price'] ?? null),
      'img_urls'           => (string)($item['img_urls'] ?? ''),
      'available_date'     => (string)($item['available_date'] ?? ''),
      'description'        => (string)($item['description'] ?? ''),
      'street'             => (string)($item['street'] ?? ''),
      'full_address'       => $full_address_json,
      'city'               => (string)($item['city'] ?? ''),
      'state'              => (string)($item['state'] ?? ''),
      'listing_website'    => (string)($item['listing_website'] ?? ''),
      'apply_now_link'     => (string)($item['apply_now_link'] ?? ''),
      'google_addresses_id'=> $ga_id !== '' ? (int)$ga_id : null,
      'google_places_id'   => $gp_id !== '' ? (int)$gp_id : null,
    ];
    $new_id_pre = $ga_db ? db_insert_apartment_listing($ga_db, $data_insert_pre) : null;
    $action_pre = $new_id_pre ? ('inserted #'.$new_id_pre) : ($ga_db ? ('insert_failed: '.db_get_err()) : 'db_unavailable');

    $formatted_json = json_encode($resp ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    
    echo "<tr id='mm-row-".$i."' data-response='".htmlspecialchars($formatted_json, ENT_QUOTES)."'><td>".($i+1)."</td>"
       . "<td>".htmlspecialchars((string)($item['title'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['unit'] ?? $item['unit_number'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['bedrooms'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['bathrooms'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['sqft'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['price'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['street'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['city'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['state'] ?? ''))."</td>"
       . "<td>".htmlspecialchars((string)($item['available_date'] ?? ''))."</td>"
       . "<td>".htmlspecialchars($addr)."</td>"
       . "<td>".htmlspecialchars($json_pid_pre)."</td>"
       . "<td class='".$class."'>".htmlspecialchars($statusTxt)."</td>"
  . "<td id='mm-ga-".$i."'>".htmlspecialchars((string)$ga_id)."</td>"
  . "<td id='mm-gp-".$i."'>".htmlspecialchars((string)$gp_id)."</td>"
  . "<td id='mm-listing-".$i."'>".htmlspecialchars($new_id_pre ? (string)$new_id_pre : '')."</td>"
  . "<td id='mm-kc-".$i."'>".htmlspecialchars((string)$kc_id)."</td>"
       . "<td id='mm-action-".$i."'>".htmlspecialchars($action_pre)."</td>"
       . "</tr>";

    continue;
  }

  // Try ordered Places-biased variants: apartment building → property management → POI → plain
  $variants = build_place_search_variants($addr);
  $bestResp = null; $bestStatus = 'error'; $bestClass = 'err';
  $ga_id = $gp_id = $kc_id = ''; $usedLabel = '';
  foreach ($variants as $v) {
    $query = http_build_query([
      'address' => $v['q'],
      'region'  => $region,
      'include_full_details' => $incDet ? '1' : '0',
      'debug'   => $debug ? '1' : '0',
      // 'upsert_ga' => '1', // optional
    ]);
    $url = $finder.(str_contains($finder,'?') ? '&' : '?').$query;
    $resp = http_get_json($url);

    if (is_array($resp) && !empty($resp['ok'])) {
      $result_src = $resp['result']['source'] ?? '';
      $final = $resp['final_ids'] ?? [];
      $ga_id = $final['google_addresses_id'] ?? '';
      $gp_id = $final['google_places_id'] ?? '';
      $kc_id = $final['king_county_parcels_id'] ?? '';
      
      // Also check for direct IDs in the response (for updated/inserted records)
      if (empty($ga_id) && isset($resp['google_addresses_id'])) {
        $ga_id = $resp['google_addresses_id'];
      }
      if (empty($gp_id) && isset($resp['google_places_id'])) {
        $gp_id = $resp['google_places_id'];
      }

      // Accept immediately if it's a real DB-backed match
      if ($result_src === 'google_places' || $result_src === 'google_addresses') {
        $bestResp = $resp; $bestStatus = 'ok ('.$v['label'].')'; $bestClass = 'ok'; $usedLabel = $v['label'];
        $summary['ok_matches']++;
        break;
      }
      // Otherwise keep first preview if we don't have any better yet
      if ($bestResp === null) {
        $bestResp = $resp; $bestStatus = ($result_src ?: 'preview').' ('.$v['label'].')';
        $bestClass = ''; $usedLabel = $v['label'];
        $summary['preview_matches']++;
      }
    }
  }
  if ($bestResp === null) { $summary['no_matches']++; }

  $statusTxt = $bestStatus;
  $class = $bestClass;

  // === UPSERT apartment_listings based on FULL ADDRESS ===
  $full_address_json = trim((string)($item['full_address'] ?? $addr));
  $listing_id_pre = $full_address_json !== '' ? db_find_listing_id_by_full_address($ga_db, $full_address_json) : null;

  if ($listing_id_pre) {
    // If we already have an exact-normalized listing match, upsert with finder results
    $data = [
      'unit_number'        => (string)($item['unit'] ?? $item['unit_number'] ?? ''),
      'title'              => (string)($item['title'] ?? ''),
      'bedrooms'           => to_int_or_null($item['bedrooms'] ?? null),
      'bathrooms'          => to_int_or_null($item['bathrooms'] ?? null),
      'sqft'               => to_int_or_null($item['sqft'] ?? null),
      'price'              => norm_price_to_int($item['price'] ?? null),
      'img_urls'           => (string)($item['img_urls'] ?? ''),
      'available_date'     => (string)($item['available_date'] ?? ''),
      'description'        => (string)($item['description'] ?? ''),
      'street'             => (string)($item['street'] ?? ''),
      'full_address'       => $full_address_json,
      'city'               => (string)($item['city'] ?? ''),
      'state'              => (string)($item['state'] ?? ''),
      'listing_website'    => (string)($item['listing_website'] ?? ''),
      'apply_now_link'     => (string)($item['apply_now_link'] ?? ''),
      'google_addresses_id'=> $ga_id !== '' ? (int)$ga_id : null,
      'google_places_id'   => $gp_id !== '' ? (int)$gp_id : null,
    ];
    $action = 'none';
    if ($ga_db) {
      $ok = db_update_apartment_listing($ga_db, $listing_id_pre, $data);
      $action = $ok ? ('updated #'.$listing_id_pre) : ('update_failed: '.db_get_err());
    } else {
      $action = 'db_unavailable';
    }
    $summary['rows'][] = [
      'index'   => $i,
      'address' => $addr,
      'status'  => $statusTxt,
      'ga_id'   => $ga_id,
      'gp_id'   => $gp_id,
      'kc_id'   => $kc_id,
      'finder_url' => $bestResp ? $url : '',
      'place_id' => $json_pid ?? '',
      'action'  => $action,
      'listing_id' => $listing_id_pre,
    ];
   echo "<tr id='mm-row-".$i."'><td>".($i+1)."</td>"
     . "<td>".htmlspecialchars($addr)."</td>"
     . "<td>".htmlspecialchars($json_pid ?? '')."</td>"
     . "<td class='".$class."'>".htmlspecialchars($statusTxt)."</td>"
     . "<td id='mm-ga-".$i."'>".htmlspecialchars((string)$ga_id)."</td>"
     . "<td id='mm-gp-".$i."'>".htmlspecialchars((string)$gp_id)."</td>"
     . "<td id='mm-listing-".$i."'>".htmlspecialchars((string)$listing_id_pre)."</td>"
     . "<td id='mm-kc-".$i."'>".htmlspecialchars((string)$kc_id)."</td>"
     . "<td id='mm-action-".$i."'>".htmlspecialchars($action)."</td>"
     . "</tr>";
    continue;
  }
  else {
    // If no listing found by full_address, insert with finder results
    $json_pid_pre = extract_place_id($item);
    $ga_from_pid  = $json_pid_pre ? db_get_ga_id_by_place_id($ga_db, $json_pid_pre) : null;
    
    // Use finder results if available, otherwise fall back to place_id lookup
    $final_ga_id = $ga_id !== '' ? (int)$ga_id : $ga_from_pid;
    $final_gp_id = $gp_id !== '' ? (int)$gp_id : null;
    
    $data_insert_pre = [
      'unit_number'        => (string)($item['unit'] ?? $item['unit_number'] ?? ''),
      'title'              => (string)($item['title'] ?? ''),
      'bedrooms'           => to_int_or_null($item['bedrooms'] ?? null),
      'bathrooms'          => to_int_or_null($item['bathrooms'] ?? null),
      'sqft'               => to_int_or_null($item['sqft'] ?? null),
      'price'              => norm_price_to_int($item['price'] ?? null),
      'img_urls'           => (string)($item['img_urls'] ?? ''),
      'available_date'     => (string)($item['available_date'] ?? ''),
      'description'        => (string)($item['description'] ?? ''),
      'street'             => (string)($item['street'] ?? ''),
      'full_address'       => $full_address_json,
      'city'               => (string)($item['city'] ?? ''),
      'state'              => (string)($item['state'] ?? ''),
      'listing_website'    => (string)($item['listing_website'] ?? ''),
      'apply_now_link'     => (string)($item['apply_now_link'] ?? ''),
      'google_addresses_id'=> $final_ga_id,
      'google_places_id'   => $final_gp_id,
    ];
    $new_id_pre = $ga_db ? db_insert_apartment_listing($ga_db, $data_insert_pre) : null;
    $action_pre = $new_id_pre ? ('inserted #'.$new_id_pre.' (finder)') : ($ga_db ? ('insert_failed_finder: '.db_get_err()) : 'db_unavailable');

    $summary['rows'][] = [
      'index'   => $i,
      'address' => $addr,
      'status'  => $statusTxt,
      'ga_id'   => $final_ga_id ?? '',
      'gp_id'   => $final_gp_id ?? '',
      'kc_id'   => $kc_id,
      'finder_url' => $bestResp ? $url : '',
      'place_id' => $json_pid_pre ?? '',
      'action'  => $action_pre,
      'listing_id' => $new_id_pre,
    ];
   echo "<tr id='mm-row-".$i."'><td>".($i+1)."</td>"
     . "<td>".htmlspecialchars($addr)."</td>"
     . "<td>".htmlspecialchars($json_pid_pre ?? '')."</td>"
     . "<td class='".$class."'>".htmlspecialchars($statusTxt)."</td>"
     . "<td id='mm-ga-".$i."'>".htmlspecialchars((string)($final_ga_id ?? ''))."</td>"
     . "<td id='mm-gp-".$i."'>".htmlspecialchars((string)($final_gp_id ?? ''))."</td>"
     . "<td id='mm-listing-".$i."'>".htmlspecialchars($new_id_pre ? (string)$new_id_pre : '')."</td>"
     . "<td id='mm-kc-".$i."'>".htmlspecialchars((string)$kc_id)."</td>"
     . "<td id='mm-action-".$i."'>".htmlspecialchars($action_pre)."</td>"
     . "</tr>";
    continue;
  }
}

echo "</table>";

$elapsed_ms = (int)round((microtime(true) - $__MM_T0) * 1000);

$summary['finished_at'] = date('c');
$summary['elapsed_ms'] = $elapsed_ms;

//////////////////////
// Write reports (JSON + CSV) next to input
//////////////////////
$dir  = dirname($path);
$base = pathinfo($path, PATHINFO_FILENAME);
$jsonOut = $dir . '/' . $base . '.matches.json';
$csvOut  = $dir . '/' . $base . '.matches.csv';

// JSON
file_put_contents($jsonOut, json_encode($summary, JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT));

// CSV (flat)
$csvHeaders = ['index','address','place_id','status','ga_id','gp_id','kc_id','finder_url','action'];
write_csv($csvOut, $summary['rows'], $csvHeaders);

echo "<p><b>Done.</b> <small class='mono'>elapsed: {$elapsed_ms} ms</small></p>";