from deep_translator import GoogleTranslator
words = ["مصفف", "شعر", "مصفف شعر", "مصففة شعر", "مصففة"]
for w in words:
    print(w, "->", GoogleTranslator(source='ar', target='en').translate(w))
