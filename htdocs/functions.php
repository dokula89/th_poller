<?php
// functions.php: shared DB connection and lookup for address matching

function get_db_connection() {
    $db_host = '172.104.206.182';
    $db_user = 'seattlelisted_usr';
    $db_pass = 'T@5z6^pl}';
    $db_name = 'offta';
    $mysqli = new mysqli($db_host, $db_user, $db_pass, $db_name);
    if ($mysqli->connect_errno) {
        error_log('DB connect error: ' . $mysqli->connect_error);
        return null;
    }
    return $mysqli;
}

function match_google_address($mysqli, $address) {
    if (!$mysqli || !$address) return null;
    $addr = $mysqli->real_escape_string($address);
    $sql = "SELECT id, google_places_id, Fulladdress, Street FROM google_places WHERE Fulladdress = '$addr' OR Street = '$addr' LIMIT 1";
    $res = $mysqli->query($sql);
    if ($res && $row = $res->fetch_assoc()) {
        return [
            'google_addresses_id' => $row['id'],
            'google_places_id' => $row['google_places_id'],
            'matched_fulladdress' => $row['Fulladdress'],
            'matched_street' => $row['Street']
        ];
    }
    return null;
}
