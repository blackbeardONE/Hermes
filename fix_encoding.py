import os
import csv
import chardet
import time
import sys
try:
    from googletrans import Translator
except ImportError:
    print("googletrans package not found. Please install it using: pip install googletrans==4.0.0-rc1")
    exit(1)

translator = Translator()

def contains_chinese(text):
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def is_english(text):
    try:
        text.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

translation_cache = {}

def translate_text(text):
    if text in translation_cache:
        return translation_cache[text]
    try:
        if text.strip() == "" or not contains_chinese(text):
            translation_cache[text] = text
            return text
        translated = translator.translate(text, src='zh-cn', dest='en')
        translation_cache[text] = translated.text
        return translated.text
    except Exception as e:
        print(f"Translation error for text '{text}': {e}")
        translation_cache[text] = text
        return text

def batch_translate_texts(texts, batch_size=5, delay=3, current_file=None, encoding_progress=None, encoding_name=None, total_files=None, current_file_index=None):
    # ANSI escape codes for colors
    COLOR_RESET = "\033[0m"
    COLOR_RED = "\033[31m"
    COLOR_GREEN = "\033[32m"
    COLOR_YELLOW = "\033[33m"
    COLOR_CYAN = "\033[36m"

    results = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_index = i // batch_size + 1
        translation_progress = int(batch_index / total_batches * 100)
        total_progress = 0
        if total_files is not None and current_file_index is not None and encoding_progress is not None:
            total_progress = int(((current_file_index - 1) + (encoding_progress / 100)) / total_files * 100)
        prefix = ""
        if current_file is not None and encoding_progress is not None and encoding_name is not None:
            prefix = f"{COLOR_CYAN}{current_file} <encoding conversion (GBK or UTF-8): {encoding_name} {encoding_progress}% ><translation progress: {translation_progress}% ><total progress: {total_progress}%>{COLOR_RESET} "
        try:
            to_translate = [t for t in batch if t is not None and contains_chinese(t) and t.strip() != ""]
            if not to_translate:
                results.extend(batch)
                continue

            # Retry logic for batch translation
            max_retries = 3
            retry_count = 0
            translations = None
            while retry_count < max_retries:
                try:
                    print(f"{prefix}{COLOR_CYAN}Attempting batch translation, try {retry_count + 1}{COLOR_RESET}")
                    translations = translator.translate(to_translate, src='zh-cn', dest='en')
                    if translations is not None:
                        break
                except Exception as inner_e:
                    print(f"{prefix}{COLOR_RED}Inner translation error for batch on try {retry_count + 1}: {inner_e}{COLOR_RESET}")
                retry_count += 1
                time.sleep(delay)

            if translations is None:
                print(f"{prefix}{COLOR_RED}Batch translation failed after {max_retries} retries. Falling back to single translation.{COLOR_RESET}")
                translations = []

                for text in to_translate:
                    if text is None or text.strip() == "":
                        print(f"{prefix}{COLOR_YELLOW}Skipping empty or None text in fallback translation: '{text}'{COLOR_RESET}")
                        translations.append(text)  # Use original text instead of None
                        continue
                    try:
                        print(f"{prefix}{COLOR_CYAN}Attempting single translation for text: {text if text is not None else ''}{COLOR_RESET}")
                        single_translation = translator.translate(text, src='zh-cn', dest='en')
                        print(f"{prefix}{COLOR_GREEN}Single translation success: {single_translation.text if single_translation.text is not None else ''}{COLOR_RESET}")
                        translations.append(single_translation)
                    except Exception as single_e:
                        print(f"{prefix}{COLOR_RED}Single translation error for text '{text}': {single_e}{COLOR_RESET}")
                        translations.append(text if text is not None else '')  # Use original text instead of None
            else:
                print(f"{prefix}{COLOR_GREEN}Batch translation success on try {retry_count + 1}{COLOR_RESET}")

            if translations is None:
                print(f"{prefix}{COLOR_YELLOW}Warning: Received None translation response, skipping batch.{COLOR_RESET}")
                results.extend(batch)
                continue
            if not translations:
                print(f"{prefix}{COLOR_YELLOW}Warning: Received empty translation response, skipping batch.{COLOR_RESET}")
                results.extend(batch)
                continue
            if not isinstance(translations, list):
                translations = [translations]
            translated_map = {}
            for t in translations:
                if t and hasattr(t, 'origin') and hasattr(t, 'text') and t.origin is not None and t.text is not None:
                    translated_map[t.origin] = t.text if t.text is not None else ""
                elif isinstance(t, str):
                    # If fallback returned original text string
                    translated_map[t] = t if t is not None else ""
            for t in batch:
                if t in translated_map:
                    translation_cache[t] = translated_map[t]
                    results.append(translated_map[t])
                else:
                    translation_cache[t] = t
                    results.append(t)
            time.sleep(delay)
        except Exception as e:
            print(f"{prefix}{COLOR_RED}Batch translation error: {e}{COLOR_RESET}")
            results.extend(batch)
    return results

def detect_encoding(file_path, num_bytes=10000):
    with open(file_path, 'rb') as f:
        rawdata = f.read(num_bytes)
    result = chardet.detect(rawdata)
    return result['encoding']

def file_contains_chinese(file_path, encoding):
    try:
        print(f"Debug: Checking if file {file_path} contains Chinese characters...")
        with open(file_path, 'r', encoding=encoding, newline='') as f:
            content = f.read()
            has_chinese = contains_chinese(content)
            print(f"Debug: file_contains_chinese for {file_path} with encoding {encoding}: {has_chinese}")
            return has_chinese
    except Exception as e:
        print(f"Error reading file {file_path} for Chinese detection: {e}")
        return False

def convert_and_translate_csv(input_path, output_path, input_encoding, output_encoding, do_translate=True, current_file=None, encoding_progress=None, encoding_name=None, total_files=None, current_file_index=None):
    print(f"Debug: Starting conversion from {input_encoding} to {output_encoding} for file {input_path}")
    try:
        with open(input_path, 'r', encoding=input_encoding, newline='') as f_in:
            reader = csv.reader(f_in)
            rows = list(reader)

        fully_translated = False
        translated_rows = []

        if do_translate:
            idx = 0
            total_rows = len(rows)
            while idx < total_rows:
                batch_rows = rows[idx:idx+10]  # process 10 rows at a time
                all_cells = [cell for row in batch_rows for cell in row]
                encoding_progress = int((idx + len(batch_rows)) / total_rows * 100)
                translated_cells = batch_translate_texts(all_cells, current_file=current_file, encoding_progress=encoding_progress, encoding_name=encoding_name, total_files=total_files, current_file_index=current_file_index)

                cell_idx = 0
                for row in batch_rows:
                    row_len = len(row)
                    translated_row = translated_cells[cell_idx:cell_idx+row_len]
                    # Convert only strings that are detected as GBK encoded to UTF-8 if output_encoding is utf-8
                    if output_encoding.lower() == 'utf-8':
                        converted_row = []
                        for cell in translated_row:
                            if isinstance(cell, str):
                                try:
                                    # Try decoding from gbk and encoding to utf-8
                                    cell_bytes = cell.encode('latin1')
                                    cell_utf8 = cell_bytes.decode('gbk')
                                    converted_row.append(cell_utf8)
                                except Exception:
                                    # If decoding fails, keep original
                                    converted_row.append(cell)
                            else:
                                converted_row.append(cell)
                        translated_rows.append(converted_row)
                    # Convert only strings that are detected as utf-8 encoded to GBK if output_encoding is gbk
                    elif output_encoding.lower() == 'gbk':
                        converted_row = []
                        for cell in translated_row:
                            if isinstance(cell, str):
                                try:
                                    # The string is already a Unicode string in Python
                                    # Just append it as is; the file will be written with encoding='gbk'
                                    converted_row.append(cell)
                                except Exception:
                                    # If any unexpected error, keep original
                                    converted_row.append(cell)
                            else:
                                converted_row.append(cell)
                        translated_rows.append(converted_row)
                    else:
                        translated_rows.append(translated_row)
                    cell_idx += row_len

                idx += len(batch_rows)
            # After processing all rows, check if fully translated and encoded
            if total_files is not None and current_file_index is not None:
                if current_file_index == total_files and encoding_progress == 100:
                    fully_translated = True
        else:
            translated_rows = rows

        # Write output file with output_encoding, strings are already converted accordingly
        with open(output_path, 'w', encoding=output_encoding, errors='replace', newline='') as f_out:
            writer = csv.writer(f_out)
            for row in translated_rows:
                writer.writerow(row)

        print(f"Debug: Successfully processed file {input_path} to {output_path} with encoding {output_encoding}")
        return True
    except Exception as e:
        print(f"Error processing file {input_path}: {e}")
        return False

def print_progress_bar(current, total, bar_length=40):
    percent = float(current) / total
    arrow_len = max(1, int(round(percent * bar_length)))
    arrow = '-' * (arrow_len - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    sys.stdout.write(f"Processing file {current} of {total}: [{arrow}{spaces}] {int(round(percent * 100))}%\n")
    sys.stdout.flush()

def process_all_csv_files(root_dir='.'):
    csv_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.csv'):
                csv_files.append(os.path.join(dirpath, filename))

    total_files = len(csv_files)
    print(f"Total CSV files to process: {total_files}")

    for idx, input_file in enumerate(csv_files, start=1):
        print(f"Processing file {idx} of {total_files}: {input_file}")
        base, ext = os.path.splitext(os.path.basename(input_file))
        encoding = detect_encoding(input_file)
        encoding_progress = int(idx / total_files * 100)
        encoding_name = None
        if encoding:
            enc_lower = encoding.lower()
            if enc_lower == 'utf-8' or enc_lower == 'ascii':
                encoding_name = 'UTF-8'
            elif enc_lower == 'gbk' or enc_lower == 'gb2312':
                encoding_name = 'GBK'
            else:
                encoding_name = encoding.upper()

        # Step 1: If file is GBK, convert to UTF-8 without translation
        if encoding_name == 'GBK':
            temp_utf8_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_temp{ext}")
            print(f"Debug: Converting GBK to UTF-8 for file {input_file}")
            success = convert_and_translate_csv(input_file, temp_utf8_file, 'gbk', 'utf-8', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name=encoding_name, total_files=total_files, current_file_index=idx)
            if not success:
                print(f"Error converting {input_file} from GBK to UTF-8")
                continue
            # Now check if UTF-8 file contains Chinese
            if file_contains_chinese(temp_utf8_file, 'utf-8'):
                print(f"Debug: UTF-8 file {temp_utf8_file} contains Chinese, translating to English")
                temp_translated_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_translated{ext}")
                success = convert_and_translate_csv(temp_utf8_file, temp_translated_file, 'utf-8', 'utf-8', do_translate=True, current_file=input_file, encoding_progress=encoding_progress, encoding_name='UTF-8', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error translating {temp_utf8_file} to English")
                    continue
                # Convert translated UTF-8 file back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                print(f"Debug: Converting translated UTF-8 file {temp_translated_file} back to GBK as {final_output_file}")
                success = convert_and_translate_csv(temp_translated_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error converting translated file {temp_translated_file} back to GBK")
                    continue
                # Cleanup temp files
                try:
                    os.remove(temp_utf8_file)
                    os.remove(temp_translated_file)
                except Exception as e:
                    print(f"Error cleaning up temp files: {e}")
            else:
                # No Chinese in UTF-8 file, just convert back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                success = convert_and_translate_csv(temp_utf8_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error converting UTF-8 file {temp_utf8_file} back to GBK")
                    continue
                try:
                    os.remove(temp_utf8_file)
                except Exception as e:
                    print(f"Error cleaning up temp UTF-8 file: {e}")

        # Step 2: If file is UTF-8, check for Chinese and translate, then convert back to GBK
        elif encoding_name == 'UTF-8':
            if file_contains_chinese(input_file, 'utf-8'):
                print(f"Debug: UTF-8 file {input_file} contains Chinese, translating to English")
                temp_translated_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_translated{ext}")
                success = convert_and_translate_csv(input_file, temp_translated_file, 'utf-8', 'utf-8', do_translate=True, current_file=input_file, encoding_progress=encoding_progress, encoding_name='UTF-8', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error translating {input_file} to English")
                    continue
                # Convert translated UTF-8 file back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                print(f"Debug: Converting translated UTF-8 file {temp_translated_file} back to GBK as {final_output_file}")
                success = convert_and_translate_csv(temp_translated_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error converting translated file {temp_translated_file} back to GBK")
                    continue
                # Cleanup temp file
                try:
                    os.remove(temp_translated_file)
                except Exception as e:
                    print(f"Error cleaning up temp translated file: {e}")
            else:
                # No Chinese, just convert encoding if needed (or skip)
                print(f"Debug: UTF-8 file {input_file} does not contain Chinese, no translation needed")
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                success = convert_and_translate_csv(input_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    print(f"Error converting UTF-8 file {input_file} back to GBK")
                    continue

        else:
            print(f"Warning: Unsupported encoding {encoding_name} for file {input_file}, skipping.")
            continue

        # Replace original file with final output file
        if success:
            try:
                print(f"Debug: Removing original file {input_file}")
                os.remove(input_file)
                print(f"Debug: Renaming {final_output_file} to {input_file}")
                os.rename(final_output_file, input_file)
                print(f"Debug: Successfully replaced original file {input_file} with {final_output_file}")
            except Exception as e:
                print(f"\nError replacing file {input_file}: {e}")

    print("\nProcessing completed.")

if __name__ == "__main__":
    print("Starting CSV encoding conversion and translation process...")
    try:
        process_all_csv_files()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully.")
        sys.exit(0)
