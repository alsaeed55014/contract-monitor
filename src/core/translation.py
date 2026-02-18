# src/core/translation.py

AR_TO_EN = {
    "بدكير": ["Manicure", "Nail Technician"],
    "منكير": ["Pedicure", "Nail Technician"],
    "بدكير منكير": ["Manicure", "Pedicure", "Nail Technician"],
    "مصففة شعر": ["Hair Stylist", "Hairdresser"],
    "تنظيف بشرة": ["Skin Care", "Facial Specialist"],
    "خادمة منزلية": ["Housemaid", "Domestic Worker"],
    "عاملة منزلية": ["Domestic Worker"],
    "شيف حلويات": ["Pastry Chef", "Dessert Chef"],
    "نادلة": ["Waitress"],
    "نادل": ["Waiter"],
    "باريستا": ["Barista"],
    "افريقي": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Sudan", "Morocco", "Tunisia", "Senegal"],
    "افريقية": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Sudan", "Morocco", "Tunisia", "Senegal"],
}


def translate_to_english(keyword: str):
    keyword = keyword.strip().lower()
    return AR_TO_EN.get(keyword, [])
