<?php
// Quick test to see cities table structure
$mysqli = new mysqli('172.104.206.182', 'seattlelisted_usr', 'T@5z6^pl}', 'offta', 3306);
if ($mysqli->connect_errno) die("Connect failed: " . $mysqli->connect_error);

$res = $mysqli->query("SHOW COLUMNS FROM cities");
echo "Cities table columns:\n";
while ($row = $res->fetch_assoc()) {
    echo "- " . $row['Field'] . " (" . $row['Type'] . ")\n";
}

echo "\n\nSample row:\n";
$res = $mysqli->query("SELECT * FROM cities LIMIT 1");
$row = $res->fetch_assoc();
if ($row) {
    foreach ($row as $k => $v) {
        echo "$k = $v\n";
    }
}
