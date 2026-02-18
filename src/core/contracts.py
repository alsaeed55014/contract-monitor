from datetime import datetime, date
from dateutil import parser

class ContractManager:
    @staticmethod
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            # Clean text
            d_clean = str(date_str).strip().replace('ص', 'AM').replace('م', 'PM')
            # Use fuzzy parsing
            return parser.parse(d_clean, fuzzy=True).date()
        except:
            return None

    @staticmethod
    def calculate_status(expiry_date_str):
        today = date.today()
        expiry = ContractManager.parse_date(expiry_date_str)
        
        if not expiry:
            return {
                'status': 'unknown',
                'days': None,
                'label_ar': 'غير معروف',
                'label_en': 'Unknown',
                'color': 'grey'
            }

        diff = (expiry - today).days

        if diff < 0:
            return {
                'status': 'expired',
                'days': diff,
                'label_ar': f'منتهي منذ {abs(diff)} يوم',
                'label_en': f'Expired {abs(diff)} days ago',
                'color': 'red'
            }
        elif diff == 0:
            return {
                'status': 'urgent',
                'days': 0,
                'label_ar': 'ينتهي اليوم',
                'label_en': 'Expires Today',
                'color': 'red'
            }
        elif diff <= 7:
            return {
                'status': 'urgent',
                'days': diff,
                'label_ar': f'متبقي {diff} يوم',
                'label_en': f'{diff} Days Left',
                'color': 'orange'
            }
        elif diff <= 30:
            return {
                'status': 'warning',
                'days': diff,
                'label_ar': f'متبقي {diff} يوم',
                'label_en': f'{diff} Days Left',
                'color': 'yellow'
            }
        else:
            return {
                'status': 'active',
                'days': diff,
                'label_ar': 'ساري',
                'label_en': 'Active',
                'color': 'green'
            }
