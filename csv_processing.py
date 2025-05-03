import os
import csv
import sys
import time
import logging
import json
from translation_utils import contains_chinese, batch_translate_texts
from encoding_utils import detect_encoding, file_contains_chinese

logger = logging.getLogger('converter')

PROGRESS_FILE = 'translation_progress.json'

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load progress file: {e}")
            return {}
    return {}

def save_progress(progress):
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save progress file: {e}")

def print_progress_bar(current, total, bar_length=40):
    # ANSI color codes for Windows CMD
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    percent = float(current) / total
    arrow_len = max(1, int(round(percent * bar_length)))
    arrow = GREEN + '-' * (arrow_len - 1) + '>' + RESET
    spaces = ' ' * (bar_length - len(arrow))
    sys.stdout.write(f"{YELLOW}Processing file {current} of {total}:{RESET} [{arrow}{spaces}] {int(round(percent * 100))}%\n")
    sys.stdout.flush()

def convert_and_translate_csv(input_path, output_path, input_encoding, output_encoding, do_translate=True, current_file=None, encoding_progress=None, encoding_name=None, total_files=None, current_file_index=None, start_row=0):
    import encoding_utils
    import io
    logger.debug(f"Starting conversion from {input_encoding} to {output_encoding} for file {input_path} starting at row {start_row}")
    try:
        # Read file in binary mode and decode lines dynamically to handle mixed encodings
        decoded_lines = encoding_utils.decode_mixed_encoding_file(input_path)
        # Use io.StringIO to create a file-like object from decoded lines for csv.reader
        csv_content = io.StringIO('\n'.join(decoded_lines))
        reader = csv.reader(csv_content)
        rows = list(reader)

        fully_translated = False
        translated_rows = rows[:start_row]  # Keep already translated rows if resuming

        if do_translate:
            idx = start_row
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
                                    # Use safe encoding to GBK with replacement for errors
                                    encoded_bytes = encoding_utils.encode_utf8_to_gbk_safe(cell)
                                    decoded_cell = encoded_bytes.decode('gbk', errors='replace')
                                    converted_row.append(decoded_cell)
                                except Exception:
                                    # If any unexpected error, keep original
                                    converted_row.append(cell)
                            else:
                                converted_row.append(cell)
                        translated_rows.append(converted_row)
                    else:
                        # If output encoding is neither utf-8 nor gbk, just append translated row as is
                        translated_rows.append(translated_row)
                    cell_idx += row_len
                idx += len(batch_rows)
            fully_translated = True
        else:
            translated_rows = rows

        # Write translated rows to output file with specified encoding
        # Add errors='replace' for gbk encoding to avoid encoding errors
        if output_encoding.lower() == 'gbk':
            f_out = open(output_path, 'w', encoding=output_encoding, errors='replace', newline='')
        else:
            f_out = open(output_path, 'w', encoding=output_encoding, newline='')
        with f_out:
            writer = csv.writer(f_out)
            writer.writerows(translated_rows)

        return True
    except Exception as e:
        logger.error(f"Error processing file {input_path}: {e}")
        return False

def process_all_csv_files(root_dir='.'):
    csv_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.csv'):
                csv_files.append(os.path.join(dirpath, filename))

    total_files = len(csv_files)
    print(f"Total CSV files to process: {total_files}")

    progress = load_progress()

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
            elif enc_lower == 'iso-8859-9':
                encoding_name = 'ISO-8859-9'
            else:
                encoding_name = encoding.upper()

        start_row = progress.get(input_file, 0)

        # Step 1: If file is GBK, convert to UTF-8 without translation
        if encoding_name == 'GBK':
            temp_utf8_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_temp{ext}")
            logger.debug(f"Converting GBK to UTF-8 for file {input_file}")
            success = convert_and_translate_csv(input_file, temp_utf8_file, 'gbk', 'utf-8', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name=encoding_name, total_files=total_files, current_file_index=idx)
            if not success:
                logger.error(f"Error converting {input_file} from GBK to UTF-8")
                continue
            # Now check if UTF-8 file contains Chinese
            if file_contains_chinese(temp_utf8_file, 'utf-8'):
                logger.debug(f"UTF-8 file {temp_utf8_file} contains Chinese, translating to English")
                temp_translated_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_translated{ext}")
                success = convert_and_translate_csv(temp_utf8_file, temp_translated_file, 'utf-8', 'utf-8', do_translate=True, current_file=input_file, encoding_progress=encoding_progress, encoding_name='UTF-8', total_files=total_files, current_file_index=idx, start_row=start_row)
                if not success:
                    logger.error(f"Error translating {temp_utf8_file} to English")
                    continue
                # Convert translated UTF-8 file back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                logger.debug(f"Converting translated UTF-8 file {temp_translated_file} back to GBK as {final_output_file}")
                success = convert_and_translate_csv(temp_translated_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting translated file {temp_translated_file} back to GBK")
                    continue
                # Cleanup temp files
                try:
                    os.remove(temp_utf8_file)
                    os.remove(temp_translated_file)
                except Exception as e:
                    logger.error(f"Error cleaning up temp files: {e}")
            else:
                # No Chinese in UTF-8 file, just convert back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                success = convert_and_translate_csv(temp_utf8_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting UTF-8 file {temp_utf8_file} back to GBK")
                    continue
                try:
                    os.remove(temp_utf8_file)
                except Exception as e:
                    logger.error(f"Error cleaning up temp UTF-8 file: {e}")

        # Step 2: If file is UTF-8, check for Chinese and translate, then convert back to GBK
        elif encoding_name == 'UTF-8':
            if file_contains_chinese(input_file, 'utf-8'):
                logger.debug(f"UTF-8 file {input_file} contains Chinese, translating to English")
                temp_translated_file = os.path.join(os.path.dirname(input_file), f"{base}_utf8_translated{ext}")
                success = convert_and_translate_csv(input_file, temp_translated_file, 'utf-8', 'utf-8', do_translate=True, current_file=input_file, encoding_progress=encoding_progress, encoding_name='UTF-8', total_files=total_files, current_file_index=idx, start_row=start_row)
                if not success:
                    logger.error(f"Error translating {input_file} to English")
                    continue
                # Convert translated UTF-8 file back to GBK
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                logger.debug(f"Converting translated UTF-8 file {temp_translated_file} back to GBK as {final_output_file}")
                success = convert_and_translate_csv(temp_translated_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting translated file {temp_translated_file} back to GBK")
                    continue
                # Cleanup temp file
                try:
                    os.remove(temp_translated_file)
                except Exception as e:
                    logger.error(f"Error cleaning up temp translated file: {e}")
            else:
                # No Chinese, just convert encoding if needed (or skip)
                logger.debug(f"UTF-8 file {input_file} does not contain Chinese, no translation needed")
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_gbk{ext}")
                success = convert_and_translate_csv(input_file, final_output_file, 'utf-8', 'gbk', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='GBK', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting UTF-8 file {input_file} back to GBK")
                    continue

        elif encoding_name == 'ISO-8859-9':
            # Treat ISO-8859-9 similar to UTF-8 for processing
            if file_contains_chinese(input_file, 'iso-8859-9'):
                logger.debug(f"ISO-8859-9 file {input_file} contains Chinese, translating to English")
                temp_translated_file = os.path.join(os.path.dirname(input_file), f"{base}_iso88599_translated{ext}")
                success = convert_and_translate_csv(input_file, temp_translated_file, 'iso-8859-9', 'utf-8', do_translate=True, current_file=input_file, encoding_progress=encoding_progress, encoding_name='ISO-8859-9', total_files=total_files, current_file_index=idx, start_row=start_row)
                if not success:
                    logger.error(f"Error translating {input_file} to English")
                    continue
                # Convert translated UTF-8 file back to ISO-8859-9
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_iso88599{ext}")
                logger.debug(f"Converting translated UTF-8 file {temp_translated_file} back to ISO-8859-9 as {final_output_file}")
                success = convert_and_translate_csv(temp_translated_file, final_output_file, 'utf-8', 'iso-8859-9', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='ISO-8859-9', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting translated file {temp_translated_file} back to ISO-8859-9")
                    continue
                # Cleanup temp file
                try:
                    os.remove(temp_translated_file)
                except Exception as e:
                    logger.error(f"Error cleaning up temp translated file: {e}")
            else:
                # No Chinese, just convert encoding if needed (or skip)
                logger.debug(f"ISO-8859-9 file {input_file} does not contain Chinese, no translation needed")
                final_output_file = os.path.join(os.path.dirname(input_file), f"{base}_translated_iso88599{ext}")
                success = convert_and_translate_csv(input_file, final_output_file, 'iso-8859-9', 'iso-8859-9', do_translate=False, current_file=input_file, encoding_progress=encoding_progress, encoding_name='ISO-8859-9', total_files=total_files, current_file_index=idx)
                if not success:
                    logger.error(f"Error converting ISO-8859-9 file {input_file}")
                    continue

        else:
            logger.warning(f"Unsupported encoding {encoding_name} for file {input_file}, skipping.")
            continue

        # Replace original file with final output file
        if success:
            try:
                logger.debug(f"Removing original file {input_file}")
                os.remove(input_file)
                logger.debug(f"Renaming {final_output_file} to {input_file}")
                os.rename(final_output_file, input_file)
                logger.debug(f"Successfully replaced original file {input_file} with {final_output_file}")
            except Exception as e:
                logger.error(f"Error replacing file {input_file}: {e}")

    print("\nProcessing completed.")
