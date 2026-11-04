<?php
require_once 'config.php';

// إذا كان المستخدم مسجل دخوله بالفعل، اذهب للوحة التحكم
if (isset($_SESSION['user_id'])) {
    header('Location: dashboard.php');
    exit;
}

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if (empty($username) || empty($password)) {
        $error = 'الرجاء إدخال اسم المستخدم وكلمة المرور';
    } else {
        $stmt = $pdo->prepare("SELECT * FROM users WHERE username = ? LIMIT 1");
        $stmt->execute([$username]);
        $user = $stmt->fetch();

        if ($user && password_verify($password, $user['password'])) {
            // تسجيل الدخول 성공
            $_SESSION['user_id'] = $user['id'];
            $_SESSION['username'] = $user['username'];
            $_SESSION['employee_name'] = $user['employee_name'];
            $_SESSION['role'] = $user['role'];
            $_SESSION['login_time'] = time();

            // الحصول على عنوان IP
            $ipAddress = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';

            // تسجيل دخول في سجل الحضور
            recordLogin($pdo, $user['id'], $user['employee_name'], $ipAddress);

            header('Location: dashboard.php');
            exit;
        } else {
            $error = 'اسم المستخدم أو كلمة المرور غير صحيحة';
        }
    }
}
?>
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - نظام الحضور والانصراف</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f172a; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
            direction: rtl;
        }
        .login-card {
            background: #1e293b;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        h2 { color: #f8fafc; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #cbd5e1; margin-bottom: 8px; font-size: 14px; }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            color: #f8fafc;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        button {
            width: 100%;
            padding: 12px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover { background: #2563eb; }
        .error { color: #f87171; text-align: center; margin-bottom: 20px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>تسجيل الدخول</h2>
        
        <?php if ($error): ?>
            <div class="error"><?php echo htmlspecialchars($error); ?></div>
        <?php endif; ?>

        <form method="POST" action="">
            <div class="form-group">
                <label>اسم المستخدم</label>
                <input type="text" name="username" required placeholder="أدخل اسم المستخدم">
            </div>
            <div class="form-group">
                <label>كلمة المرور</label>
                <input type="password" name="password" required placeholder="أدخل كلمة المرور">
            </div>
            <button type="submit">تسجيل الدخول</button>
        </form>

        <div class="footer">
            <p>نظام الحضور والانصراف - تسجيل خروج تلقائي عند إغلاق المتصفح</p>
            <p>مستخدم تجريبي: admin / admin123</p>
        </div>
    </div>
</body>
</html>