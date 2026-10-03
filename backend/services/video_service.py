from typing import Tuple, List, Dict, Any

ALLOWED_EXTENSIONS = [".mp4", ".mov", ".m4v", ".webm", ".mkv"]
MIN_DURATION = 25.0
MAX_DURATION = 45.0
MAX_FILE_SIZE = 100 * 1024 * 1024 # 100 MB
MIN_WIDTH = 720
MIN_HEIGHT = 1280
IDEAL_WIDTH = 1080
IDEAL_HEIGHT = 1920

def validate_video_metadata(
    file_name: str,
    file_size: int,
    duration: float,
    width: int,
    height: int
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Extension Check
    lower_name = file_name.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        errors.append(f"Invalid file format '{file_name}'. Only MP4 and MOV formats are accepted.")

    # 2. File Size Check
    if file_size <= 0:
        errors.append("Invalid file size (0 bytes).")
    elif file_size > MAX_FILE_SIZE:
        errors.append(f"File size exceeds the 100MB limit (Current size: {round(file_size / (1024 * 1024), 2)}MB).")

    # 3. Duration Check (25s - 45s)
    duration_valid = True
    if duration < MIN_DURATION:
        errors.append(f"Video duration is {round(duration, 1)}s. Minimum required duration is 25 seconds.")
        duration_valid = False
    elif duration > MAX_DURATION:
        errors.append(f"Video duration is {round(duration, 1)}s. Maximum allowed duration is 45 seconds.")
        duration_valid = False

    # 4. Dimension and Aspect Ratio Check
    resolution_valid = True
    aspect_ratio_valid = True
    aspect_ratio_str = "Unknown"

    if width > 0 and height > 0:
        ratio = height / width
        aspect_ratio_str = f"{width}:{height}"

        # Check portrait orientation
        if height <= width:
            errors.append("Video must be in vertical portrait mode (9:16 aspect ratio). Horizontal or square videos are not accepted.")
            aspect_ratio_valid = False
        elif not (1.6 <= ratio <= 1.9): # 9:16 is 1.777...
            warnings.append(f"Video aspect ratio is approximately {width}x{height}. Standard vertical 9:16 (1080x1920) is recommended.")
            # Note: We give a warning if slightly non-standard, but accept if close portrait
            if ratio < 1.4:
                errors.append("Video aspect ratio is not 9:16 portrait.")
                aspect_ratio_valid = False

        if width < MIN_WIDTH or height < MIN_HEIGHT:
            warnings.append(f"Resolution is {width}x{height}. Optimal resolution is 1080x1920 px.")
            if width < 480 or height < 640:
                errors.append("Video resolution is too low for evaluation. Minimum 720p portrait is required.")
                resolution_valid = False
    else:
        errors.append("Invalid video dimensions provided.")
        resolution_valid = False

    return {
        "valid": len(errors) == 0,
        "duration_valid": duration_valid,
        "resolution_valid": resolution_valid,
        "aspect_ratio_valid": aspect_ratio_valid,
        "aspect_ratio": "9:16" if aspect_ratio_valid else aspect_ratio_str,
        "errors": errors,
        "warnings": warnings,
    }
