# Hermes

## Introduction

Hermes is a Python package designed for processing CSV files with a focus on encoding conversion and translation. It automates the detection of file encodings, converts between common encodings such as GBK, UTF-8, and ISO-8859-9, and translates Chinese text within CSV files into English. Hermes is particularly useful for batch processing large sets of CSV files, ensuring consistent encoding and language translation.

## Features

- **Encoding Detection and Conversion**: Automatically detects the encoding of CSV files and converts between GBK, UTF-8, and ISO-8859-9 as needed.
- **Chinese Text Detection and Translation**: Identifies Chinese text within CSV files and translates it to English using batch translation for efficiency.
- **Batch Processing**: Processes all CSV files within a specified directory, handling large volumes of data seamlessly.
- **Progress Tracking and Resuming**: Maintains translation progress in a JSON file, allowing interrupted processes to resume without loss of work.
- **Logging and Error Handling**: Provides detailed logging of the conversion and translation process, including error reporting and cleanup of temporary files.

## Use Cases

- Translating CSV files containing Chinese text into English for localization or data analysis.
- Converting CSV files between different encodings to ensure compatibility with various systems and software.
- Automating the processing of large directories of CSV files to save time and reduce manual effort.
- Resuming interrupted translation or conversion tasks without starting over.

## How to Use

Run the main script `converter.py` with the path to the directory containing CSV files:

```bash
python Hermes/converter.py /path/to/csv/files
```

If no path is provided as a command line argument, the script will prompt for a folder path, defaulting to the current directory if left blank.

The script will:

1. Detect all CSV files in the specified directory and its subdirectories.
2. Detect the encoding of each CSV file.
3. Convert files from GBK or ISO-8859-9 to UTF-8 as needed.
4. Translate Chinese text within the files to English using batch translation.
5. Convert translated files back to the original encoding (usually GBK).
6. Replace the original files with the translated and converted versions.
7. Track progress in `translation_progress.json` to allow resuming.

## Dependencies

- `googletrans` (version 4.0.0-rc1) for primary translation.
- Optional: `translate` package as a backup translator.
- Standard Python libraries: `csv`, `os`, `json`, `logging`, etc.

Install dependencies using:

```bash
pip install googletrans==4.0.0-rc1
pip install translate  # optional, for backup translator
```

## Logging

Hermes uses a logging system to record the progress and any errors during processing. Logs are useful for troubleshooting and monitoring the batch processing of CSV files.

## Summary

Hermes is a robust tool for automating the conversion and translation of CSV files, especially useful for handling Chinese text and ensuring compatibility across different encoding standards. It supports batch processing, progress tracking, and error handling to facilitate efficient and reliable data processing workflows.
