import chardet
import logging

logger = logging.getLogger('converter')

def detect_encoding(file_path, num_bytes=10000):
    try:
        with open(file_path, 'rb') as f:
            rawdata = f.read(num_bytes)
        result = chardet.detect(rawdata)
        return result['encoding']
    except Exception as e:
        logger.error(f"Error detecting encoding for file {file_path}: {e}")
        return None

def contains_chinese(text):
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def file_contains_chinese(file_path, encoding):
    try:
        logger.debug(f"Checking if file {file_path} contains Chinese characters with encoding {encoding}...")
        # Use decode_mixed_encoding_file to read file robustly
        decoded_lines = decode_mixed_encoding_file(file_path)
        content = '\n'.join(decoded_lines)
        has_chinese = contains_chinese(content)
        logger.debug(f"file_contains_chinese for {file_path} with mixed decoding: {has_chinese}")
        return has_chinese
    except Exception as e:
        logger.error(f"Error reading file {file_path} for Chinese detection with mixed decoding: {e}")
        return False

def is_english(text):
    try:
        text.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

def decode_mixed_encoding_file(file_path):
    """
    Reads a file with mixed encodings by detecting encoding per line dynamically.
    Decodes each line using detected encoding with errors='replace' to avoid decode errors.

    Returns the decoded content as a list of strings (lines).
    """
    import logging
    import chardet
    logger = logging.getLogger('converter')
    decoded_lines = []
    try:
        with open(file_path, 'rb') as f:
            raw_lines = f.readlines()
        total_lines = len(raw_lines)
        logger.info(f"Total lines in file {file_path}: {total_lines}")

        for i, raw_line in enumerate(raw_lines, start=1):
            try:
                detection = chardet.detect(raw_line)
                encoding = detection.get('encoding')
                confidence = detection.get('confidence', 0)
                if encoding is None or confidence < 0.5:
                    encoding = 'utf-8'  # default fallback
                decoded_line = raw_line.decode(encoding, errors='replace').rstrip('\r\n')
                logger.debug(f"Line {i} decoded as {encoding} with confidence {confidence:.2f}")
                decoded_lines.append(decoded_line)
            except Exception as e:
                logger.error(f"Error decoding line {i} in file {file_path}: {e}")
                decoded_lines.append('')  # Append empty string on error to keep line count
        return decoded_lines
    except Exception as e:
        logger.error(f"Failed to read file {file_path} in binary mode: {e}")
        return []

def encode_utf8_to_gbk_safe(text):
    """
    Safely encodes a UTF-8 decoded string to GBK encoding.
    Uses errors='replace' to avoid encoding errors.
    Logs a warning if replacement occurs.

    Returns bytes encoded in GBK.
    """
    import logging
    logger = logging.getLogger('converter')
    try:
        encoded_bytes = text.encode('gbk', errors='strict')
        return encoded_bytes
    except UnicodeEncodeError:
        encoded_bytes = text.encode('gbk', errors='replace')
        logger.warning("Encoding to GBK replaced some characters due to encoding errors.")
        return encoded_bytes
