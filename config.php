<?php
// إعدادات الاتصال بقاعدة البيانات
// عدل هذه البيانات وفقاً لإعدادات الخادم الخاص بك

define('DB_HOST', 'localhost');
define('DB_NAME', 'attendance_system');
define('DB_USER', 'root');
define('DB_PASS', '');
define('DB_CHARSET', 'utf8mb4');

// جلسة النظام
define('SESSION_TIMEOUT', 1800); // 30 دقيقة بالثواني (للإغلاق التلقائي)

// الاتصال بقاعدة البيانات باستخدام PDO
try {
    $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
} catch (PDOException $e) {
    die("فشل الاتصال بقاعدة البيانات: " . $e->getMessage());
}

// بدء الجلسة إذا لم تبدأ
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    ini_set('session.use_only_cookies', 1);
    session_start();
}

// دالة للتحقق من تسجيل الدخول
function requireLogin() {
    global $pdo;
    if (!isset($_SESSION['user_id'])) {
        header('Location: login.php');
        exit;
    }

    // تحديث وقت آخر نشاط للمستخدم الحالي
    $userId = $_SESSION['user_id'];
    $stmt = $pdo->prepare("
        UPDATE attendance_logs 
        SET last_activity = NOW() 
        WHERE user_id = ? 
          AND logout_time IS NULL
        ORDER BY login_time DESC 
        LIMIT 1
    ");
    $stmt->execute([$userId]);
}

// دالة لجلب معلومات المستخدم الحالي
function getCurrentUser() {
    if (!isset($_SESSION['user_id'])) return null;
    return [
        'id' => $_SESSION['user_id'],
        'username' => $_SESSION['username'] ?? '',
        'employee_name' => $_SESSION['employee_name'] ?? '',
        'role' => $_SESSION['role'] ?? 'user',
    ];
}

// دالة لتسجيل الخروج في قاعدة البيانات
function recordLogout($pdo, $userId) {
    $stmt = $pdo->prepare("
        UPDATE attendance_logs 
        SET logout_time = NOW(), 
            logout_status = 'تم تسجيل الخروج' 
        WHERE user_id = ? 
          AND logout_status = 'لم يسجل خروج' 
          AND logout_time IS NULL
        ORDER BY login_time DESC 
        LIMIT 1
    ");
    $stmt->execute([$userId]);
}

// دالة لتسجيل الدخول في قاعدة البيانات
function recordLogin($pdo, $userId, $employeeName, $ipAddress) {
    $stmt = $pdo->prepare("
        INSERT INTO attendance_logs (user_id, employee_name, login_time, logout_status, last_activity, ip_address)
        VALUES (?, ?, NOW(), 'لم يسجل خروج', NOW(), ?)
    ");
    $stmt->execute([$userId, $employeeName, $ipAddress]);
}
?>