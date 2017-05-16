<?php
if ($_GET['filter']) {
	if (is_array($_GET['filter']))
		$params = $_GET['filter'];
	else
		$params = array($_GET['filter']);
	$extensions = array_map(function($elem) { return preg_quote($elem); }, $params);
}
else {
	$extensions = array('\.fhx', '\.spf', '\.7z', '\.cpio\.gz', 'zImage', '\.yaml', '\.json', '\.all', '\.dtb', 'sims');
}
if (sizeof($extensions) > 1)
	$regex_filter = '/(?:' . implode('|', $extensions) . ')$/';
else
	$regex_filter = '/' . $extensions[0] . '$/';

$files = array();
$directory = new RecursiveDirectoryIterator('.', FilesystemIterator::SKIP_DOTS);
$iterator = new RecursiveIteratorIterator($directory);
foreach (new RegexIterator($iterator, $regex_filter) as $file_path) {
	$clean_path = substr($file_path, 2); /* use substr to skip './' */
	$basename = basename($clean_path);
	/* Search for already existing file (unique by basename)
	 * Overwrite if the new path is shorter than the existing */
	$existing = $files[$basename];
	if (!$existing || (strlen($clean_path) < strlen($existing)))
		$files[$basename] = $clean_path;
}
$file_paths = array_values($files);
sort($file_paths);
header('Content-Type: application/json');
echo json_encode($file_paths);
?>
