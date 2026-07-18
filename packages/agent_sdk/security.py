import re
SECRET_KEYS={"password","passwd","pwd","secret","token","api_key","apikey","access_key","connection_string"}
def redact(value):
    if isinstance(value, dict): return {k:("***REDACTED***" if any(s in k.lower() for s in SECRET_KEYS) else redact(v)) for k,v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        value=re.sub(r'(?i)(password|pwd|token|api_key)=([^;\s]+)', r'\1=***REDACTED***', value)
        value=re.sub(r'(?i)(://[^:/\s]+:)([^@\s]+)(@)', r'\1***REDACTED***\3', value)
    return value
