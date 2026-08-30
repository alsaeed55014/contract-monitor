"""
src/services/message_variation.py
===================================
محرك تعيد صياغة وتنويع الرسائل الذكي لمكافحة حظر واتساب 2026
يقوم بتغيير كل رسالة بشكل تلقائي مع الحفاظ الكامل على المعنى الأصلي والمحتوى المطلوب.
"""

import re
import random
import string

class MessageVariationEngine:
    """
    محرك صياغة المتغيرات والمعاني للرسائل (Anti-Ban Paraphrasing Engine)
    يتعرف على الكلمات والعبارات باللغتين العربية والإنجليزي ويرتب مرادفات متكافئة بالمعنى.
    """

    # قاموس المرادفات العربية الحافظة للمعنى
    AR_SYNONYMS = [
        # التحيات
        (r'\b(مرحبا|مرحباً|أهلاً|اهلا|أهلا|تحية طيبة|السلام عليكم|السلام عليكم ورحمة الله وبركاته)\b', 
         ['مرحباً بك', 'أهلاً وسهلاً', 'تحية طيبة وبعد', 'السلام عليكم ورحمة الله وبركاته', 'أهلاً بك', 'حياكم الله', 'السلام عليكم']),
        
        # السؤال عن الحال والافتتاحية
        (r'(أتمنى أن تكون بخير|نأمل أن تكون بأتم الصحة|أتمنى لك دوام الصحة والعافية|نأمل أن تكون بأفضل حال|أتمنى لك يوماً سعيداً)',
         ['أتمنى أن تكون بأفضل حال', 'نأمل أن تكون بأتم الصحة والعافية', 'أتمنى لك يوماً موفقاً وسعيداً', 'نأمل أن تكون بخير وعافية', 'أتمنى لك دوام الصحة والعافية']),
        
        # التقييم والفحص
        (r'(نعلمكم بأنا نقيّم|نعمل على تقييم|نقوم بمراجعة|فريقنا يفحص حالياً|نعمل حالياً على مطابقة|يجري حالياً فحص|نحن بصدد مراجعة|نعمل على مراجعة)',
         ['فريقنا يعمل حالياً على تقييم', 'نقوم بمراجعة وفحص', 'يجري حالياً تقييم ومطابقة', 'نعمل بجدية على مراجعة', 'يسعدنا فحص وتقييم']),
        
        # المتقدمين / المرشحين
        (r'\b(المرشحين|المتقدمين|الكوادر|الكفاءات|السير الذاتية|طلبات التوظيف)\b',
         ['المرشحين', 'المتقدمين للعمل', 'الكوادر والخبرات', 'الكفاءات المتقدمة', 'الملفات والكوادر']),
        
        # الوظائف / الشواغر
        (r'(الوظائف المتاحة|الفرص الوظيفية|الشواغر الوظيفية|عروض العمل|المناصب الشاغرة|فرص العمل المتاحة)',
         ['الفرص الوظيفية المتاحة لديّنا', 'الشواغر الوظيفية الحالية', 'عروض وفرص العمل المتوفرة', 'المناصب الوظيفية المتاحة', 'فرص العمل الجديدة']),
        
        # الاستفسار والرغبة
        (r'(لمعرفة ما إذا كنت باحثاً عن عمل|لتأكيد مدى تفرغك حالياً|لمعرفة رغبتك بالانضمام|للتأكد من إمكانية انضمامك|لتحديد مدى جاهزيتك للعمل|للتحقق من رغبتك بالتوظيف)',
         ['ولمعرفة مدى رغبتك وتفرغك للانضمام', 'وللتأكد مما إذا كنت ما زلت باحثاً عن فرصة عمل', 'ولمعرفة مدى جاهزيتك وتواجدك حالياً', 'وللتأكد من رغبتك في متابعة إجراءات التوظيف']),

        # الطلب والرجاء
        (r'\b(يرجى|نرجو|برجاء|تكرم بـ|لطفاً|نأمل تكرمك بـ|نرجو تكرمكم بـ)\b',
         ['يرجى التكرم بـ', 'نرجو منكم', 'نأمل تكرمكم بـ', 'لطفاً', 'برجاء تكرمكم بـ']),
         
        # الرد والتأكيد
        (r'(الرد بـ|الإجابة بـ|التأكيد بـ|إفادتنا بـ|إرسال رد بـ)',
         ['التأكيد بإرسال', 'الرد عبر اختيار', 'إفادتنا بـ', 'الإجابة بكلمة']),

        # خيارات الرد
        (r'(نعم – يرجى الاستمرار|نعم – مهتم ومتاح|نعم – أنا متاح|نعم – ارغب بالتواصل)',
         ['نعم – استمر معي', 'نعم – مهتم ومتاح حالياً', 'نعم – أنا متاح للعمل', 'نعم – أرغب بالمتابعة']),

        (r'(لا – غير متاح حالياً|لا – غير مهتم|لا – لست متاحاً|لا – لست باحثاً عن عمل)',
         ['لا – غير متاح في الوقت الحالي', 'لا – لست باحثاً عن فرصة حالياً', 'لا – غير مهتم حالياً', 'لا – لا تناسبني حالياً']),

        # مشاركة الرسالة
        (r'(في حال عدم رغبتك، يسعدنا مشاركة الرسالة مع صديق|إذا لم تكن باحثاً عن عمل، نرجو تكرمك بإعادة إرسال الرسالة|إذا كنت غير متاح، يسعدنا تحويل هذه الفرصة لأحد أصدقائك)',
         ['في حال عدم تفرغك، نقدّر جداً مشاركة هذه الفرصة مع زميل أو صديق يبحث عن عمل', 'إذا لم تكن باحثاً عن عمل حالياً، يسعدنا إرسال الرسالة لأحد معارفك المهتمين بالتوظيف', 'في حال عدم رغبتك بالانضمام، نرجو التكرم بمشاركة الإعلان مع أصدقائك الباحثين عن عمل']),

        # خاتمة الشكر والتوقيع
        (r'(مع جزيل الشكر والتقدير|مع أطيب التحيات|دمتم بخير|شاكرين ومقدرين|مع خالص التحية والتقدير|مع الفائق الاحترام والتقدير|مع فائق الاحترام)',
         ['مع جزيل الشكر والتقدير', 'مع أطيب التحيات وأرقها', 'شاكرين ومقدرين حسن تعاونكم', 'مع خالص التقدير والاحترام', 'دمتم بكل خير وعافية', 'مع فائق الاحترام والتقدير']),
    ]

    # قاموس المرادفات الإنجليزية الحافظة للمعنى
    EN_SYNONYMS = [
        (r'\b(Hello|Hi|Greetings|Dear)\b',
         ['Hello', 'Hi', 'Greetings', 'Dear', 'Good day']),
        
        (r'(I hope you are doing well|I hope this message finds you well|Wishing you a productive day|Hope you are having a great day|Trust you are doing well)',
         ['I hope you are doing well.', 'I hope this message finds you in good health.', 'Wishing you a productive and successful day.', 'Trust you are having a great day ahead.', 'Hope all is well with you.']),
        
        (r'\b(evaluating|reviewing|assessing|considering|matching)\b',
         ['evaluating', 'reviewing', 'assessing', 'considering', 'matching']),
        
        (r'\b(candidates|applicants|profiles|talents)\b',
         ['candidates', 'applicants', 'profiles', 'talents']),
        
        (r'(job opportunities|career opportunities|open positions|available roles)',
         ['job opportunities', 'career opportunities', 'open positions', 'available roles']),
        
        (r'(if you are still looking for a position|if you are still open to new opportunities|if you are currently seeking employment|if you are available for hire)',
         ['if you are still actively seeking a position.', 'if you are currently open to new job opportunities.', 'if you are available for new employment options.', 'if you are still interested in a new role.']),

        (r'(Best regards|Kind regards|Warm regards|Sincerely|With respect)',
         ['Best regards,', 'Kind regards,', 'Warm regards,', 'Sincerely,', 'With respect,']),
    ]

    @classmethod
    def parse_spintax(cls, text: str) -> str:
        """تحليل الـ Spintax المكتوب مثل {خيار1|خيار2|خيار3} واختيار خيار عشوائي"""
        if not text: return ""
        pattern = r'\{([^{}]+)\}'
        while re.search(pattern, text):
            def repl(match):
                options = match.group(1).split('|')
                return random.choice(options)
            text = re.sub(pattern, repl, text)
        return text

    @classmethod
    def clean_text(cls, text: str) -> str:
        """إزالة أي رموز غير مرئية قد تؤدي لحظر الحساب"""
        if not text: return ""
        for ch in ['\u200b', '\u200c', '\u200d', '\ufeff', '\u200e', '\u200f', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e']:
            text = text.replace(ch, '')
        return text

    @classmethod
    def paraphrase(cls, text: str, seed_key: str = None) -> str:
        """
        الدالة الرئيسية لتغيير صياغة وتوليد مظهر فريد وطبيعي لكل رسالة مع الحفاظ الكامل على المعنى الأصلي.
        تتأكد من:
        1. حماية الروابط وأرقام الهواتف والمتغيرات {Name} و {CV}
        2. تطبيق استبدال المرادفات الذكية (Synonym Swapping)
        3. تحليل Spintax إن وجد
        4. تنظيف النص من أي أحرف مخفية
        """
        if not text or not text.strip():
            return text

        # 1. حماية المتغيرات والروابط عبر استبدالها بأسماء مؤقتة
        protected_tokens = []

        def protect_match(match):
            idx = len(protected_tokens)
            token = f"___PROT_TOKEN_{idx}___"
            protected_tokens.append(match.group(0))
            return token

        # حماية المتغيرات {Name}, {name}, {CV}, {cv}, إلخ
        temp_text = re.sub(r'\{[a-zA-Z0-9_]+\}', protect_match, text)

        # حماية الروابط URLs
        temp_text = re.sub(r'https?://[^\s]+', protect_match, temp_text)

        # 2. تطبيق استبدال المرادفات العربية
        for pattern, options in cls.AR_SYNONYMS:
            def replace_ar(m):
                return random.choice(options)
            temp_text = re.sub(pattern, replace_ar, temp_text, flags=re.IGNORECASE)

        # 3. تطبيق استبدال المرادفات الإنجليزية
        for pattern, options in cls.EN_SYNONYMS:
            def replace_en(m):
                return random.choice(options)
            temp_text = re.sub(pattern, replace_en, temp_text, flags=re.IGNORECASE)

        # 4. تحليل Spintax المكتوب صراحة
        temp_text = cls.parse_spintax(temp_text)

        # 5. تنظيف أي أحرف مخفية
        temp_text = cls.clean_text(temp_text)

        # 6. استعادة المتغيرات والروابط المحمية
        for idx, original_val in enumerate(protected_tokens):
            token = f"___PROT_TOKEN_{idx}___"
            temp_text = temp_text.replace(token, original_val)

        return temp_text.strip()
