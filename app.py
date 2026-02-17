from flask import Flask, render_template, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# بيانات جوجل شيت بتاعك
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw'
GID = '2008131'

def get_google_sheets_data():
    """جلب البيانات من جوجل شيت"""
    try:
        # التحقق من وجود ملف المفتاح
        if not os.path.exists('credentials.json'):
            print("⚠️ ملف credentials.json مش موجود!")
            print("📌 روح على ملف SETUP_INSTRUCTIONS.md واتبع الخطوات")
            return None
        
        # الاتصال بجوجل شيت
        creds = Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        
        # فتح الشيت
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet_by_id(int(GID))
        
        # قراءة البيانات
        data = sheet.get_all_records()
        
        print(f"✅ تم قراءة {len(data)} سجل من جوجل شيت بنجاح!")
        return data
        
    except FileNotFoundError:
        print("❌ ملف credentials.json مش موجود!")
        return None
    except Exception as e:
        print(f"❌ خطأ في الاتصال بجوجل شيت: {e}")
        print("📌 تأكد من:")
        print("   1. ملف credentials.json موجود في نفس المجلد")
        print("   2. شاركت الشيت مع Service Account Email")
        print("   3. Google Sheets API مفعّل")
        return None

def check_contract_expiry(data):
    """فحص العقود اللي هتخلص خلال يومين"""
    expiring_soon = []
    today = datetime.now()
    two_days_later = today + timedelta(days=2)
    
    for row in data:
        contract_end_date = row.get('When is your contract end date?', '')
        
        if contract_end_date and contract_end_date != '':
            try:
                # تحويل التاريخ لصيغة قابلة للمقارنة
                if isinstance(contract_end_date, str):
                    # محاولة تنسيقات مختلفة
                    for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            end_date = datetime.strptime(contract_end_date, date_format)
                            break
                        except:
                            continue
                    else:
                        continue
                else:
                    end_date = contract_end_date
                
                # فحص لو التاريخ خلال يومين
                if today <= end_date <= two_days_later:
                    days_left = (end_date - today).days
                    expiring_soon.append({
                        'name': row.get('Full Name:', 'غير محدد'),
                        'phone': str(row.get('Phone Number', 'غير محدد')),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'days_left': days_left,
                        'nationality': row.get('Nationality', 'غير محدد'),
                        'city': row.get('Which city in Saudi Arabia are you in', 'غير محدد')
                    })
                    print(f"⚠️ تنبيه: عقد {row.get('Full Name:', 'Unknown')} هينتهي خلال {days_left} يوم!")
                    
            except Exception as e:
                print(f"⚠️ مشكلة في قراءة تاريخ: {contract_end_date} - {e}")
                continue
    
    return expiring_soon

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """جلب كل البيانات والتنبيهات"""
    data = get_google_sheets_data()
    
    if data is None:
        return jsonify({
            'error': 'فشل الاتصال بجوجل شيت',
            'message': 'تأكد من وجود ملف credentials.json ومشاركة الشيت'
        }), 500
    
    expiring_contracts = check_contract_expiry(data)
    
    return jsonify({
        'total_records': len(data),
        'expiring_soon': expiring_contracts,
        'data': data[:50]  # أول 50 سجل بس
    })

@app.route('/api/expiring')
def get_expiring():
    """جلب التنبيهات بس"""
    data = get_google_sheets_data()
    
    if data is None:
        return jsonify({'error': 'فشل الاتصال'}), 500
    
    expiring_contracts = check_contract_expiry(data)
    
    return jsonify({
        'count': len(expiring_contracts),
        'contracts': expiring_contracts
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎯 نظام تتبع العقود - We're Hiring!")
    print("="*70)
    print(f"📊 Google Sheet ID: {SPREADSHEET_ID}")
    print(f"🌐 السيرفر شغال على: http://localhost:5000")
    print(f"🔄 التحديث التلقائي: كل دقيقة")
    print("="*70)
    print("\n⏳ جاري الاتصال بجوجل شيت...\n")
    
    # تجربة الاتصال قبل تشغيل السيرفر
    test_data = get_google_sheets_data()
    if test_data:
        print(f"\n✅ تمام! البرنامج متصل بجوجل شيت ({len(test_data)} سجل)")
        print(f"✅ افتح المتصفح على: http://localhost:5000")
    else:
        print("\n⚠️ في مشكلة في الاتصال!")
        print("📌 شوف ملف SETUP_INSTRUCTIONS.md للحل")
    
    print("\n" + "="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
