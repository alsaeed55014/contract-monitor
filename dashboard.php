<?php
require_once 'config.php';
requireLogin();

$user = getCurrentUser();
$ipAddress = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
?>
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم - نظام الحضور والانصراف</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f172a; 
            margin: 0; 
            direction: rtl;
        }
        .sidebar {
            background: #1e293b;
            width: 260px;
            height: 100vh;
            position: fixed;
            top: 0;
            right: 0;
            padding: 20px;
            box-shadow: -2px 0 10px rgba(0,0,0,0.3);
        }
        .sidebar h3 { color: #f8fafc; margin-top: 0; }
        .sidebar a {
            display: block;
            color: #cbd5e1;
            text-decoration: none;
            padding: 12px;
            margin: 8px 0;
            border-radius: 6px;
            transition: 0.3s;
        }
        .sidebar a:hover, .sidebar a.active {
            background: #3b82f6;
            color: white;
        }
        .main-content {
            margin-right: 260px;
            padding: 30px;
        }
        header {
            background: #1e293b;
            padding: 20px 30px;
            color: #f8fafc;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .user-info { color: #94a3b8; font-size: 14px; }
        .btn-logout {
            background: #ef4444;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-logout:hover { background: #dc2626; }
        .card {
            background: #1e293b;
            border-radius: 10px;
            padding: 25px;
            margin-top: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }
        .badge-active { background: #22c55e; color: white; }
        .badge-inactive { background: #ef4444; color: white; }
        .alert {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .alert-info { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            padding: 12px 15px;
            text-align: right;
            border-bottom: 1px solid #334155;
            color: #cbd5e1;
        }
        th { background: #334155; color: #f8fafc; font-weight: 600; }
        tr:hover { background: #334155; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>القائمة الرئيسية</h3>
        <a href="dashboard.php" class="active">لوحة التحكم</a>
        <a href="attendance.php">سجل الحضور والانصراف</a>
        <a href="logout.php?logout">تسجيل الخروج</a>
    </div>

    <div class="main-content">
        <header>
            <div>
                <h1 style="margin:0; font-size: 20px;">مرحباً، <?php echo htmlspecialchars($user['employee_name']); ?></h1>
            </div>
            <div class="user-info">
                الدور: <?php echo htmlspecialchars($user['role']); ?>
            </div>
        </header>

        <div class="alert alert-info">
            <strong>تنبيه:</strong> نظام التسجيل التلقائي مفعل. عند إغلاق المتصفح أو إخفاء الصفحة، 
            سيتم تسجيل وقت الخروج تلقائياً في السجل.
        </div>

        <div class="card">
            <h3>حالة الجلسة الحالية</h3>
            <p>حالة تسجيل الدخول: <span class="badge badge-active">مفعل</span></p>
            <p>وقت الدخول: <?php echo date('Y-m-d H:i:s'); ?></p>
            <p>العنوان: <?php echo htmlspecialchars($ipAddress); ?></p>
            
            <button class="btn-logout" onclick="manualLogout()">تسجيل الخروج اليدوي</button>
        </div>
    </div>

    <!-- كود الإغلاق التلقائي عند إغلاق المتصفح -->
    <script>
    // دالة تسجيل الخروج اليدوي
    function manualLogout() {
        if (تأكيد('هل أنت متأكد أنك تريد تسجيل الخروج؟')) {
            window.location.href = 'logout.php?logout';
        }
    }

    // دالة تسجيل الخروج التلقائي عند إغلاق المتصفح
    function autoLogout() {
        // إرسال طلب للخادم باستخدام navigator.sendBeacon (يعمل حتى بعد إغلاق الصفحة)
        const formData = new FormData();
        formData.append('action', 'auto_logout');

        navigator.sendBeacon('logout.php', formData);

        // بديل باستخدام fetch مع keepalive (للمتصفحات التي لا تدعم sendBeacon مع FormData)
        /*
        fetch('logout.php', {
            method: 'POST',
            keepalive: true,
            body: 'action=auto_logout',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        */
    }

    // 1. عند إخفاء الصفحة أو تقليل النافذة أو transición لتبويب آخر
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            autoLogout();
        }
    });

    // 2. عند إغلاق الصفحة أو إعادة تحميلها (كطريقة احتياطية)
    window.addEventListener('beforeunload', function () {
        autoLogout();
    });

    // 3. عند مغادرة الصفحة (pagehide) للمتصفحات الحديثة (سفاري، كروم الجوال)
    window.addEventListener('pagehide', function () {
        autoLogout();
    });

    // تأكيد الخروج اليدوي
    function تأكيد(رسالة) {
        return confirm(رسالة);
    }
    </script>
</body>
</html>