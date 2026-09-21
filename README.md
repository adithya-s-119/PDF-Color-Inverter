# PDF Color Inverter

A modern Windows desktop application for inverting the colours of PDF documents, with batch processing, live preview, drag-and-drop support, and optional English + Malayalam OCR.

## Why Use PDF Color Inverter?

PDF Color Inverter can be useful in a few practical situations:

- **Dark-mode reading:** If a PDF has a white background and is uncomfortable to read for long periods, you can invert the PDF to create a dark-background version that is easier to read in low-light environments.
- **Printing:** If a PDF has a dark or black background, you can invert it to create a white-background version that is more suitable for printing and can help reduce unnecessary dark ink or toner usage.
- **Accessibility and personal preference:** Inverting a document can make certain PDFs more comfortable to view depending on the reader's display and lighting conditions.

## Version

**1.0**

## Features

- Invert visible PDF page colours
- Batch conversion of multiple PDF files
- Add individual PDF files or an entire folder
- Native Windows drag-and-drop
- Live inverted page preview
- Per-file conversion progress and status
- Adjustable rendering quality from 100–300 DPI
- Optional English + Malayalam OCR
- Searchable and selectable OCR text
- Bundled Malayalam Unicode font
- Bundled Tesseract OCR runtime for standalone builds
- Modern CustomTkinter interface
- Light, dark, and system appearance modes
- Standalone Windows executable using PyInstaller

## OCR

OCR uses Tesseract with:

- English: `eng`
- Malayalam: `mal`
- Malayalam font: Noto Sans Malayalam

The Windows build script downloads and validates the required OCR language data and font before creating the executable.

## Requirements

For building from source:

- Windows
- Normal CPython 3.13
- Internet access during the build
- Tesseract OCR, or WinGet so the build script can install it

**Important:** use normal CPython 3.13. Do not use the Python 3.14 free-threaded build (`3.14t`).

## Build the Windows EXE

1. Clone the repository.
2. Open Command Prompt in the project directory.
3. Run:

```bat
build_windows.bat
```

The finished executable will be created at:

```text
dist\\PDFColorInverter.exe
```

The build script automatically:

1. Creates a Python 3.13 virtual environment.
2. Installs the Python dependencies.
3. Finds or installs Tesseract OCR.
4. Downloads the English and Malayalam Tesseract models.
5. Downloads the Noto Sans Malayalam font.
6. Validates the downloaded runtime files.
7. Builds a standalone one-file Windows executable.

## Run from Source

After the environment is prepared, you can run:

```bat
run_windows.bat
```

Or launch the application directly with Python:

```bat
.venv\\Scripts\\python.exe app.py
```

## Project Structure

```text
PDF-Color-Inverter/
├── app.py
├── build_windows.bat
├── run_windows.bat
├── requirements.txt
├── README.md
└── .gitignore
```

The Tesseract runtime and Malayalam font are generated locally by the build script and are intentionally excluded from Git.

## Output

Converted files are written to the selected output folder. If no output folder is selected, the application creates an `Inverted` folder beside the source PDF.

The default filename suffix is:

```text
_inverted
```

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for the full license text.

## Author

**Adithya S**

GitHub: [adithya-s-119](https://github.com/adithya-s-119)
