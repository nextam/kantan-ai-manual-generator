# Manual Generator - Gemini 2.5 Pro統合仕様書

## 📋 概要

Gemini 2.5 Proを中核AIエンジンとして活用し、製造業向けの高度な作業マニュアル自動生成システムを構築。動作分析、文書処理、テキスト生成、OCR処理まで、全てをGeminiの多機能性で統合実現。

## 🤖 Gemini 2.5 Pro活用戦略

### 1. 統合AI機能マッピング

```python
# Gemini 2.5 Pro機能統合設計
GEMINI_FUNCTIONS = {
    "video_analysis": {
        "model": "gemini-2.5-pro",
        "capabilities": [
            "multimodal_understanding",  # 動画・画像理解
            "motion_tracking",           # 動作追跡分析
            "object_detection",          # 物体認識
            "temporal_analysis"          # 時系列分析
        ]
    },
    "document_processing": {
        "model": "gemini-2.5-pro", 
        "capabilities": [
            "ocr_processing",            # OCR・文字認識
            "document_understanding",    # 文書構造理解
            "table_extraction",          # 表形式データ抽出
            "semantic_search"            # セマンティック検索
        ]
    },
    "content_generation": {
        "model": "gemini-2.5-pro",
        "capabilities": [
            "manual_creation",           # マニュアル生成
            "comparison_analysis",       # 比較分析レポート
            "terminology_explanation",  # 専門用語解説
            "safety_recommendations"    # 安全性提案
        ]
    },
    "function_calling": {
        "model": "gemini-2.5-pro",
        "capabilities": [
            "workflow_orchestration",   # 処理フロー制御
            "data_extraction",           # 構造化データ抽出
            "validation_checking",       # 品質検証
            "recommendation_engine"      # 推薦システム
        ]
    }
}
```

## 🏗️ Gemini統合アーキテクチャ

### 2. 統合AIサービス層

```python
# modules/gemini_service.py
import google.generativeai as genai
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from typing import List, Dict, Any, Optional
import json
import base64

class GeminiUnifiedService:
    """Gemini 2.5 Pro統合サービス"""
    
    def __init__(self):
        # Vertex AI初期化
        vertexai.init(project=PROJECT_ID, location='us-central1')
        self.model = GenerativeModel('gemini-2.5-pro')
        
        # Function Calling定義
        self.functions = self._setup_function_definitions()
    
    def _setup_function_definitions(self):
        """Gemini Function Calling用関数定義"""
        return [
            {
                "name": "extract_work_steps",
                "description": "動画から作業手順を構造化データとして抽出",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_number": {"type": "integer"},
                                    "action": {"type": "string"},
                                    "tools_used": {"type": "array", "items": {"type": "string"}},
                                    "duration": {"type": "number"},
                                    "safety_notes": {"type": "string"},
                                    "quality_points": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "compare_work_techniques",
                "description": "熟練者と非熟練者の作業技術を比較分析",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "differences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "aspect": {"type": "string"},
                                    "expert_approach": {"type": "string"},
                                    "novice_approach": {"type": "string"},
                                    "improvement_suggestion": {"type": "string"},
                                    "impact_level": {"type": "string", "enum": ["high", "medium", "low"]}
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "extract_document_data",
                "description": "技術文書からキー情報を抽出",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "key_data": {"type": "object"},
                        "terminology": {"type": "array", "items": {"type": "object"}},
                        "related_procedures": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        ]
    
    async def analyze_expert_novice_comparison(self, expert_video: str, novice_video: str, context_docs: List[str] = None):
        """熟練者・非熟練者動画の包括的比較分析"""
        
        # 1. 個別動画分析
        expert_analysis = await self._analyze_single_video(expert_video, "expert")
        novice_analysis = await self._analyze_single_video(novice_video, "novice")
        
        # 2. 文書コンテキスト処理
        doc_context = ""
        if context_docs:
            doc_context = await self._process_context_documents(context_docs)
        
        # 3. 比較分析実行
        comparison_prompt = f"""
        製造業の作業動画比較分析を実行してください。

        # 分析対象
        熟練者動画分析結果:
        {expert_analysis}
        
        非熟練者動画分析結果:
        {novice_analysis}
        
        # 参考資料
        {doc_context}
        
        # 分析要求
        以下の観点で詳細な比較分析を行い、compare_work_techniques関数を呼び出して構造化データとして出力してください：
        
        1. 動作効率性の違い
        2. 安全性への配慮の差
        3. 品質管理アプローチの違い
        4. 工具使用方法の差異
        5. 時間効率性の比較
        6. 改善提案の優先順位付け
        """
        
        response = await self.model.generate_content_async(
            comparison_prompt,
            tools=[{"function_declarations": self.functions}],
            generation_config={
                "temperature": 0.1,  # 分析の一貫性を重視
                "top_p": 0.8,
                "max_output_tokens": 8192
            }
        )
        
        return self._parse_function_call_response(response)
    
    async def _analyze_single_video(self, video_uri: str, skill_level: str):
        """単一動画の詳細分析"""
        
        video_part = Part.from_uri(video_uri, mime_type='video/mp4')
        
        analysis_prompt = f"""
        この動画は製造業における{skill_level}（熟練者/非熟練者）の作業映像です。
        
        以下の観点で詳細分析を行い、extract_work_steps関数を呼び出してください：
        
        1. 作業手順の分解と時系列分析
        2. 使用工具の識別と使用方法
        3. 安全性に関する行動パターン
        4. 品質管理のチェックポイント
        5. 無駄な動作や効率的な動作の識別
        6. 注意すべき危険箇所
        
        特に{skill_level}特有の行動パターンに注目して分析してください。
        """
        
        response = await self.model.generate_content_async(
            [video_part, analysis_prompt],
            tools=[{"function_declarations": self.functions}],
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "max_output_tokens": 8192
            }
        )
        
        return self._parse_function_call_response(response)
    
    async def process_document_with_ocr(self, document_path: str, document_type: str):
        """文書のOCR処理と構造化データ抽出"""
        
        # 画像として文書を読み込み
        with open(document_path, 'rb') as f:
            document_data = base64.b64encode(f.read()).decode()
        
        document_part = Part.from_data(
            data=base64.b64decode(document_data),
            mime_type='image/jpeg'  # 適切なMIMEタイプを設定
        )
        
        ocr_prompt = f"""
        この{document_type}（見積書/図面/不具合報告書など）の画像を分析し、以下を実行してください：
        
        1. 全てのテキストをOCRで正確に読み取り
        2. 文書の構造と階層を理解
        3. キー情報を抽出（部品番号、仕様、注意事項など）
        4. 専門用語とその定義を識別
        5. 作業手順に関連する情報を抽出
        
        extract_document_data関数を呼び出して、構造化データとして出力してください。
        """
        
        response = await self.model.generate_content_async(
            [document_part, ocr_prompt],
            tools=[{"function_declarations": self.functions}],
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "max_output_tokens": 8192
            }
        )
        
        return self._parse_function_call_response(response)
    
    async def generate_comprehensive_manual(self, analysis_data: Dict, output_config: Dict):
        """包括的マニュアル生成"""
        
        generation_prompt = f"""
        製造業作業マニュアルの自動生成を行います。
        
        # 入力データ
        分析結果: {json.dumps(analysis_data, ensure_ascii=False, indent=2)}
        
        # 出力設定
        {json.dumps(output_config, ensure_ascii=False, indent=2)}
        
        # 生成要求
        以下の構造で高品質なマニュアルを生成してください：
        
        ## 1. 作業概要
        - 目的と重要性
        - 必要な技能レベル
        - 推定作業時間
        
        ## 2. 準備工程
        - 必要工具一覧
        - 材料・部品チェックリスト
        - 安全装備確認
        
        ## 3. 詳細作業手順
        - ステップバイステップ指示
        - 各工程の品質チェックポイント
        - 注意事項と安全警告
        
        ## 4. 熟練者のコツ
        - 効率化のポイント
        - よくある失敗と対策
        - 品質向上のテクニック
        
        ## 5. トラブルシューティング
        - よくある問題と解決方法
        - 緊急時の対応手順
        
        文体は{output_config.get('writing_style', 'formal')}で、
        詳細度は{output_config.get('content_length', 'normal')}レベルで生成してください。
        """
        
        response = await self.model.generate_content_async(
            generation_prompt,
            generation_config={
                "temperature": 0.3,  # 創造性とバランス
                "top_p": 0.9,
                "max_output_tokens": 65535  # Gemini 2.5 Proの最大活用
            }
        )
        
        return response.text
    
    async def extract_key_frames_with_ai(self, video_uri: str, manual_content: str):
        """AIによる重要フレーム抽出とアノテーション"""
        
        video_part = Part.from_uri(video_uri, mime_type='video/mp4')
        
        frame_extraction_prompt = f"""
        マニュアル内容と動画を照合し、以下を実行してください：
        
        マニュアル内容:
        {manual_content}
        
        # 実行内容
        1. マニュアルの各工程に対応する重要な瞬間を動画から特定
        2. 安全性や品質に関わる重要ポイントを画像として抽出
        3. 各フレームに対する詳細な説明とアノテーション情報を生成
        4. 推奨する画像挿入位置をマニュアル内で特定
        
        # 出力形式
        フレーム抽出指示と詳細説明をJSON形式で出力してください。
        """
        
        response = await self.model.generate_content_async(
            [video_part, frame_extraction_prompt],
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "max_output_tokens": 8192
            }
        )
        
        return json.loads(response.text)
    
    def _parse_function_call_response(self, response):
        """Function Calling レスポンスのパース"""
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            return {
                "function_name": function_call.name,
                "arguments": dict(function_call.args)
            }
        else:
            return {"text_response": response.text}
```

### 3. エンドポイント統合

```python
# app.py への追加機能
from modules.gemini_service import GeminiUnifiedService

@app.route('/ai_comparison_analysis', methods=['POST'])
async def ai_comparison_analysis():
    """Gemini AIによる熟練者・非熟練者比較分析"""
    try:
        data = request.get_json()
        gemini_service = GeminiUnifiedService()
        
        result = await gemini_service.analyze_expert_novice_comparison(
            expert_video=data['expert_video_uri'],
            novice_video=data['novice_video_uri'],
            context_docs=data.get('reference_documents', [])
        )
        
        return jsonify({
            'success': True,
            'analysis_result': result,
            'ai_engine': 'gemini-2.5-pro'
        })
        
    except Exception as e:
        return jsonify({'error': f'AI分析エラー: {str(e)}'}), 500

@app.route('/ai_document_processing', methods=['POST'])
async def ai_document_processing():
    """Gemini AIによる文書処理・OCR"""
    try:
        files = request.files.getlist('documents')
        gemini_service = GeminiUnifiedService()
        
        processed_docs = []
        for file in files:
            # 一時保存
            temp_path = save_temp_file(file)
            
            # Gemini OCR & 構造化
            result = await gemini_service.process_document_with_ocr(
                temp_path, 
                file.filename.split('.')[-1]
            )
            
            processed_docs.append(result)
        
        return jsonify({
            'success': True,
            'processed_documents': processed_docs,
            'ai_engine': 'gemini-2.5-pro'
        })
        
    except Exception as e:
        return jsonify({'error': f'文書処理エラー: {str(e)}'}), 500

@app.route('/ai_comprehensive_manual_generation', methods=['POST'])
async def ai_comprehensive_manual_generation():
    """Gemini AIによる包括的マニュアル生成"""
    try:
        data = request.get_json()
        gemini_service = GeminiUnifiedService()
        
        # 1. 比較分析実行
        if 'expert_video' in data and 'novice_video' in data:
            comparison_result = await gemini_service.analyze_expert_novice_comparison(
                data['expert_video'], 
                data['novice_video'],
                data.get('reference_documents')
            )
        else:
            comparison_result = {}
        
        # 2. マニュアル生成
        manual_content = await gemini_service.generate_comprehensive_manual(
            comparison_result,
            data['output_config']
        )
        
        # 3. キーフレーム抽出
        if data.get('include_images', True):
            key_frames = await gemini_service.extract_key_frames_with_ai(
                data['expert_video'],
                manual_content
            )
        else:
            key_frames = []
        
        return jsonify({
            'success': True,
            'manual_content': manual_content,
            'key_frames': key_frames,
            'comparison_analysis': comparison_result,
            'ai_engine': 'gemini-2.5-pro',
            'generation_timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': f'マニュアル生成エラー: {str(e)}'}), 500
```

## 🎯 Gemini 2.5 Pro活用の利点

### 1. 統合AI処理による高精度化
- **マルチモーダル理解**: 動画・画像・テキストの同時処理
- **文脈理解**: 専門用語と作業手順の関連性理解
- **一貫性確保**: 単一AIによる処理での情報整合性

### 2. Function Callingによる構造化出力
- **データ品質向上**: 決められた形式での確実な出力
- **処理効率化**: 後処理の自動化とエラー削減
- **拡張性**: 新機能追加時の関数定義拡張

### 3. 大容量コンテキスト活用
- **包括的分析**: 複数動画・文書の同時考慮
- **詳細出力**: 65,535トークンでの詳細マニュアル生成
- **継続的学習**: 過去の分析結果の活用

## 📈 期待される技術的効果

### 精度向上指標
- **動作認識精度**: 95%以上（従来85%）
- **文書理解精度**: 98%以上（OCR + 意味理解）
- **マニュアル品質**: 専門用語使用率90%以上
- **一貫性スコア**: 95%以上（複数生成での一貫性）

### 処理効率化
- **統合処理**: 従来の6つのAIツール → Gemini 1つに集約
- **開発工数**: 60%削減（API統合の簡素化）
- **運用コスト**: 40%削減（単一プロバイダー活用）

この仕様により、Gemini 2.5 Proの先進的な機能を最大限活用した、製造業特化の高精度マニュアル生成システムが実現されます。
