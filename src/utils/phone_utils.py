import re

def format_phone_number(phone, country_code="966"):
    """
    Cleans and formats phone numbers for Saudi Arabia (966) and Philippines (63).
    """
    if not phone:
        return None
    
    # Remove all non-numeric characters except +
    clean = re.sub(r'[^\d+]', '', str(phone))
    
    # Saudi Arabia logic
    if country_code == "966":
        # Remove leading + if present for processing
        s = clean.lstrip('+')
        if s.startswith('05') and len(s) == 10:
            return f"+966{s[1:]}"
        elif s.startswith('5') and len(s) == 9:
            return f"+966{s}"
        elif s.startswith('966') and len(s) == 12:
            return f"+{s}"
        elif len(s) == 9:
            return f"+966{s}"
            
    # Philippines logic
    elif country_code == "63":
        s = clean.lstrip('+')
        if s.startswith('09') and len(s) == 11:
            return f"+63{s[1:]}"
        elif s.startswith('9') and len(s) == 10:
            return f"+63{s}"
        elif s.startswith('63') and len(s) == 12:
            return f"+{s}"
            
    # Generic fallback: if it starts with +, return it, else add +
    if clean.startswith('+'):
        return clean
    return f"+{clean}"

def validate_numbers(raw_text):
    """
    Extracts and validates numbers from a raw string/text.
    """
    # Split by comma, newline, or space
    parts = re.split(r'[,\n\s]+', raw_text)
    valid_sa = []
    valid_ph = []
    invalid = []
    seen = set()
    
    for p in parts:
        p = p.strip()
        if not p: continue
        
        # Try SA first
        formatted_sa = format_phone_number(p, "966")
        formatted_ph = format_phone_number(p, "63")
        
        # Heuristic to decide if it's likely SA or PH
        # SA numbers usually have 9 digits after 966
        # PH numbers usually have 10 digits after 63
        
        if formatted_sa and len(formatted_sa) == 13: # +966 + 9 digits
            if formatted_sa not in seen:
                valid_sa.append(formatted_sa)
                seen.add(formatted_sa)
        elif formatted_ph and len(formatted_ph) == 13: # +63 + 10 digits
            if formatted_ph not in seen:
                valid_ph.append(formatted_ph)
                seen.add(formatted_ph)
        else:
            invalid.append(p)
            
    return valid_sa, valid_ph, invalid
