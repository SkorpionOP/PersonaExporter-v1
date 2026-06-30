from parsers.whatsapp import WhatsAppParser
from parsers.telegram import TelegramParser

def get_parser_for_filename(filename: str):
    fn_lower = filename.lower()
    if fn_lower.endswith('.json'):
        return TelegramParser()
    elif fn_lower.endswith('.txt'):
        return WhatsAppParser()
    else:
        raise ValueError("Unsupported file format. Must be .txt (WhatsApp) or .json (Telegram).")
