# PDF Color Inverter v3.6

This release fixes the Windows build script so the English and Malayalam Tesseract models are passed correctly to the download routine. The previous script called `:download` without arguments, causing PowerShell to receive an empty URL and report `Invalid URI: The hostname could not be parsed.`

The application itself is based on v3.5 and includes:
- Modern CustomTkinter interface
- PDF colour inversion
- Batch conversion queue
- Native Windows drag-and-drop
- Live page preview
- Optional English + Malayalam OCR
- Bundled Tesseract OCR runtime
- Bundled Noto Sans Malayalam font
- Standalone PyInstaller EXE build

## Build

Run `build_windows.bat` from this folder. The script explicitly uses normal CPython 3.13 and does not use Python 3.14 free-threaded (`3.14t`).

The build downloads `eng.traineddata`, `mal.traineddata`, and the Noto Sans Malayalam font, verifies them, and then bundles them into the EXE. Runtime downloads are kept out of the Git repository.