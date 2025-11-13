"""
File: output_formats.py
Purpose: Define output format configurations for unified manual generation
Main functionality: Output format constants and validation
Dependencies: None
"""

# Output format definitions
OUTPUT_FORMATS = {
    "text_only": {
        "name": "テキストのみ",
        "name_en": "Text Only",
        "description": "画像なし、テキスト中心の詳細マニュアル",
        "description_en": "Detailed text-only manual without images",
        "use_case": "新人教育・詳細資料",
        "use_case_en": "Training and detailed documentation",
        "features": {
            "extract_images": False,
            "extract_video_clips": False,
            "generate_subtitles": False,
            "detailed_text": True
        },
        "icon": "📝"
    },
    "text_with_images": {
        "name": "テキスト + 画像",
        "name_en": "Text with Images",
        "description": "テキストに画像切り抜きを挿入",
        "description_en": "Text manual with image snapshots",
        "use_case": "現場作業者向け",
        "use_case_en": "For on-site workers",
        "features": {
            "extract_images": True,
            "extract_video_clips": False,
            "generate_subtitles": False,
            "detailed_text": True
        },
        "icon": "🖼️",
        "recommended": True
    },
    "text_with_video_clips": {
        "name": "テキスト + 動画クリップ",
        "name_en": "Text with Video Clips",
        "description": "該当箇所の短尺動画プレビュー付き",
        "description_en": "Text with short video clips for each step",
        "use_case": "動的な手順確認",
        "use_case_en": "Dynamic step verification",
        "features": {
            "extract_images": False,
            "extract_video_clips": True,
            "generate_subtitles": False,
            "detailed_text": True
        },
        "icon": "🎬"
    },
    "subtitle_video": {
        "name": "字幕付き動画",
        "name_en": "Subtitled Video",
        "description": "元動画に作業手順の字幕を自動挿入",
        "description_en": "Original video with auto-generated subtitles",
        "use_case": "視覚的学習",
        "use_case_en": "Visual learning",
        "features": {
            "extract_images": False,
            "extract_video_clips": False,
            "generate_subtitles": True,
            "detailed_text": False
        },
        "icon": "📹"
    },
    "hybrid": {
        "name": "ハイブリッド",
        "name_en": "Hybrid",
        "description": "複数形式を組み合わせ",
        "description_en": "Combined multiple formats",
        "use_case": "包括的なマニュアル",
        "use_case_en": "Comprehensive manual",
        "features": {
            "extract_images": True,
            "extract_video_clips": True,
            "generate_subtitles": True,
            "detailed_text": True
        },
        "icon": "⚙️"
    }
}


def get_format_info(format_key):
    """
    Get output format information
    
    Args:
        format_key: Output format key
        
    Returns:
        Format configuration dict or None
    """
    return OUTPUT_FORMATS.get(format_key)


def is_valid_format(format_key):
    """
    Check if format key is valid
    
    Args:
        format_key: Output format key
        
    Returns:
        Boolean
    """
    return format_key in OUTPUT_FORMATS


def get_default_format():
    """
    Get default output format
    
    Returns:
        Default format key
    """
    return "text_with_images"


def get_format_list():
    """
    Get list of all available formats
    
    Returns:
        List of format info dicts
    """
    return [
        {
            "key": key,
            **info
        }
        for key, info in OUTPUT_FORMATS.items()
    ]
