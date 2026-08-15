import io
import os
from typing import Optional, Tuple
import pymupdf  # PyMuPDF
from pypdf import PdfReader, PdfWriter

def compress_pdf(file_bytes: bytes, max_size_mb: int = 10, quality: int = 70) -> Tuple[bytes, str]:
    """
    Compress PDF file to reduce size while maintaining readability.
    Uses PyMuPDF for image downsampling (best for scanned PDFs 25-35MB -> ~10MB).
    Falls back to pypdf if PyMuPDF fails.
    
    Args:
        file_bytes: Original PDF bytes
        max_size_mb: Target maximum size in MB
        quality: Compression quality (1-100, higher = better quality but larger file)
    
    Returns:
        tuple of (compressed_bytes, compression_status)
    """
    original_size = len(file_bytes)
    
    if original_size <= max_size_mb * 1024 * 1024:
        return file_bytes, "no_compression_needed"
    
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        
        image_scale = quality / 100.0
        if image_scale < 0.3:
            image_scale = 0.3
        if image_scale > 1.0:
            image_scale = 1.0
        
        for page in doc:
            images = page.get_images(full=True)
            for img_index, img in enumerate(images, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    pil_image = None
                    try:
                        from PIL import Image
                        import io as _io
                        pil_image = Image.open(_io.BytesIO(img_bytes))
                    except Exception:
                        pil_image = None
                    
                    if pil_image:
                        width, height = pil_image.size
                        new_width = int(width * image_scale)
                        new_height = int(height * image_scale)
                        if new_width < 1:
                            new_width = 1
                        if new_height < 1:
                            new_height = 1
                        
                        if pil_image.mode in ("RGBA", "P"):
                            pil_image = pil_image.convert("RGB")
                        
                        resized = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        out_buffer = _io.BytesIO()
                        resized.save(out_buffer, format="JPEG", quality=quality, optimize=True)
                        doc.update_image(xref, stream=out_buffer.getvalue())
        
        compressed_bytes = doc.tobytes(
            deflate=True,
            garbage=4,
            clean=True,
        )
        doc.close()
        
        compressed_size = len(compressed_bytes)
        reduction = ((original_size - compressed_size) / original_size) * 100
        
        if compressed_size > max_size_mb * 1024 * 1024 and quality > 30:
            return compress_pdf(file_bytes, max_size_mb, quality - 15)
        
        status = f"compressed_{reduction:.1f}%"
        return compressed_bytes, status
        
    except Exception as e:
        print(f"PyMuPDF compression failed: {e}, falling back to pypdf")
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            writer = PdfWriter()
            
            for page in reader.pages:
                writer.add_page(page)
            
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            compressed_bytes = output_buffer.getvalue()
            
            compressed_size = len(compressed_bytes)
            reduction = ((original_size - compressed_size) / original_size) * 100
            
            if compressed_size > max_size_mb * 1024 * 1024 and quality > 30:
                return compress_pdf(file_bytes, max_size_mb, quality - 20)
            
            status = f"compressed_{reduction:.1f}%"
            return compressed_bytes, status
        except Exception as e2:
            print(f"pypdf fallback compression failed: {e2}")
            return file_bytes, "compression_failed"

def compress_pdf_to_size(file_bytes: bytes, target_size_mb: int = 10) -> bytes:
    try:
        compressed, status = compress_pdf(file_bytes, target_size_mb)
        return compressed
    except Exception:
        return file_bytes
