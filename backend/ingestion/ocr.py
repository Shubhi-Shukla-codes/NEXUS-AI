"""
NEXUS Offline Native OCR Engine
Provides zero-dependency, local-first OCR using Windows 10/11 built-in
Windows.Media.Ocr APIs via PowerShell WinRT bridge.
100% offline, air-gapped compliant, requiring no cloud APIs or external binaries.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger("nexus.ingestion.ocr")

# PowerShell script template for Windows Native OCR
POWERSHELL_OCR_SCRIPT = """
param (
    [string]$ImageDir,
    [string]$OutputFile
)

[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataWriter, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}[0]

function AwaitOperation($op, $type) {
    $t = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    while (-not $t.IsCompleted) { [System.Threading.Thread]::Sleep(15) }
    if ($t.IsFaulted) { throw $t.Exception.InnerException }
    return $t.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new("en-US"))
}

$results = @{}
$files = Get-ChildItem -Path $ImageDir -Filter "*.png" | Sort-Object Name

foreach ($f in $files) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
        $stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        $writer = New-Object Windows.Storage.Streams.DataWriter($stream)
        $writer.WriteBytes($bytes)
        $stored = AwaitOperation ($writer.StoreAsync()) ([System.UInt32])
        $stream.Seek(0)

        $decoder = AwaitOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = AwaitOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $ocrRes = AwaitOperation ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

        $results[$f.Name] = $ocrRes.Text
    } catch {
        $results[$f.Name] = ""
    }
}

$json = $results | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText($OutputFile, $json, [System.Text.Encoding]::UTF8)
"""


def is_ocr_available() -> bool:
    """Check if Windows native OCR or alternative OCR is available on system."""
    if sys.platform != "win32":
        return False
    try:
        # Quick probe of PowerShell Windows.Media.Ocr availability
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null; Write-Output 'OK'"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return "OK" in res.stdout
    except Exception as exc:
        logger.warning("OCR availability check failed: %s", exc)
        return False


def ocr_rendered_images(image_dir: Path) -> Dict[str, str]:
    """
    Execute batch OCR on all PNG images in image_dir.
    Returns mapping: { "page_1.png": "Extracted text..." }
    """
    out_json = image_dir / "ocr_output.json"
    script_path = image_dir / "run_ocr.ps1"
    
    script_path.write_text(POWERSHELL_OCR_SCRIPT, encoding="utf-8")
    
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
        "-ImageDir", str(image_dir),
        "-OutputFile", str(out_json)
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            logger.error("PowerShell OCR execution failed: %s", proc.stderr)
            return {}
            
        if out_json.exists():
            content = out_json.read_text(encoding="utf-8-sig")
            if content.strip():
                return json.loads(content)
        return {}
    except Exception as exc:
        logger.error("Error executing OCR batch: %s", exc)
        return {}


def ocr_pdf_pages_fallback(pdf_path: Path, page_indices: List[int], dpi: int = 150) -> Dict[int, str]:
    """
    Render specified pages of a PDF to images and extract text using offline native OCR.
    Args:
        pdf_path: Path to PDF file
        page_indices: 0-indexed list of page indices to process
        dpi: Rendering resolution (default 150 DPI for balance of speed and clarity)
    Returns:
        Mapping of page_index (0-indexed) to extracted text
    """
    if not page_indices:
        return {}
        
    import fitz
    
    results: Dict[int, str] = {}
    with tempfile.TemporaryDirectory(prefix="nexus_ocr_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        doc = fitz.open(str(pdf_path))
        
        idx_to_file = {}
        for idx in page_indices:
            if 0 <= idx < len(doc):
                page = doc[idx]
                pix = page.get_pixmap(dpi=dpi)
                fname = f"page_{idx:04d}.png"
                img_path = tmp_dir / fname
                pix.save(str(img_path))
                idx_to_file[fname] = idx
                
        doc.close()
        
        if not idx_to_file:
            return {}
            
        ocr_res = ocr_rendered_images(tmp_dir)
        for fname, text in ocr_res.items():
            if fname in idx_to_file:
                results[idx_to_file[fname]] = text or ""
                
    return results
