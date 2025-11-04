import re
from urllib.parse import unquote
from typing import List, Tuple

# Canonicalization rules:
# 1. URL decode
# 2. If starts with gs://<bucket>/ -> strip scheme+bucket
# 3. Remove leading uploads/ once
# 4. Collapse duplicate leading video/ (video/video/ -> video/)
# 5. Fix _mp4 extension to .mp4 (for legacy compatibility)
# 6. Return canonical path (e.g., video/xxxx.mp4)
# 7. Provide all tried candidates for logging / fallback

def fix_mp4_extension(file_path: str) -> str:
    """
    Legacy compatibility: Convert _mp4 suffix to .mp4 extension
    This handles files that were stored with incorrect extensions due to
    secure_filename() removing dots from Japanese filenames.
    
    Args:
        file_path: File path that may end with _mp4
        
    Returns:
        File path with proper .mp4 extension
    """
    if file_path.endswith('_mp4'):
        return file_path[:-4] + '.mp4'
    return file_path

def normalize_video_path(raw_path: str) -> Tuple[str, List[str]]:
    if not raw_path:
        return raw_path, []
    candidates: List[str] = []
    try:
        decoded = unquote(raw_path)
    except Exception:
        decoded = raw_path
    candidates.append(decoded)

    work = decoded
    if work.startswith('gs://'):
        without = work[5:]  # after gs://
        bucket, sep, rest = without.partition('/')
        if rest:
            work = rest
            candidates.append(work)
    # strip one leading uploads/
    if work.startswith('uploads/'):
        work2 = work[len('uploads/'):]
        candidates.append(work2)
        work = work2
    # collapse duplicated video/ prefix
    while work.startswith('video/video/'):
        work = work[len('video/') :]
        candidates.append(work)
    # Ensure we have at least one candidate that starts with video/
    if not work.startswith('video/') and ('/video/' in work):
        # e.g., something/video/filename
        idx = work.find('video/')
        tail = work[idx:]
        candidates.append(tail)
        work = tail

    # Fix _mp4 extension for legacy compatibility
    work = fix_mp4_extension(work)
    if work != candidates[-1]:  # Only add if different
        candidates.append(work)

    # Deduplicate preserving order
    seen = set()
    dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            dedup.append(c)

    canonical = work
    return canonical, dedup

__all__ = ["normalize_video_path", "fix_mp4_extension"]
