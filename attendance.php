<?php
require_once 'config.php';
requireLogin();

// جلب سجلات الحضور والانصراف
$stmt = $pdo->query("
    SELECT al.id, al.employee_name, al.login_time, al.logout_time, al.logout_status, al.ip_address
    FROM attendance_logs al
    ORDER BY al.login_time DESC
    LIMIT 100
");
$logs = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سجل الحضور والانصراف - نظام المتابعة</title>
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
        header h1 { margin: 0; font-size: 20px; }
        .btn-back {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
        }
        .btn-back:hover { background: #2563eb; }
        .card {
            background: #1e293b;
            border-radius: 10px;
            padding: 25px;
            margin-top: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }
        .badge-logged-out { background: #22c55e; color: white; }
        .badge-not-logged { background: #ef4444; color: white; }
        .badge-auto { background: #f59e0b; color: white; }
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
        .text-center { text-align: center; }
        .text-muted { color: #94a3b8; font-size: 13px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>القائمة الرئيسية</h3>
        <a href="dashboard.php">لوحة التحكم</a>
        <a href="attendance.php" class="active">سجل الحضور والانصراف</a>
        <a href="logout.php?logout">تسجيل الخروج</a>
    </div>

    <div class="main-content">
        <header>
            <h1>سجل الحضور والانصراف</h1>
            <a href="dashboard.php" class="btn-back">العودة للوحة التحكم</a>
        </header>

        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>اسم الموظف</th>
                        <th>وقت الدخول</th>
                        <th>وقت الخروج</th>
                        <th>حالة الخروج</th>
                        <th>عنوان IP</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (empty($logs)): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted">لا توجد سجلات حالياً</td>
                        </tr>
                    <?php else: ?>
                        <?php $counter = 1; foreach ($logs as $log): ?>
                            <tr>
                                <td class="text-center"><?php echo $counter++; ?></td>
                                <td><?php echo htmlspecialchars($log['employee_name']); ?></td>
                                <td><?php echo date('Y-m-d H:i:s', strtotime($log['login_time'])); ?></td>
                                <td>
                                    <?php if ($log['logout_time']): ?>
                                        <?php echo date('Y-m-d H:i:s', strtotime($log['logout_time'])); ?>
                                    <?php else: ?>
                                        <span class="text-muted">—</span>
                                    <?php endif; ?>
                                </td>
                                <td class="text-center">
                                    <?php
                                    $status = $log['logout_status'];
                                    if ($status === 'تم تسجيل الخروج تلقائياً') {
                                        echo '<span class="badge badge-auto">تم تسجيل الخروج تلقائياً</span>';
                                    } elseif ($status === 'تم تسجيل الخروج') {
                                        echo '<span class="badge badge-logged-out">تم تسجيل الخروج</span>';
                                    } else {
                                        echo '<span class="badge badge-not-logged">لم يسجل خروج</span>';
                                    }
                                    ?>
                                </td>
                                <td><?php echo htmlspecialchars($log['ip_address']); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>