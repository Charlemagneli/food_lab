import os
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.errors import APIError


def save_image(file, folder, prefix="image", max_side=2400, max_pixels=25_000_000, quality=84):
    if not file or not file.filename:
        return None
    try:
        file.stream.seek(0)
        with Image.open(file.stream) as probe:
            probe.verify()
        file.stream.seek(0)
        with Image.open(file.stream) as source:
            width, height = source.size
            if width < 1 or height < 1 or width * height > max_pixels:
                raise APIError("image_dimensions_invalid", "图片尺寸过大或无效", 400)
            image = ImageOps.exif_transpose(source)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            # Copy pixels into a fresh image so EXIF and other source metadata are not retained.
            clean = image.copy()
            clean.info.clear()
    except APIError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise APIError("image_invalid", "请上传真实有效的 JPG、PNG、WEBP、GIF 或 AVIF 图片", 400)

    target_dir = Path(folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{uuid.uuid4().hex}.webp"
    destination = target_dir / filename
    temporary = target_dir / f".{filename}.tmp"
    try:
        clean.save(temporary, "WEBP", quality=quality, method=6)
        os.replace(temporary, destination)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise APIError("image_save_failed", "图片保存失败，请稍后重试", 500)
    return f"/images/uploads/{filename}"
