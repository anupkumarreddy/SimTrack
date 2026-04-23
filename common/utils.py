
def calculate_pass_rate(pass_count, total_count):
    if total_count == 0:
        return 0.0
    return round((pass_count / total_count) * 100, 2)

def normalize_signature(text):
    if not text:
        return ''
    text = text.lower()
    text = ' '.join(text.split())
    return text

def format_percentage(value):
    if value is None:
        return '0.00%'
    return f"{value:.2f}%"
