<?php
require_once 'config.php';

$userId = $_SESSION['user_id'] ?? null;

// إذا جاء الطلب عبر AJAX / sendBeacon (إغلاق تلقائي للمتصفح)
if (isset($_POST['action']) && $_POST['action'] === 'auto_logout') {
    if ($userId) {
        recordLogout($pdo, $userId);
    }
    // إنهاء الجلسة على الخادم
    session_destroy();
    http_response_code(200);
    echo json_encode(['status' => 'success', 'message' => 'تم تسجيل الخروج تلقائياً']);
    exit;
}

// إذا جاء الطلب عبر زر تسجيل الخروج العادي
if (isset($_GET['logout'])) {
    if ($userId) {
        recordLogout($pdo, $userId);
    }
    session_destroy();
    header('Location: login.php?logged_out=1');
    exit;
}

// طلب غير معروف
http_response_code(400);
echo json_encode(['status' => 'error', 'message' => 'طلب غير صالح']);
?>