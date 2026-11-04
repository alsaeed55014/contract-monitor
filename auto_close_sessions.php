<?php
/**
 * auto_close_sessions.php
 * 
 * هذا الملف يغلق تلقائياً جميع الجلسات التي لم يكن لها نشاط منذ مدة محددة (30 دقيقة افتراضياً).
 * قم بتشغيل هذا الملف عبر Cron Job كل 5-10 دقائق للتأكد من تسجيل خروج المستخدمين 
 * حتى إذا أغلقوا المتصفح بدون إرسال طلب خروج.
 * 
 * مثال إعداد Cron (كل 5 دقائق):
 * */5 * * * * /usr/bin/php /مسار/المشروع/auto_close_sessions.php
 */

require_once 'config.php';

try {
    // مدة عدم النشاط بالدقائق قبل اعتبار الجلسة منتهية (30 دقيقة)
    $inactiveMinutes = 30;

    $stmt = $pdo->prepare("
        UPDATE attendance_logs 
        SET logout_time = NOW(), 
            logout_status = 'تم تسجيل الخروج تلقائياً' 
        WHERE logout_status = 'لم يسجل خروج' 
          AND logout_time IS NULL
          AND last_activity < DATE_SUB(NOW(), INTERVAL :minutes MINUTE)
    ");
    $stmt->bindValue(':minutes', $inactiveMinutes, PDO::PARAM_INT);
    $stmt->execute();

    $closedCount = $stmt->rowCount();

    // вывод结果 (يمكن استخدامه لسجلات cron)
    echo date('Y-m-d H:i:s') . " - تم إغلاق {$closedCount} جلسة تلقائياً بسبب عدم النشاط.\n";

} catch (PDOException $e) {
    echo date('Y-m-d H:i:s') . " - خطأ: " . $e->getMessage() . "\n";
    http_response_code(500);
}
?>