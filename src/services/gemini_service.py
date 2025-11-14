"""
Gemini 2.5 Pro統合サービス
製造業マニュアル生成のための包括的AI機能を提供
"""

import google.generativeai as genai
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason, Tool, FunctionDeclaration
import vertexai.preview.generative_models as generative_models
from typing import List, Dict, Any, Optional, Union
import json
import base64
import time
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Import GCP config helper
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.gcp_config import get_gcp_project_id

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiUnifiedService:
    """Gemini 2.5 Pro統合サービス"""
    
    def __init__(self, project_id: str = None):
        """
        初期化
        
        Args:
            project_id: Google Cloud Project ID (optional, auto-detected from credentials if not provided)
        """
        # Get configuration from environment variables or credentials file
        if project_id:
            self.project_id = project_id
        else:
            try:
                self.project_id = get_gcp_project_id()
            except ValueError as e:
                raise ValueError(f"Failed to determine GCP project ID: {e}")
        
        location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        # Vertex AI初期化
        vertexai.init(project=self.project_id, location=location)
        self.model = GenerativeModel('gemini-2.5-pro')
        
        # 安全設定
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Function Calling定義
        self.tools = self._setup_tool_definitions()
        
        logger.info("Gemini 2.5 Pro統合サービスが初期化されました")
    
    def _setup_tool_definitions(self) -> List[Tool]:
        """VertexAI用ツール定義"""
        
        # 作業手順抽出ツール
        extract_work_steps = FunctionDeclaration(
            name="extract_work_steps",
            description="動画から作業手順を構造化データとして抽出する",
            parameters={
                "type": "object",
                "properties": {
                    "work_title": {
                        "type": "string",
                        "description": "作業の名称"
                    },
                    "estimated_time": {
                        "type": "number",
                        "description": "推定作業時間（分）"
                    },
                    "skill_level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "expert"],
                        "description": "必要な技能レベル"
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_number": {"type": "integer", "description": "手順番号"},
                                "action": {"type": "string", "description": "実行する動作"},
                                "tools_used": {
                                    "type": "array", 
                                    "items": {"type": "string"},
                                    "description": "使用する工具"
                                },
                                "duration_seconds": {"type": "number", "description": "所要時間（秒）"},
                                "safety_notes": {"type": "string", "description": "安全上の注意事項"},
                                "quality_points": {"type": "string", "description": "品質管理のポイント"},
                                "expert_tips": {"type": "string", "description": "熟練者のコツ"},
                                "common_mistakes": {"type": "string", "description": "よくある失敗"}
                            },
                            "required": ["step_number", "action"]
                        }
                    }
                },
                "required": ["work_title", "steps"]
            }
        )
        
        # 作業技術比較ツール
        compare_work_techniques = FunctionDeclaration(
            name="compare_work_techniques",
            description="熟練者と非熟練者の作業技術を比較分析する",
            parameters={
                "type": "object",
                "properties": {
                    "overall_assessment": {
                        "type": "object",
                        "properties": {
                            "efficiency_gap": {"type": "string", "description": "効率性の差"},
                            "safety_gap": {"type": "string", "description": "安全性の差"},
                            "quality_gap": {"type": "string", "description": "品質の差"}
                        }
                    },
                    "detailed_differences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "aspect": {"type": "string", "description": "比較観点"},
                                "expert_approach": {"type": "string", "description": "熟練者のアプローチ"},
                                "novice_approach": {"type": "string", "description": "非熟練者のアプローチ"},
                                "improvement_suggestion": {"type": "string", "description": "改善提案"},
                                "impact_level": {
                                    "type": "string", 
                                    "enum": ["high", "medium", "low"],
                                    "description": "影響度"
                                },
                                "training_priority": {
                                    "type": "integer",
                                    "description": "研修優先度（1-5）"
                                }
                            },
                            "required": ["aspect", "expert_approach", "novice_approach", "improvement_suggestion"]
                        }
                    },
                    "recommended_training": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "skill_area": {"type": "string"},
                                "training_method": {"type": "string"},
                                "expected_improvement": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["overall_assessment", "detailed_differences"]
            }
        )
        
        # キーフレーム特定ツール
        identify_key_frames = FunctionDeclaration(
            name="identify_key_frames",
            description="動画から重要なフレーム/瞬間を特定する",
            parameters={
                "type": "object",
                "properties": {
                    "key_moments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "timestamp": {"type": "number", "description": "タイムスタンプ（秒）"},
                                "description": {"type": "string", "description": "この瞬間の説明"},
                                "importance": {
                                    "type": "string",
                                    "enum": ["critical", "important", "helpful"],
                                    "description": "重要度"
                                },
                                "category": {
                                    "type": "string",
                                    "enum": ["safety", "quality", "efficiency", "technique"],
                                    "description": "カテゴリ"
                                },
                                "annotation_text": {"type": "string", "description": "画像に追加すべき注釈"},
                                "manual_section": {"type": "string", "description": "マニュアルの該当セクション"}
                            },
                            "required": ["timestamp", "description", "importance"]
                        }
                    }
                },
                "required": ["key_moments"]
            }
        )
        
        # 文書データ抽出ツール
        extract_document_data = FunctionDeclaration(
            name="extract_document_data",
            description="文書から構造化データを抽出する",
            parameters={
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "文書の種類（マニュアル、仕様書、報告書など）"
                    },
                    "title": {
                        "type": "string",
                        "description": "文書タイトル"
                    },
                    "extracted_text": {
                        "type": "string",
                        "description": "OCRで抽出されたテキスト全文"
                    },
                    "key_information": {
                        "type": "object",
                        "properties": {
                            "specifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "parameter": {"type": "string", "description": "パラメータ名"},
                                        "value": {"type": "string", "description": "値"},
                                        "unit": {"type": "string", "description": "単位"}
                                    }
                                },
                                "description": "仕様・数値データ"
                            },
                            "safety_warnings": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "安全警告・注意事項"
                            },
                            "quality_standards": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "品質基準・許容値"
                            },
                            "procedures": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step": {"type": "integer", "description": "手順番号"},
                                        "description": {"type": "string", "description": "手順内容"},
                                        "checkpoints": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "チェックポイント"
                                        }
                                    }
                                },
                                "description": "作業手順"
                            }
                        }
                    },
                    "technical_terms": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "term": {"type": "string", "description": "専門用語"},
                                "definition": {"type": "string", "description": "定義・意味"},
                                "context": {"type": "string", "description": "使用文脈"}
                            }
                        },
                        "description": "専門用語集"
                    }
                },
                "required": ["document_type", "extracted_text", "key_information"]
            }
        )
        
        return [Tool(function_declarations=[extract_work_steps, compare_work_techniques, identify_key_frames, extract_document_data])]
        """Gemini Function Calling用関数定義"""
        return [
            {
                "name": "extract_work_steps",
                "description": "動画から作業手順を構造化データとして抽出する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "work_title": {
                            "type": "string",
                            "description": "作業の名称"
                        },
                        "estimated_time": {
                            "type": "number",
                            "description": "推定作業時間（分）"
                        },
                        "skill_level": {
                            "type": "string",
                            "enum": ["beginner", "intermediate", "expert"],
                            "description": "必要な技能レベル"
                        },
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_number": {"type": "integer", "description": "手順番号"},
                                    "action": {"type": "string", "description": "実行する動作"},
                                    "tools_used": {
                                        "type": "array", 
                                        "items": {"type": "string"},
                                        "description": "使用する工具"
                                    },
                                    "duration_seconds": {"type": "number", "description": "所要時間（秒）"},
                                    "safety_notes": {"type": "string", "description": "安全上の注意事項"},
                                    "quality_points": {"type": "string", "description": "品質管理のポイント"},
                                    "expert_tips": {"type": "string", "description": "熟練者のコツ"},
                                    "common_mistakes": {"type": "string", "description": "よくある失敗"}
                                },
                                "required": ["step_number", "action"]
                            }
                        }
                    },
                    "required": ["work_title", "steps"]
                }
            },
            {
                "name": "compare_work_techniques",
                "description": "熟練者と非熟練者の作業技術を比較分析する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "overall_assessment": {
                            "type": "object",
                            "properties": {
                                "efficiency_gap": {"type": "string", "description": "効率性の差"},
                                "safety_gap": {"type": "string", "description": "安全性の差"},
                                "quality_gap": {"type": "string", "description": "品質の差"}
                            }
                        },
                        "detailed_differences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "aspect": {"type": "string", "description": "比較観点"},
                                    "expert_approach": {"type": "string", "description": "熟練者のアプローチ"},
                                    "novice_approach": {"type": "string", "description": "非熟練者のアプローチ"},
                                    "improvement_suggestion": {"type": "string", "description": "改善提案"},
                                    "impact_level": {
                                        "type": "string", 
                                        "enum": ["high", "medium", "low"],
                                        "description": "影響度"
                                    },
                                    "training_priority": {
                                        "type": "integer",
                                        "description": "研修優先度（1-5）"
                                    }
                                },
                                "required": ["aspect", "expert_approach", "novice_approach", "improvement_suggestion"]
                            }
                        },
                        "recommended_training": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "skill_area": {"type": "string"},
                                    "training_method": {"type": "string"},
                                    "expected_improvement": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["overall_assessment", "detailed_differences"]
                }
            },
            {
                "name": "extract_document_data",
                "description": "技術文書からキー情報を抽出する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_type": {
                            "type": "string",
                            "enum": ["estimate", "blueprint", "defect_report", "specification", "manual", "other"],
                            "description": "文書の種類"
                        },
                        "key_information": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "文書タイトル"},
                                "version": {"type": "string", "description": "バージョン"},
                                "date": {"type": "string", "description": "作成日"},
                                "department": {"type": "string", "description": "担当部署"}
                            }
                        },
                        "extracted_text": {"type": "string", "description": "OCRで抽出されたテキスト"},
                        "terminology": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "term": {"type": "string", "description": "専門用語"},
                                    "definition": {"type": "string", "description": "定義・説明"},
                                    "category": {"type": "string", "description": "カテゴリ"}
                                }
                            }
                        },
                        "related_procedures": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "関連する作業手順"
                        },
                        "safety_requirements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "安全要求事項"
                        },
                        "quality_standards": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "品質基準"
                        }
                    },
                    "required": ["document_type", "extracted_text"]
                }
            },
            {
                "name": "identify_key_frames",
                "description": "動画から重要なフレーム/瞬間を特定する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key_moments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "timestamp": {"type": "number", "description": "タイムスタンプ（秒）"},
                                    "description": {"type": "string", "description": "この瞬間の説明"},
                                    "importance": {
                                        "type": "string",
                                        "enum": ["critical", "important", "helpful"],
                                        "description": "重要度"
                                    },
                                    "category": {
                                        "type": "string",
                                        "enum": ["safety", "quality", "efficiency", "technique"],
                                        "description": "カテゴリ"
                                    },
                                    "annotation_text": {"type": "string", "description": "画像に追加すべき注釈"},
                                    "manual_section": {"type": "string", "description": "マニュアルの該当セクション"}
                                },
                                "required": ["timestamp", "description", "importance"]
                            }
                        }
                    },
                    "required": ["key_moments"]
                }
            }
        ]
    
    async def analyze_expert_novice_comparison(
        self, 
        expert_video_uri: str, 
        novice_video_uri: str, 
        context_docs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        熟練者・非熟練者動画の包括的比較分析
        
        Args:
            expert_video_uri: 熟練者動画のGCS URI
            novice_video_uri: 非熟練者動画のGCS URI
            context_docs: 参考文書のリスト
            
        Returns:
            比較分析結果
        """
        logger.info("熟練者・非熟練者動画の比較分析を開始")
        
        try:
            # 1. 個別動画分析
            expert_analysis = await self._analyze_single_video(expert_video_uri, "expert")
            novice_analysis = await self._analyze_single_video(novice_video_uri, "novice")
            
            # 2. 文書コンテキスト処理
            doc_context = ""
            if context_docs:
                doc_context = await self._process_context_documents(context_docs)
            
            # 3. 比較分析実行
            comparison_prompt = f"""
製造業の作業動画比較分析を実行してください。

**前置きの挨拶や説明は不要です。直接compare_work_techniques関数を呼び出してください。**

# 分析対象
## 熟練者動画分析結果:
{json.dumps(expert_analysis, ensure_ascii=False, indent=2)}

## 非熟練者動画分析結果:
{json.dumps(novice_analysis, ensure_ascii=False, indent=2)}

# 参考資料
{doc_context}

# 分析要求
以下の観点で詳細な比較分析を行い、compare_work_techniques関数を呼び出して構造化データとして出力してください：

## 重要な分析観点:
1. **動作効率性の違い**: 無駄な動作、最適化されたパス、時間効率
2. **安全性への配慮の差**: 安全装備の使用、危険予測、事故防止行動
3. **品質管理アプローチの違い**: チェック頻度、精度確認方法、品質基準遵守
4. **工具使用方法の差異**: 持ち方、使用順序、メンテナンス配慮
5. **時間効率性の比較**: 各工程の時間配分、全体の流れ
6. **技術的習熟度**: 難易度の高い技術の習得度、応用力

## 分析深度:
- 具体的な行動の違いを詳細に記述
- 改善提案は実装可能性も考慮
- 研修計画への具体的な組み込み方法も提示
- 数値的な評価も可能な限り含める

**「承知いたしました」などの前置きは不要です。直接compare_work_techniques関数を呼び出してください。**
            """
            
            response = self.model.generate_content(
                comparison_prompt,
                tools=self.tools,
                generation_config={
                    "temperature": 0.1,  # 分析の一貫性を重視
                    "top_p": 0.8,
                    "max_output_tokens": 8192
                },
                safety_settings=self.safety_settings
            )
            
            result = self._parse_function_call_response(response)
            result['expert_analysis'] = expert_analysis
            result['novice_analysis'] = novice_analysis
            
            logger.info("比較分析が完了しました")
            return result
            
        except Exception as e:
            logger.error(f"比較分析でエラーが発生: {str(e)}")
            raise e
    
    async def _analyze_single_video(self, video_uri: str, skill_level: str) -> Dict[str, Any]:
        """
        単一動画の詳細分析
        
        Args:
            video_uri: 動画のGCS URIまたはローカルパス
            skill_level: スキルレベル（expert/novice）
            
        Returns:
            動画分析結果
        """
        logger.info(f"{skill_level}動画の分析を開始: {video_uri}")
        
        # URIの種類に応じて処理を分岐
        if video_uri.startswith('gs://'):
            # GCS URI の場合 - Part.from_uri()を使用
            logger.info(f"Using GCS URI for video analysis: {video_uri}")
            video_part = Part.from_uri(video_uri, mime_type='video/mp4')
        elif video_uri.startswith('http://') or video_uri.startswith('https://'):
            # HTTP URL の場合
            logger.info(f"Using HTTP URL for video analysis: {video_uri}")
            video_part = Part.from_uri(video_uri, mime_type='video/mp4')
        else:
            # ローカルファイルパスはサポートしない
            error_msg = f"Local file paths are not supported. Please upload video to GCS first. Path: {video_uri}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        skill_level_ja = "熟練者" if skill_level == "expert" else "非熟練者"
        
        analysis_prompt = f"""
この動画は製造業における{skill_level_ja}の作業映像です。

**前置きの説明は不要です。直接extract_work_steps関数を呼び出してください。**

以下の観点で詳細分析を行い、extract_work_steps関数を呼び出してください：

## 分析重点項目:
1. **作業手順の分解と時系列分析**
   - 各工程の開始・終了時間
   - 手順の論理的順序性
   - 並行作業の有無

2. **使用工具の識別と使用方法**
   - 工具の種類と選択理由
   - 持ち方、操作方法
   - 工具の状態確認行動

3. **安全性に関する行動パターン**
   - 保護具の着用状況
   - 危険予測行動
   - 安全確認手順

4. **品質管理のチェックポイント**
   - 測定・確認行動
   - 品質基準の確認頻度
   - エラー検出・修正プロセス

5. **効率性と技術レベル**
   - 動作の滑らかさ
   - 無駄な動作の有無
   - 技術的な熟練度

6. **注意すべき危険箇所**
   - 潜在的な危険要因
   - 事故につながりそうな行動

## {skill_level_ja}特有の特徴:
{skill_level_ja}特有の行動パターン、技術レベル、安全意識に特に注目して分析してください。

**「承知いたしました」などの前置きは不要です。直接extract_work_steps関数を呼び出してください。**
        """
        
        try:
            logger.info(f"Gemini APIに動画分析リクエストを送信中 - {skill_level}")
            response = self.model.generate_content(
                [video_part, analysis_prompt],
                tools=self.tools,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_output_tokens": 8192
                },
                safety_settings=self.safety_settings
            )
            logger.info(f"Gemini APIからの応答を受信 - {skill_level}")
        except Exception as e:
            logger.error(f"Gemini API呼び出し中にエラー: {str(e)}")
            logger.error(f"エラー詳細 - video_part: {type(video_part)}, skill_level: {skill_level}")
            raise
        
        result = self._parse_function_call_response(response)
        logger.info(f"{skill_level}動画の分析が完了")
        
        # Transform result to include work_steps at top level for compatibility
        if result.get('function_name') == 'extract_work_steps' and 'arguments' in result:
            args = result['arguments']
            # Add work_steps from arguments.steps for subtitle generation compatibility
            result['work_steps'] = args.get('steps', [])
            result['work_title'] = args.get('work_title', '')
            result['estimated_time'] = args.get('estimated_time')
            result['skill_level'] = args.get('skill_level', 'intermediate')
        
        return result
    
    async def _load_local_video(self, video_path: str) -> Part:
        """
        ローカル動画ファイルをBase64エンコードしてPartオブジェクトを作成
        
        Args:
            video_path: ローカル動画ファイルのパス
            
        Returns:
            Part: Base64エンコード済み動画データのPartオブジェクト
        """
        import os
        
        # パスの正規化（Windows形式のパス対応）
        if video_path.startswith('/uploads/') or video_path.startswith('uploads/'):
            # 相対パスをフルパスに変換
            current_dir = Path(__file__).parent.parent  # manual_generator directory
            # Windows形式のバックスラッシュを正規化
            clean_path = video_path.replace('\\', '/').lstrip('/')
            full_path = current_dir / clean_path
        else:
            full_path = Path(video_path)
        
        logger.info(f"ローカル動画ファイルを読み込み中: {full_path}")
        
        # ファイルの存在確認
        if not full_path.exists():
            raise FileNotFoundError(f"動画ファイルが見つかりません: {full_path}")
        
        # ファイルサイズチェック（Gemini APIの制限確認）
        file_size = full_path.stat().st_size
        file_size_mb = file_size / (1024*1024)
        
        # 一時的にサイズ制限を緩和（テスト用）
        max_size = 200 * 1024 * 1024  # 200MB制限
        
        logger.info(f"ファイルサイズ: {file_size_mb:.1f}MB")
        
        if file_size > max_size:
            max_size_mb = max_size / (1024*1024)
            logger.error(f"ファイルサイズが制限を超過: {file_size_mb:.1f}MB > {max_size_mb:.0f}MB")
            raise ValueError(f"動画ファイルが{max_size_mb:.0f}MBを超えています: {file_size_mb:.1f}MB。ファイルサイズを小さくしてください。")
        
        # 大きなファイルの場合は警告を出力
        if file_size_mb > 50:
            logger.warning(f"大きなファイルです: {file_size_mb:.1f}MB - 処理に時間がかかる可能性があります")
        
        # ファイルを読み込んでPartオブジェクトを作成
        with open(full_path, 'rb') as video_file:
            video_data = video_file.read()

        logger.info(f"動画ファイル読み込み完了: {len(video_data)} bytes")

        # Partオブジェクトを作成（新しいSDKではinline_dataを使用）
        import base64
        video_base64 = base64.b64encode(video_data).decode('utf-8')
        part = Part(inline_data={'mime_type': 'video/mp4', 'data': video_base64})
        logger.info(f"Partオブジェクト作成完了 - サイズ: {len(video_data)} bytes, mime_type: video/mp4")
        return part
    
    async def _process_context_documents(self, doc_paths: List[str]) -> str:
        """
        参考文書の処理とコンテキスト生成
        
        Args:
            doc_paths: 文書パスのリスト
            
        Returns:
            処理された文書コンテキスト
        """
        logger.info(f"{len(doc_paths)}件の参考文書を処理中")
        
        processed_docs = []
        for doc_path in doc_paths:
            try:
                doc_result = await self.process_document_with_ocr(doc_path, "reference")
                processed_docs.append(doc_result)
            except Exception as e:
                logger.warning(f"文書処理エラー: {doc_path} - {str(e)}")
        
        # 文書情報を統合
        context = "## 参考資料情報:\n"
        for i, doc in enumerate(processed_docs, 1):
            if 'arguments' in doc and 'extracted_text' in doc['arguments']:
                context += f"### 資料{i}:\n{doc['arguments']['extracted_text'][:500]}...\n\n"
        
        return context
    
    async def process_document_with_ocr(self, document_path: str, document_type: str) -> Dict[str, Any]:
        """
        文書のOCR処理と構造化データ抽出
        
        Args:
            document_path: 文書ファイルのパス
            document_type: 文書の種類
            
        Returns:
            構造化された文書データ
        """
        logger.info(f"文書のOCR処理を開始: {document_path}")
        
        try:
            # ファイルの読み込み
            with open(document_path, 'rb') as f:
                file_data = f.read()
            
            # ファイル形式の判定とPartオブジェクト作成
            file_extension = Path(document_path).suffix.lower()
            
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                mime_type = f'image/{file_extension[1:]}'
                if file_extension == '.jpg':
                    mime_type = 'image/jpeg'
            elif file_extension == '.pdf':
                mime_type = 'application/pdf'
            else:
                # その他のファイルは画像として処理を試行
                mime_type = 'image/jpeg'
            
            document_part = Part.from_bytes(data=file_data, mime_type=mime_type)
            
            ocr_prompt = f"""
この{document_type}の文書画像を分析し、以下を実行してください：

## OCR・文書解析タスク:
1. **テキスト抽出**: 全てのテキストを正確にOCRで読み取り
2. **文書構造理解**: 階層、セクション、表組みなどの構造を把握
3. **キー情報識別**: 重要な数値、仕様、注意事項を特定
4. **専門用語抽出**: 技術用語とその文脈を理解
5. **作業関連情報**: 手順、安全要求、品質基準を抽出

## 特に注目すべき要素:
- 部品番号、型番、仕様値
- 安全警告、注意事項
- 品質基準、許容値
- 作業手順、チェックポイント
- 図表、グラフの内容

extract_document_data関数を呼び出して、構造化データとして出力してください。
文書の種類に適した情報を重点的に抽出してください。
            """
            
            response = self.model.generate_content(
                [document_part, ocr_prompt],
                tools=self.tools,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "max_output_tokens": 8192
                },
                safety_settings=self.safety_settings
            )
            
            result = self._parse_function_call_response(response)
            logger.info(f"文書処理が完了: {document_path}")
            return result
            
        except Exception as e:
            logger.error(f"文書処理でエラーが発生: {document_path} - {str(e)}")
            raise e
    
    async def generate_comprehensive_manual_react(
        self, 
        analysis_data: Dict[str, Any], 
        output_config: Dict[str, Any]
    ) -> str:
        """
        ReAct形式での包括的マニュアル生成（推論を繰り返して精度向上）
        
        Args:
            analysis_data: 分析結果データ
            output_config: 出力設定
            
        Returns:
            生成されたマニュアル内容
        """
        logger.info("ReAct形式でのマニュアル生成を開始")
        
        # デフォルト設定
        config = {
            "format": "detailed",
            "sections": ["overview", "preparation", "steps", "expert_tips", "safety", "quality", "troubleshooting"],
            "content_length": "normal",
            "writing_style": "formal",
            "language": "ja",
            "include_comparisons": True,
            **output_config
        }
        
        # Extract template requirements
        template_description = config.get('template_description', '')
        custom_prompt = config.get('custom_prompt', '')
        sections_with_prompts = config.get('sections_with_prompts', [])
        
        logger.info(f"[REACT-INIT] Template description length: {len(template_description) if template_description else 0}")
        logger.info(f"[REACT-INIT] Template description: {template_description[:300] if template_description else 'None'}")
        logger.info(f"[REACT-INIT] Custom prompt: {custom_prompt[:200] if custom_prompt else 'None'}")
        logger.info(f"[REACT-INIT] Sections count: {len(sections_with_prompts)}")
        for idx, section in enumerate(sections_with_prompts):
            logger.info(f"[REACT-INIT] Section {idx}: {section.get('title')} - Custom prompt length: {len(section.get('custom_prompt', ''))}")
        
        # Step 1: Planning phase - Define structure
        planning_result = await self._react_planning_phase(analysis_data, config, sections_with_prompts)
        
        # Step 2: Generate each section iteratively
        section_contents = {}
        for section in sections_with_prompts:
            section_id = section.get('id')
            section_title = section.get('title')
            section_prompt = section.get('custom_prompt', '')
            
            logger.info(f"Generating section: {section_title} (ID: {section_id})")
            
            section_content = await self._react_generate_section(
                section_id=section_id,
                section_title=section_title,
                section_prompt=section_prompt,
                analysis_data=analysis_data,
                config=config,
                planning=planning_result
            )
            
            section_contents[section_id] = section_content
        
        # Step 3: Assemble final manual
        final_manual = await self._react_assembly_phase(
            section_contents=section_contents,
            sections_with_prompts=sections_with_prompts,
            template_description=template_description,
            config=config
        )
        
        logger.info("ReAct形式でのマニュアル生成が完了")
        return final_manual
    
    async def _react_planning_phase(
        self,
        analysis_data: Dict[str, Any],
        config: Dict[str, Any],
        sections_with_prompts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """ReAct Step 1: Plan the manual structure"""
        
        sections_info = "\n".join([
            f"- {s.get('title')} (ID: {s.get('id')}): {s.get('custom_prompt', 'デフォルト')}"
            for s in sections_with_prompts
        ])
        
        planning_prompt = f"""
あなたは製造業マニュアル作成の専門家です。以下の情報を基に、マニュアル構成を計画してください。

# 動画分析結果の概要
作業タイプ: {analysis_data.get('work_type', '不明')}
主要ステップ数: {len(analysis_data.get('steps', []))}

# 要求されるセクション構成
{sections_info}

# タスク
各セクションに含めるべき具体的な内容を箇条書きで計画してください。
動画分析結果から得られた情報をどのセクションに配置するか明確にしてください。

出力形式（JSON）:
{{
  "section_id": {{
    "key_points": ["ポイント1", "ポイント2", ...],
    "data_sources": ["分析結果のどの部分を使うか"],
    "focus_areas": ["重点的に記述する内容"]
  }}
}}
"""
        
        response = self.model.generate_content(
            planning_prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 4096}
        )
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning("Planning phase returned no valid JSON, using default")
                return {}
        except Exception as e:
            logger.error(f"Planning phase parsing failed: {e}")
            return {}
    
    def _get_section_guidance(self, section_title: str) -> str:
        """Get standard guidance based on section title"""
        title_lower = section_title.lower()
        
        # Common section patterns and their guidance
        guidance_map = {
            'はじめに': '作業の目的、重要性、全体の流れを簡潔に説明。読者が作業を開始する前に知っておくべき基本情報を提供。',
            '概要': '作業の全体像、目的、期待される結果を説明。',
            '準備': '必要な工具、材料、環境条件をリスト形式で列挙。各項目の用途や重要性も簡潔に説明。',
            '準備物': '必要な工具、材料、部品を箇条書きで列挙。それぞれの用途や注意点も記載。',
            '必要なもの': '作業に必要な全ての物品をカテゴリ別（工具、材料、保護具など）に整理して列挙。',
            '手順': 'ステップバイステップで作業を詳細に説明。各ステップに番号を付け、注意点を明記。',
            '作業手順': '作業を順序立てて説明。各ステップで何をするか、なぜそうするか、注意すべき点を記載。',
            '実施手順': '実施する作業を時系列で詳しく記述。各工程の目的と期待される結果も説明。',
            '注意事項': '安全に関する警告、よくある間違い、トラブルシューティングを記載。重要度の高い順に整理。',
            '安全': '作業中の安全に関する注意点、保護具の使用方法、緊急時の対応を詳しく説明。',
            '品質': '品質基準、検査方法、合格/不合格の判定基準を明確に記載。',
            'チェック': '確認すべき項目をチェックリスト形式で列挙。各項目の確認方法と基準を説明。',
            'トラブルシューティング': 'よくある問題とその解決方法を、問題→原因→対処法の形式で記載。',
            'まとめ': '作業の要点を振り返り、次のステップや関連情報を提供。',
            '参考': '関連資料、参考文献、追加情報へのリンクを提供。'
        }
        
        # Check for exact match or partial match
        for key, guidance in guidance_map.items():
            if key in title_lower or title_lower in key:
                return guidance
        
        # Default guidance if no match
        return f'「{section_title}」というタイトルに相応しい内容を生成してください。タイトルから期待される情報を適切に含めてください。'
    
    async def _react_generate_section(
        self,
        section_id: str,
        section_title: str,
        section_prompt: str,
        analysis_data: Dict[str, Any],
        config: Dict[str, Any],
        planning: Dict[str, Any]
    ) -> str:
        """ReAct Step 2: Generate individual section with reasoning"""
        
        section_plan = planning.get(section_id, {})
        
        logger.info(f"[REACT-SECTION] Generating: {section_title} (ID: {section_id})")
        logger.info(f"[REACT-SECTION] Custom prompt length: {len(section_prompt) if section_prompt else 0}")
        logger.info(f"[REACT-SECTION] Custom prompt: {section_prompt[:300] if section_prompt else 'None'}")
        
        # Build section-specific instructions based on title
        section_guidance = self._get_section_guidance(section_title)
        logger.info(f"[REACT-SECTION] Section guidance: {section_guidance}")
        
        section_generation_prompt = f"""
# セクション生成タスク

## セクション情報
- タイトル: {section_title}
- ID: {section_id}

## セクションの役割と標準的な内容
{section_guidance}

## 追加のカスタム要件
{section_prompt if section_prompt else '特になし（上記の標準的な内容に従ってください）'}

## 計画された内容
{json.dumps(section_plan, ensure_ascii=False, indent=2) if section_plan else 'なし'}

## 利用可能なデータ
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

## 生成条件
- 文体: {config.get('writing_style', 'formal')}
- 詳細度: {config.get('content_length', 'normal')}
- 言語: {config.get('language', 'ja')}

# タスク
1. まず「セクションの役割と標準的な内容」に従って基本構成を決定
2. 「追加のカスタム要件」が指定されている場合は、それを**厳密に反映**
3. 計画に沿って、利用可能なデータを活用してこのセクションの内容を生成

**重要**: 
- セクションタイトル（## {section_title}）から開始してください
- 前置きや説明は不要です。直接内容を書いてください
- カスタム要件がある場合は必ずその指示に従ってください
"""
        
        response = self.model.generate_content(
            section_generation_prompt,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 8192
            },
            safety_settings=self.safety_settings
        )
        
        return response.text if hasattr(response, 'text') else str(response)
    
    async def _react_assembly_phase(
        self,
        section_contents: Dict[str, str],
        sections_with_prompts: List[Dict[str, Any]],
        template_description: str,
        config: Dict[str, Any]
    ) -> str:
        """ReAct Step 3: Assemble and refine the complete manual"""
        
        # Assemble sections in order
        assembled_content = f"# 作業マニュアル\n\n"
        
        if template_description:
            assembled_content += f"> {template_description}\n\n"
        
        for section in sections_with_prompts:
            section_id = section.get('id')
            if section_id in section_contents:
                assembled_content += section_contents[section_id] + "\n\n"
        
        return assembled_content
    
    async def generate_comprehensive_manual(
        self, 
        analysis_data: Dict[str, Any], 
        output_config: Dict[str, Any]
    ) -> str:
        """
        包括的マニュアル生成（ReAct形式を使用）
        
        Args:
            analysis_data: 分析結果データ
            output_config: 出力設定
            
        Returns:
            生成されたマニュアル内容
        """
        logger.info("包括的マニュアル生成を開始")
        
        # Check if ReAct mode should be used
        sections_with_prompts = output_config.get('sections_with_prompts', [])
        use_react = len(sections_with_prompts) > 0
        
        if use_react:
            logger.info(f"[REACT] ReAct形式を使用してマニュアルを生成 (sections: {len(sections_with_prompts)})")
            template_description = output_config.get('template_description', '')
            logger.info(f"[REACT] Template description length: {len(template_description) if template_description else 0}")
            logger.info(f"[REACT] Sections: {[(s.get('title'), len(s.get('custom_prompt', ''))) for s in sections_with_prompts]}")
            
            print(f"\n{'='*80}")
            print(f"[REACT] ReAct形式を使用してマニュアルを生成 (sections: {len(sections_with_prompts)})")
            print(f"[REACT] Sections: {[(s.get('title'), len(s.get('custom_prompt', ''))) for s in sections_with_prompts]}")
            print(f"{'='*80}\n")
            
            return await self.generate_comprehensive_manual_react(analysis_data, output_config)
        
        # Fallback to original method
        logger.info("従来形式でマニュアルを生成")
        
        # デフォルト設定
        config = {
            "format": "detailed",
            "sections": ["overview", "preparation", "steps", "expert_tips", "safety", "quality", "troubleshooting"],
            "content_length": "normal",
            "writing_style": "formal",
            "language": "ja",
            "include_comparisons": True,
            **output_config
        }
        
        # Build custom instructions
        template_description = config.get('template_description', '')
        custom_prompt = config.get('custom_prompt', '')
        sections_with_prompts = config.get('sections_with_prompts', [])
        
        custom_instructions = ""
        if template_description:
            custom_instructions += f"\n\n## テンプレート要件\n{template_description}\n"
        
        if custom_prompt:
            custom_instructions += f"\n\n## カスタム指示\n{custom_prompt}\n"
        
        if sections_with_prompts:
            custom_instructions += "\n\n## セクション別カスタム要件\n"
            for section in sections_with_prompts:
                if isinstance(section, dict) and section.get('custom_prompt'):
                    custom_instructions += f"\n### {section.get('title', section.get('id'))}\n"
                    custom_instructions += f"{section['custom_prompt']}\n"
        
        generation_prompt = f"""
製造業作業マニュアルの自動生成を行います。

# 入力分析データ
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

# 出力設定
{json.dumps(config, ensure_ascii=False, indent=2)}
{custom_instructions}

# 重要な出力ルール
**前置きの文章は一切書かずに、直接マニュアル内容から開始してください。**
「承知いたしました」「～を基に」「～します」などの導入文は不要です。
最初の文字から「# 作業マニュアル」または「## 📋 1. 作業概要」で開始してください。

# マニュアル生成要求

以下の構造で高品質な作業マニュアルを生成してください：

## 📋 1. 作業概要
- 作業の目的と重要性
- 必要な技能レベルと前提知識
- 推定作業時間と人員配置
- 完成時の品質基準

## 🔧 2. 準備工程
- 必要工具一覧（規格・仕様含む）
- 材料・部品チェックリスト
- 安全装備と保護具の確認
- 作業環境の整備事項

## 📝 3. 詳細作業手順
- ステップバイステップの明確な指示
- 各工程の判断基準と品質チェックポイント
- 注意事項と安全警告
- 工具の正しい使用方法

## 💡 4. 熟練者のコツとベストプラクティス
- 効率化のポイント
- 高品質を実現するテクニック
- 時間短縮の工夫
- よくある失敗とその回避方法

## ⚠️ 5. 安全管理
- 潜在的な危険要因の特定
- 事故防止のための具体的対策
- 緊急時の対応手順
- 安全確認のチェックリスト

## ✅ 6. 品質管理
- 品質基準と判定方法
- 測定・検査のポイント
- 不良品の判定基準
- 品質改善のアプローチ

## 🔧 7. トラブルシューティング
- よくある問題とその症状
- 原因分析の手順
- 具体的な解決方法
- 専門部署への エスカレーション基準

## 生成条件:
- 文体: {config['writing_style']}（formal=敬語・丁寧語、conversational=わかりやすい口調、technical=技術的・簡潔）
- 詳細度: {config['content_length']}（verbose=非常に詳細、normal=標準、concise=簡潔）
- 言語: {config['language']}
- 比較分析の活用: {"あり" if config.get('include_comparisons') else "なし"}

## 品質要求:
- 専門用語は正確に使用し、必要に応じて説明を併記
- 安全性に関わる事項は特に強調
- 具体的で実行可能な指示
- 読み手のレベルに応じた適切な詳細度
- 論理的で理解しやすい構成

**繰り返しますが、前置きの挨拶や説明は一切不要です。直接マニュアル内容から開始してください。**

熟練者と非熟練者の比較分析結果を活用し、実践的で教育効果の高いマニュアルを生成してください。
        """
        
        response = self.model.generate_content(
            generation_prompt,
            generation_config={
                "temperature": 0.3,  # 創造性とバランス
                "top_p": 0.9,
                "max_output_tokens": 65535  # Gemini 2.5 Proの最大活用
            },
            safety_settings=self.safety_settings
        )
        
        logger.info("マニュアル生成が完了")
        
        # レスポンスのテキスト内容を安全に取得
        try:
            content = response.text
        except Exception as e:
            logger.warning(f"response.textの取得に失敗、代替方法を使用: {str(e)}")
            # 複数パートがある場合の代替処理
            if (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
                
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                
                if text_parts:
                    content = '\n'.join(text_parts)
                else:
                    raise Exception(f"レスポンスからテキストを抽出できませんでした: {str(e)}")
            else:
                raise Exception(f"レスポンスからテキストを抽出できませんでした: {str(e)}")
        
        # 前置き文章を除去
        content = self._remove_preamble(content)
        
        return content
    
    def _remove_preamble(self, content: str) -> str:
        """
        LLMの前置き文章を除去する
        
        Args:
            content: 元のコンテンツ
            
        Returns:
            前置き文章を除去したコンテンツ
        """
        # よくある前置き文章のパターン
        preamble_patterns = [
            r'^承知いたしました.*?(?=\n|$)',
            r'^.*?を基に.*?作成します.*?(?=\n|$)', 
            r'^.*?に基づいて.*?生成します.*?(?=\n|$)',
            r'^.*?について.*?説明します.*?(?=\n|$)',
            r'^.*?から.*?マニュアルを.*?(?=\n|$)',
            r'^.*?詳細な分析結果.*?包括的な.*?(?=\n|$)',
            r'^.*?ご提供いただいた.*?(?=\n|$)',
            r'^以下.*?作成いたします.*?(?=\n|$)',
            r'^それでは.*?(?=\n|$)',
            r'^.*?マニュアルを作成いたします.*?(?=\n|$)'
        ]
        
        import re
        
        # 各パターンで前置き文章を除去
        for pattern in preamble_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 先頭の空行を除去
        content = content.lstrip('\n ')
        
        # マークダウンヘッダーで始まっていない場合、最初の有効なヘッダーまでの内容を除去
        lines = content.split('\n')
        start_index = 0
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            # マークダウンヘッダー、番号付きリスト、箇条書きが見つかったらそこから開始
            if (stripped_line.startswith('#') or 
                stripped_line.startswith('##') or
                re.match(r'^\d+\.', stripped_line) or
                stripped_line.startswith('- ') or
                stripped_line.startswith('* ') or
                stripped_line.startswith('📋') or
                stripped_line.startswith('🔧') or
                stripped_line.startswith('📝')):
                start_index = i
                break
        
        if start_index > 0:
            content = '\n'.join(lines[start_index:])
        
        return content.strip()
    
    async def extract_key_frames_with_ai(self, video_uri: str, manual_content: str) -> Dict[str, Any]:
        """
        AIによる重要フレーム抽出とアノテーション
        
        Args:
            video_uri: 動画のGCS URI
            manual_content: マニュアル内容
            
        Returns:
            キーフレーム情報
        """
        logger.info("重要フレーム抽出を開始")
        
        video_part = Part.from_uri(video_uri, mime_type='video/mp4')
        
        frame_extraction_prompt = f"""
マニュアル内容と動画を照合し、重要なフレーム/瞬間を特定してください。

# マニュアル内容:
{manual_content[:3000]}...  # 最初の3000文字

# 実行タスク:
1. **重要瞬間の特定**: マニュアルの各工程に対応する重要な瞬間を動画から特定
2. **教育価値の評価**: 学習効果の高い場面を優先的に選択
3. **安全・品質ポイント**: 安全性や品質に関わる重要ポイントを特定
4. **アノテーション設計**: 各フレームに必要な説明や注釈を設計

# 特に重要な瞬間:
- 作業開始時の準備確認
- 危険を伴う工程
- 品質チェックポイント
- 熟練技術が必要な場面
- よくある失敗が起きやすい瞬間
- 作業完了時の確認事項

# 出力要求:
identify_key_frames関数を呼び出して、以下を含む構造化データを出力してください：
- 正確なタイムスタンプ
- 各瞬間の教育的価値
- 推奨するアノテーション内容
- マニュアル内の対応セクション

教育効果を最大化できるよう、最も重要な10-15個の瞬間を選択してください。
        """
        
        response = self.model.generate_content(
            [video_part, frame_extraction_prompt],
            tools=self.tools,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "max_output_tokens": 8192
            },
            safety_settings=self.safety_settings
        )
        
        result = self._parse_function_call_response(response)
        logger.info("重要フレーム抽出が完了")
        return result
    
    def _parse_function_call_response(self, response) -> Dict[str, Any]:
        """
        Function Calling レスポンスのパース
        
        Args:
            response: Geminiからのレスポンス
            
        Returns:
            パースされた結果
        """
        try:
            if not response.candidates or not response.candidates[0].content:
                return {
                    "error": "レスポンスにコンテンツが含まれていません",
                    "success": False
                }
            
            content = response.candidates[0].content
            parts = content.parts
            
            result = {
                "success": True,
                "parts": []
            }
            
            # 各パートを処理
            for part in parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # Function Call パート
                    function_call = part.function_call
                    result["parts"].append({
                        "type": "function_call",
                        "function_name": function_call.name,
                        "arguments": dict(function_call.args)
                    })
                elif hasattr(part, 'text') and part.text:
                    # テキストパート
                    result["parts"].append({
                        "type": "text",
                        "content": part.text
                    })
            
            # 下位互換性のため、単一のfunction_callまたはテキストの場合は従来の形式も返す
            if len(result["parts"]) == 1:
                part = result["parts"][0]
                if part["type"] == "function_call":
                    result.update({
                        "function_name": part["function_name"],
                        "arguments": part["arguments"]
                    })
                elif part["type"] == "text":
                    result["text_response"] = part["content"]
            
            return result
            
        except Exception as e:
            logger.error(f"レスポンスパースエラー: {str(e)}")
            return {
                "error": str(e),
                "success": False
            }
    
    def get_generation_config(self, task_type: str) -> Dict[str, Any]:
        """
        タスクタイプに応じた生成設定を取得
        
        Args:
            task_type: タスクの種類
            
        Returns:
            生成設定
        """
        configs = {
            "analysis": {
                "temperature": 0.1,
                "top_p": 0.8,
                "max_output_tokens": 8192
            },
            "generation": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 65535
            },
            "extraction": {
                "temperature": 0.2,
                "top_p": 0.8,
                "max_output_tokens": 8192
            }
        }
        
        return configs.get(task_type, configs["analysis"])
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using Vertex AI text-embedding-004
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (768-dim)
        """
        try:
            from vertexai.language_models import TextEmbeddingModel
            
            # Use text-embedding-004 model
            model = TextEmbeddingModel.from_pretrained('text-embedding-004')
            embeddings = model.get_embeddings([text])
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0].values
            else:
                raise Exception("No embedding returned from model")
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise Exception(f"Embedding generation failed: {str(e)}")



# Alias for backward compatibility
GeminiService = GeminiUnifiedService
