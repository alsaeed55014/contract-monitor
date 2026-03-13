# --------- send_notification.ps1 --------- 
 # هذا سكربت يقوم بإرسال إشعار عند بدء تشغيل الكمبيوتر أو تشغيل البرنامج 
 
 # نص الإشعار 
 $Title = "تنبيه" 
 $Message = "تم تشغيل البرنامج. إشعارات Google Sheets جاهزة للاستقبال." 
 
 # إرسال الإشعار 
 try {
     [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null 
     
     $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02) 
     $textNodes = $Template.GetElementsByTagName("text")
     $textNodes.Item(0).InnerText = $Title
     $textNodes.Item(1).InnerText = $Message
     
     $Notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("برنامجك") 
     $Notification = [Windows.UI.Notifications.ToastNotification]::new($Template) 
     $Notifier.Show($Notification)
 } catch {
     Write-Error "فشل إرسال الإشعار: $_"
 }
