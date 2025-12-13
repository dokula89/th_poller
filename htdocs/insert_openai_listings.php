<?php
/**
 * insert_openai_listings.php
 * 
 * Inserts apartment listings from the latest OpenAI batch JSON file into the database.
 * Links listings to google_addresses via google_places_id.
 * 
 * Usage: GET /insert_openai_listings.php
 *        GET /insert_openai_listings.php?file=openai_batch_20251212_155655.json
 */

header('Content-Type: application/json; charset=utf-8');

// Load environment variables
if (file_exists(__DIR__.'/.env')) {
    foreach (file(__DIR__.'/.env', FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES) as $line) {
        if (strpos($line,'=')!==false) {
            list($k,$v) = explode('=',$line,2);
            putenv(trim($k).'='.trim($v));
        }
    }
}

// Database configuration
$DB_HOST = getenv('DB_HOST') ?: '172.104.206.182';
$DB_USER = getenv('DB_USER') ?: 'seattlelisted_usr';
$DB_PASS = getenv('DB_PASS') ?: 'T@5z6^pl}';
$DB_NAME = getenv('DB_NAME') ?: 'offta';
$DB_PORT = (int)(getenv('DB_PORT') ?: 3306);

// Websites folder path
$WEBSITES_PATH = 'C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Captures\\websites';

// Connect to database
$db = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, $DB_PORT);
if ($db->connect_errno) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Database connection failed: ' . $db->connect_error]);
    exit;
}
$db->set_charset('utf8mb4');

/**
 * Find the most recent openai_batch_*.json file
 */
function find_latest_openai_json(string $folder): ?string {
    $pattern = $folder . DIRECTORY_SEPARATOR . 'openai_batch_*.json';
    $files = glob($pattern);
    if (empty($files)) return null;
    
    // Sort by filename (timestamp is in filename) descending
    rsort($files);
    return $files[0];
}

/**
 * Get google_addresses.id from google_places.id
 */
function get_google_addresses_id(mysqli $db, ?string $google_places_id): ?int {
    if (empty($google_places_id)) return null;
    
    // First, get google_addresses_id from google_places table
    $stmt = $db->prepare("SELECT google_addresses_id FROM google_places WHERE id = ? LIMIT 1");
    if (!$stmt) return null;
    
    $gp_id = (int)$google_places_id;
    $stmt->bind_param('i', $gp_id);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result->fetch_assoc();
    $stmt->close();
    
    if ($row && !empty($row['google_addresses_id'])) {
        return (int)$row['google_addresses_id'];
    }
    
    return null;
}

/**
 * Clean string value - convert "null" strings to actual null
 */
function clean_val($val) {
    if ($val === null || $val === 'null' || $val === 'NULL' || $val === '') {
        return null;
    }
    return is_string($val) ? trim($val) : $val;
}

/**
 * Clean price - extract integer from price string
 */
function clean_price($val): ?int {
    if ($val === null || $val === 'null' || $val === '') return null;
    $cleaned = preg_replace('/[^0-9]/', '', (string)$val);
    return $cleaned !== '' ? (int)$cleaned : null;
}

/**
 * Insert a single apartment listing
 */
function insert_listing(mysqli $db, array $property, array $unit, ?int $google_addresses_id, ?int $google_places_id): array {
    $property_info = $property['property_info'] ?? [];
    $amenities = $property['amenities'] ?? [];
    $policies = $property['policies'] ?? [];
    
    // Prepare data
    $data = [
        'Building_Name' => clean_val($property_info['Building_Name'] ?? null),
        'full_address' => clean_val($property_info['full_address'] ?? null),
        'street' => clean_val($property_info['street'] ?? null),
        'city' => clean_val($property_info['city'] ?? null),
        'state' => clean_val($property_info['state'] ?? null),
        'suburb' => clean_val($property_info['suburb'] ?? null),
        'phone_contact' => clean_val($property_info['phone_contact'] ?? null),
        'email_contact' => clean_val($property_info['email_contact'] ?? null),
        'listing_website' => clean_val($property_info['listing_website'] ?? null),
        'apply_now_link' => clean_val($property_info['apply_now_link'] ?? null),
        
        'unit_number' => clean_val($unit['unit_number'] ?? null),
        'title' => clean_val($unit['title'] ?? null),
        'bedrooms' => clean_val($unit['bedrooms'] ?? null),
        'bathrooms' => clean_val($unit['bathrooms'] ?? null),
        'sqft' => clean_val($unit['sqft'] ?? null),
        'price' => clean_price($unit['price'] ?? null),
        'available_date' => clean_val($unit['available_date'] ?? null),
        'Lease_Length' => clean_val($unit['Lease_Length'] ?? null),
        'Deposit_Amount' => clean_val($unit['Deposit_Amount'] ?? null),
        'floorplan_url' => clean_val($unit['floorplan_url'] ?? null),
        'description' => clean_val($unit['description'] ?? null),
        
        'Pool' => clean_val($amenities['Pool'] ?? null),
        'Gym' => clean_val($amenities['Gym'] ?? null),
        'Balcony' => clean_val($amenities['Balcony'] ?? null),
        'Parking' => clean_val($amenities['Parking'] ?? null),
        'parking_fee' => clean_val($amenities['parking_fee'] ?? null),
        'Cats' => clean_val($amenities['Cats'] ?? null),
        'Dogs' => clean_val($amenities['Dogs'] ?? null),
        'MFTE' => clean_val($amenities['MFTE'] ?? null),
        'amenities' => !empty($amenities['amenities_list']) ? json_encode($amenities['amenities_list']) : null,
        
        'Application_Fee' => clean_val($policies['Application_Fee'] ?? null),
        'Credit_Score' => clean_val($policies['Credit_Score'] ?? null),
        'Managed' => clean_val($policies['Managed'] ?? null),
        
        'google_addresses_id' => $google_addresses_id,
        'google_places_id' => $google_places_id
    ];
    
    // Build title from unit info if not present
    if (empty($data['title']) && !empty($data['bedrooms'])) {
        $beds = $data['bedrooms'] == '0' ? 'Studio' : $data['bedrooms'] . ' Bed';
        $baths = !empty($data['bathrooms']) ? ' / ' . $data['bathrooms'] . ' Bath' : '';
        $data['title'] = $beds . $baths;
    }
    
    $sql = "INSERT INTO apartment_listings (
        user_id, active, type, network_id,
        Building_Name, full_address, street, city, state, suburb, country,
        phone_contact, email_contact, listing_website, apply_now_link,
        unit_number, title, bedrooms, bathrooms, sqft, price, available_date,
        Lease_Length, Pool, Gym, Balcony, Parking, parking_fee, Cats, Dogs, MFTE, amenities,
        description, floorplan_url, Managed,
        google_addresses_id, google_places_id,
        time_created, time_updated
    ) VALUES (
        0, 'yes', 'For-Rent', 1,
        ?, ?, ?, ?, ?, ?, 'USA',
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?,
        NOW(), NOW()
    )";
    
    $stmt = $db->prepare($sql);
    if (!$stmt) {
        return ['ok' => false, 'error' => 'Prepare failed: ' . $db->error];
    }
    
    $stmt->bind_param(
        'sssssssssssssssssisssssssssssssii',
        $data['Building_Name'], $data['full_address'], $data['street'], $data['city'], $data['state'], $data['suburb'],
        $data['phone_contact'], $data['email_contact'], $data['listing_website'], $data['apply_now_link'],
        $data['unit_number'], $data['title'], $data['bedrooms'], $data['bathrooms'], $data['sqft'], $data['price'], $data['available_date'],
        $data['Lease_Length'], $data['Pool'], $data['Gym'], $data['Balcony'], $data['Parking'], $data['parking_fee'], $data['Cats'], $data['Dogs'], $data['MFTE'], $data['amenities'],
        $data['description'], $data['floorplan_url'], $data['Managed'],
        $data['google_addresses_id'], $data['google_places_id']
    );
    
    $ok = $stmt->execute();
    if (!$ok) {
        $error = $stmt->error;
        $stmt->close();
        return ['ok' => false, 'error' => 'Execute failed: ' . $error];
    }
    
    $insert_id = $stmt->insert_id;
    $stmt->close();
    
    return ['ok' => true, 'id' => $insert_id];
}

// Main execution
try {
    // Determine which JSON file to process
    $json_file = null;
    if (!empty($_GET['file'])) {
        $json_file = $WEBSITES_PATH . DIRECTORY_SEPARATOR . basename($_GET['file']);
        if (!file_exists($json_file)) {
            throw new Exception("Specified file not found: " . $_GET['file']);
        }
    } else {
        $json_file = find_latest_openai_json($WEBSITES_PATH);
        if (!$json_file) {
            throw new Exception("No openai_batch_*.json files found in " . $WEBSITES_PATH);
        }
    }
    
    // Read and parse JSON
    $json_content = file_get_contents($json_file);
    if ($json_content === false) {
        throw new Exception("Could not read file: " . $json_file);
    }
    
    $data = json_decode($json_content, true);
    if ($data === null) {
        throw new Exception("Invalid JSON in file: " . json_last_error_msg());
    }
    
    $properties = $data['properties'] ?? [];
    if (empty($properties)) {
        throw new Exception("No properties found in JSON file");
    }
    
    $results = [
        'ok' => true,
        'file' => basename($json_file),
        'total_properties' => count($properties),
        'total_units' => 0,
        'inserted' => 0,
        'errors' => [],
        'skipped' => 0,
        'listings' => []
    ];
    
    // Process each property
    foreach ($properties as $idx => $property) {
        $google_places_id = !empty($property['_google_places_id']) ? (int)$property['_google_places_id'] : null;
        $google_addresses_id = get_google_addresses_id($db, $property['_google_places_id'] ?? null);
        $source_file = $property['_source_file'] ?? 'unknown';
        
        $units = $property['units'] ?? [];
        if (empty($units)) {
            // No units - create one listing for the property with minimal info
            $units = [['title' => 'Property Listing']];
        }
        
        foreach ($units as $unit_idx => $unit) {
            $results['total_units']++;
            
            // Skip units without price (usually unavailable)
            if (empty($unit['price']) && empty($unit['sqft']) && empty($unit['bedrooms'])) {
                $results['skipped']++;
                continue;
            }
            
            $insert_result = insert_listing($db, $property, $unit, $google_addresses_id, $google_places_id);
            
            if ($insert_result['ok']) {
                $results['inserted']++;
                $results['listings'][] = [
                    'id' => $insert_result['id'],
                    'source' => $source_file,
                    'gp_id' => $google_places_id,
                    'ga_id' => $google_addresses_id,
                    'title' => clean_val($unit['title'] ?? null),
                    'price' => clean_price($unit['price'] ?? null)
                ];
            } else {
                $results['errors'][] = [
                    'source' => $source_file,
                    'unit' => $unit_idx,
                    'error' => $insert_result['error']
                ];
            }
        }
    }
    
    echo json_encode($results, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => $e->getMessage()
    ], JSON_PRETTY_PRINT);
}

$db->close();
