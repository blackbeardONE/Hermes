import time
import requests
import logging

try:
    from googletrans import Translator
except ImportError:
    print("googletrans package not found. Please install it using: pip install googletrans==4.0.0-rc1")
    exit(1)

translator = Translator()

# Backup translator using translate package (if available)
try:
    from translate import Translator as BackupTranslator
    backup_translator = BackupTranslator(to_lang="en", from_lang="zh")
    backup_translator_available = True
except ImportError:
    print("translate package not found. Backup translator will not be available. Install with: pip install translate")
    backup_translator = None
    backup_translator_available = False

logger = logging.getLogger('converter')

translation_cache = {}

def get_active_translators():
    return [
        "Google Translate (googletrans)",
        "Backup Translator (translate package)"
    ]

def contains_chinese(text):
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

# Define 2 translators as task1 and task2 without retry/backoff to avoid delays

import traceback

def task1_translate(text):
    try:
        return translator.translate(text, src='zh-cn', dest='en').text
    except Exception as e:
        logger.warning(f"Task1 translation error: {e}, retrying once immediately")
        logger.debug(traceback.format_exc())
        try:
            # Immediate retry once without delay
            return translator.translate(text, src='zh-cn', dest='en').text
        except Exception as e2:
            logger.error(f"Task1 translation error on retry: {e2}")
            logger.debug(traceback.format_exc())
            raise

def task2_translate(text):
    if not backup_translator_available:
        return text
    try:
        return backup_translator.translate(text)
    except Exception as e:
        logger.error(f"Task2 translation error: {e}")
        raise

translator_functions = [
    task1_translate,
    task2_translate
]

def batch_translate_texts(texts, batch_size=1, current_file=None, encoding_progress=None, encoding_name=None, total_files=None, current_file_index=None):
    results = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    num_translators = len(translator_functions)
    translator_index = 0  # Start with translator 1

    def translate_batch(to_translate, translator_func, prefix, batch_index, translator_idx):
        translations = []
        for text in to_translate:
            translated_text = translator_func(text)
            translations.append(translated_text)
        logger.info(f"{prefix}Batch {batch_index} translation success with translator index {translator_idx + 1}")
        return translations

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_index = i // batch_size + 1
        translation_progress = int(batch_index / total_batches * 100)
        total_progress = 0
        if total_files is not None and current_file_index is not None and encoding_progress is not None:
            total_progress = int(((current_file_index - 1) + (encoding_progress / 100)) / total_files * 100)
        prefix = ""
        if current_file is not None and encoding_progress is not None and encoding_name is not None:
            prefix = f"{current_file} <encoding conversion (GBK or UTF-8): {encoding_name} {encoding_progress}% ><translation progress: {translation_progress}% ><total progress: {total_progress}%> "

        to_translate = [t for t in batch if t is not None and contains_chinese(t) and t.strip() != ""]
        if not to_translate:
            results.extend(batch)
            continue

        translations = None
        tried_translators = 0
        current_translator_index = translator_index

        while tried_translators < num_translators:
            try:
                translations = translate_batch(to_translate, translator_functions[current_translator_index], prefix, batch_index, current_translator_index)
                translator_index = (current_translator_index + 1) % num_translators
                break
            except Exception as e:
                logger.warning(f"{prefix}Translator index {current_translator_index + 1} failed, switching to next translator immediately.")
                current_translator_index = (current_translator_index + 1) % num_translators
                tried_translators += 1

        if translations is None:
            logger.error(f"{prefix}Batch translation failed with all translators. Returning original texts.")
            translations = batch  # fallback to original texts

        if not isinstance(translations, list):
            translations = [translations]

        for t in batch:
            if t in translation_cache:
                results.append(translation_cache[t])
            else:
                # Map original to translated if possible
                idx_in_translations = batch.index(t)
                translated_text = translations[idx_in_translations] if idx_in_translations < len(translations) else t
                translation_cache[t] = translated_text
                results.append(translated_text)

    return results
