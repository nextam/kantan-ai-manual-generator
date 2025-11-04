"""動画解析マニュアル生成システム（画像あり）

ポリシー: vertexai ライブラリは使用せず、google-genai の Vertex モード (client = genai.Client(vertexai=True,...)) を常に利用。
"""
from __future__ import annotations

import os, cv2, json, base64, numpy as np, logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from google import genai  # type: ignore
from google.genai import types  # type: ignore
Part = types.Part  # google-genai Part を直接使用

logger = logging.getLogger(__name__)

# GCS動画ローカルキャッシュ: 同一 gs:// 動画の再ダウンロードを避ける (プロセス存続中のみ有効)
_GCS_VIDEO_LOCAL_CACHE: Dict[str, str] = {}


class ManualWithImagesGenerator:
    """マニュアル（画像あり）生成システム (google-genai / vertexモード固定)"""

    def __init__(self, project_id: str | None = None, location: str = "us-central1") -> None:
        # .env 読み込み（存在すれば）
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = location
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID が未設定です")
        creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds and not os.path.isabs(creds):
            base = Path(__file__).resolve().parents[1]
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str((base / creds).resolve())
        self._model_name = "gemini-2.5-pro"
        self._client = genai.Client(vertexai=True, project=self.project_id, location=self.location)  # type: ignore
        logger.info("google-genai Vertexモード初期化完了 (manual with images)")

    def _generate_content(self, parts):
        return self._client.models.generate_content(model=self._model_name, contents=parts)  # type: ignore

    # ---------- 共通: サンプルフレーム抽出 ----------
    def extract_video_samples(self, video_path: str, sample_count: int = 15) -> List[Dict[str, Any]]:
        temp_local_path = None
        original_path = video_path
        # gs:// 対応: 一時ダウンロードしてローカルパスを OpenCV に渡す
        if video_path.startswith('gs://'):
            try:
                import tempfile
                from google.cloud import storage  # Lazy import for environments without GCS
                bucket_name_path = video_path[5:]
                bucket_name, blob_path = bucket_name_path.split('/', 1)
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                suffix = os.path.splitext(blob_path)[1] or '.mp4'
                fd, temp_local_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                blob.download_to_filename(temp_local_path)
                logger.info(f"GCS動画を一時ダウンロード: {video_path} -> {temp_local_path}")
                video_path = temp_local_path
            except Exception as e:
                raise RuntimeError(f"GCS動画の一時ダウンロードに失敗: {video_path} ({e})")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            # 失敗時に一時ファイルをクリーンアップ
            if temp_local_path and os.path.exists(temp_local_path):
                try: os.remove(temp_local_path)
                except Exception: pass
            raise ValueError(f"動画ファイルを開けません: {original_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = max(1, total_frames // max(1, sample_count))

        frames: List[Dict[str, Any]] = []
        current = 0
        while current < total_frames and len(frames) < sample_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current)
            ok, frame = cap.read()
            if not ok:
                break
            ts = (current / fps) if fps else 0.0
            frames.append({
                "frame_number": current,
                "timestamp": ts,
                "timestamp_formatted": f"{int(ts//60):02d}:{int(ts%60):02d}",
                "frame": frame,
            })
            current += frame_interval

        cap.release()
        # 一時ファイル削除
        if temp_local_path and os.path.exists(temp_local_path):
            try:
                os.remove(temp_local_path)
                logger.debug(f"一時GCS動画ファイル削除: {temp_local_path}")
            except Exception:
                pass
        logger.info(f"サンプルフレーム抽出: {len(frames)}件")
        return frames

    # ---------- Stage 1: 作業ステップ分析 ----------
    def stage_1_analyze_work_steps(self, video_path: str, custom_prompt: Dict[str, Any] | None = None) -> Dict[str, Any]:
        logger.info("=== 1段階: 作業ステップ分析開始 ===")
        frames = self.extract_video_samples(video_path, sample_count=15)

        # 画像パーツ
        image_parts = []
        for fd in frames:
            # JPEGエンコード
            ok, buf = cv2.imencode('.jpg', fd['frame'], [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            jpeg_bytes = buf.tobytes()
            # 古い google-genai 1.1.0 には Part.from_data が無いため from_bytes を使用
            image_parts.append(Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"))

        # ユーザー入力情報の取得
        user_title = (custom_prompt or {}).get('title') or ''
        user_description = (custom_prompt or {}).get('description') or ''
        purpose = (custom_prompt or {}).get('purpose') or user_description or ''
        extra = (custom_prompt or {}).get('custom_instruction') or ''
        
        # タイトル情報をプロンプトに含める
        title_info = f"【対象作業】{user_title}\n" if user_title else ""
        
        if extra:
            style_directives = (
                f"{title_info}"
                "【執筆スタイル指示】\n"
                f"{extra}\n\n"
                f"- 目的: {purpose or '現場で活用できる実用的な作業マニュアル'}\n"
                "- 基本スタイル: 体言止めの箇条書き（名詞/名詞句で終える）。動詞終止形は避ける。\n"
                "- 箇条書き例: 『図面確認』『部材数量チェック』『仮締め実施』など。\n"
            )
        else:
            style_directives = (
                f"{title_info}"
                "【執筆スタイル指示】\n"
                f"- 目的: {purpose or '現場で活用できる実用的な作業マニュアル'}\n"
                "- 基本スタイル: 体言止めの箇条書き（名詞/名詞句で終える）。動詞終止形は避ける。\n"
                "- 必要に応じて安全上の注意を明記する\n"
                "- 箇条書き例: 『図面確認』『部材数量チェック』『仮締め実施』など。\n"
            )

        frames_list_text = [f"フレーム{i+1}: {f['timestamp_formatted']}" for i, f in enumerate(frames)]
        prompt = (
            "あなたは製造業の作業手順書作成の専門家です。提供された動画フレーム画像を分析し、作業の流れとタイムスタンプを特定してください。\n\n"
            f"動画情報:\n- 総フレーム数: {len(frames)}\n- 各フレームのタイムスタンプ: {frames_list_text}\n\n"
            f"{style_directives}\n\n"
            "重要: 必ず以下のJSONフォーマットで回答してください。他のテキストは含めず、JSONのみを返してください。\n\n"
            "{\n"
            "  \"work_title\": \"作業全体のタイトル\",\n"
            "  \"work_type\": \"作業の種類（組立、検査、など）\",\n"
            "  \"estimated_duration\": \"予想作業時間（分）\",\n"
            "  \"difficulty_level\": \"初級/中級/上級\",\n"
            "  \"work_steps\": [\n"
            "    {\n"
            "      \"step_number\": 1,\n"
            "      \"step_title\": \"作業ステップのタイトル\",\n"
            "      \"step_description\": \"作業内容の詳細説明（文体と文量指示に合わせる）\",\n"
            "      \"start_timestamp\": \"00:15\",\n"
            "      \"end_timestamp\": \"00:45\",\n"
            "      \"start_seconds\": 15.0,\n"
            "      \"end_seconds\": 45.0,\n"
            "      \"representative_frame\": 3,\n"
            "      \"key_actions\": [\"具体的な動作1\", \"具体的な動作2\"],\n"
            "      \"important_points\": [\"重要ポイント1\", \"重要ポイント2\"],\n"
            "      \"safety_notes\": \"安全上の注意点（必要に応じて）\"\n"
            "    }\n"
            "  ],\n"
            "  \"required_tools\": [\"必要な工具リスト\"],\n"
            "  \"materials\": [\"使用する材料\"],\n"
            "  \"overall_notes\": \"全体的な注意事項\"\n"
            "}\n\n"
            "指示:\n"
            "1. 画像を時系列で分析し、明確な作業ステップを特定\n"
            "2. 各ステップの開始・終了タイミングを推定\n"
            "3. 代表的なフレーム番号を指定（1からフレーム数の範囲）\n"
            "4. 現場で使用できる実用的な内容にする\n"
            "5. 日本語で回答\n"
            "6. JSONフォーマットを厳密に守り、他のテキストは一切含めない\n"
        )

        try:
            contents = [prompt] + image_parts
            response = self._generate_content(contents)
            text = (response.text or '').strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            data.update({
                "stage": 1,
                "timestamp": datetime.now().isoformat(),
                "video_path": video_path,
                "sample_frames_count": len(frames),
            })
            logger.info(f"1段階完了: {len(data.get('work_steps', []))}ステップ分析")
            return data
        except json.JSONDecodeError as e:
            logger.error("1段階: JSON解析失敗")
            return {
                "stage": 1,
                "error": f"JSON decode error: {e}",
                "raw_response": text[:1000] if 'text' in locals() else '',
                "work_steps": [],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise RuntimeError(f"1段階の作業分析に失敗しました: {e}")

    # ---------- Stage 1 (hybrid/text-only) ----------
    def stage_1_analyze_work_steps_text_only(self, video_path: str, custom_prompt: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """フレーム抽出なしで動画 URI を直接解析し手順 JSON を得る軽量版"""
        logger.info("=== 1段階(hybrid): テキストのみ解析開始 ===")
        if not video_path.startswith('gs://'):
            logger.warning("hybrid stage1 にローカルパスが渡されました。推奨は GCS URI")
        # ユーザー入力情報の取得
        user_title = (custom_prompt or {}).get('title') or ''
        user_description = (custom_prompt or {}).get('description') or ''
        purpose = (custom_prompt or {}).get('purpose') or user_description or ''
        extra = (custom_prompt or {}).get('custom_instruction') or ''
        
        # タイトル情報をプロンプトに含める
        title_instruction = f"対象作業: {user_title}\n" if user_title else ""
        
        # カスタムプロンプトを最優先で配置
        if extra:
            prompt = f"""あなたは製造業の作業手順書作成の専門家です。

{title_instruction}{extra}

動画全体を分析し作業手順を JSON 形式で返却してください。
代表フレームは後段で生成するため、ここでは step の代表フレーム番号は連番仮値で構いません。
目的: {purpose or '現場で活用できる実用的なマニュアル'}
出力は既定フォーマット JSON のみ。他の文字列禁止。"""
        else:
            prompt = (
                f"あなたは製造業の作業手順書作成の専門家です。{title_instruction}動画全体を分析し作業手順を JSON 形式で返却してください。"
                "代表フレームは後段で生成するため、ここでは step の代表フレーム番号は連番仮値で構いません。"
                f"目的: {purpose or '現場で活用できる実用的なマニュアル'}\n"
                "安全/品質上の留意点を含めて作成してください。\n"
                "出力は既定フォーマット JSON のみ。他の文字列禁止。"
            )
        part = Part.from_uri(file_uri=video_path, mime_type='video/mp4')
        try:
            resp = self._generate_content([prompt, part])
            text = (resp.text or '').strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            data = json.loads(text)
            steps = data.get('work_steps', [])
            for i, s in enumerate(steps, 1):
                s.setdefault('representative_frame', i)
            data.update({'stage':1,'mode':'hybrid_text_only','sample_frames_count':0,'video_path':video_path})
            logger.info(f"1段階(hybrid) 完了: {len(steps)}ステップ")
            return data
        except Exception as e:
            raise RuntimeError(f"1段階(hybrid) 解析失敗: {e}")

    # ---------- Stage 2: 代表フレーム抽出 ----------
    def fix_frame_orientation(self, frame: np.ndarray, video_path: str) -> np.ndarray:
        """フレームの上下を強制補正 (常に縦方向反転)"""
        try:
            from utils.frame_orientation import enforce_vertical_orientation, ALWAYS_FLIP_VERTICAL, ALWAYS_FLIP_HORIZONTAL
            flipped = enforce_vertical_orientation(frame)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"generator.orientation.flip vertical={ALWAYS_FLIP_VERTICAL} horizontal={ALWAYS_FLIP_HORIZONTAL} size={frame.shape if frame is not None else None}")
            return flipped
        except Exception:
            # 失敗した場合は元のフレームを返却
            return frame

    def stage_2_extract_representative_frames(self, video_path: str, stage1_result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== 2段階: 代表フレーム抽出開始 (ゼロモデル前処理 + Gemini再ランキング) ===")
        if not stage1_result.get('work_steps'):
            raise ValueError("1段階の結果に作業ステップが含まれていません")

        def _laplacian_sharpness(img: np.ndarray) -> float:
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                return float(cv2.Laplacian(gray, cv2.CV_64F).var())
            except Exception:
                return 0.0

        def _brightness(img: np.ndarray) -> float:
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                return float(np.mean(gray))
            except Exception:
                return 0.0

        def _normalize(values: List[float]) -> List[float]:
            if not values:
                return values
            vmin, vmax = min(values), max(values)
            if vmax - vmin < 1e-6:
                return [0.5 for _ in values]
            return [(v - vmin) / (vmax - vmin) for v in values]

        def _candidate_timestamps(start_s: float, end_s: float) -> List[float]:
            if end_s <= start_s:
                end_s = start_s + 5.0
            dur = end_s - start_s
            return sorted({
                round(start_s + dur * 0.25, 3),
                round(start_s + dur * 0.5, 3),
                round(start_s + dur * 0.75, 3)
            })

        def _gemini_rank(step_meta: Dict[str, Any], candidates: List[Dict[str, Any]]) -> int:
            if not candidates:
                return -1
            # Vertex AI 利用不可の場合はシャープネス最大
            # rerank は常に gemini 利用 (fallback なし) 想定
            try:
                prompt = (
                    "あなたは製造業の作業手順可視化アシスタントです。候補画像からそのステップを最も明確に示す1枚を選択してください。"
                    "出力はJSONのみ。フォーマット: {\n"
                    "  \"selected_index\": <0-based index>,\n"
                    "  \"confidence\": 0.0〜1.0,\n"
                    "  \"scores\": [ { \"index\": i, \"relevance\":1-5, \"clarity\":1-5, \"stability\":1-5 } ]\n"
                    "}\n"
                    f"ステップ番号: {step_meta.get('step_number')} タイトル: {step_meta.get('step_title')}\n"
                    f"説明: {step_meta.get('step_description','')}\n"
                    "評価観点: relevance=動作の核心が写っているか / clarity=ピンぼけや暗さが少ない / stability=ブレや途中遷移の瞬間でない。"
                )
                parts = [prompt]
                for c in candidates:
                    parts.append(Part.from_bytes(data=base64.b64decode(c['image_base64']), mime_type='image/jpeg'))
                response = self._generate_content(parts)
                txt = (response.text or '').strip()
                if txt.startswith('```json'):
                    txt = txt[7:]
                if txt.startswith('```'):
                    txt = txt[3:]
                if txt.endswith('```'):
                    txt = txt[:-3]
                txt = txt.strip()
                data = json.loads(txt)
                idx = int(data.get('selected_index', 0))
                if 0 <= idx < len(candidates):
                    return idx
                return int(np.argmax([c['sharpness'] for c in candidates]))
            except Exception as e:
                logger.warning(f"Gemini再ランキング失敗: {e}. シャープネスfallback")
                return int(np.argmax([c['sharpness'] for c in candidates]))

        # ---- gs:// パスをローカル実体へ (キャッシュ利用) ----
        local_path = video_path
        if video_path.startswith('gs://'):
            cached = _GCS_VIDEO_LOCAL_CACHE.get(video_path)
            if cached and os.path.exists(cached):
                local_path = cached
                logger.debug(f"GCS動画キャッシュ再利用(Stage2): {video_path} -> {local_path}")
            else:
                try:
                    import tempfile
                    from google.cloud import storage  # type: ignore
                    bucket_name, blob_path = video_path[5:].split('/', 1)
                    client = storage.Client(); bucket = client.bucket(bucket_name); blob = bucket.blob(blob_path)
                    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(blob_path)[1] or '.mp4'); os.close(fd)
                    blob.download_to_filename(tmp_path)
                    _GCS_VIDEO_LOCAL_CACHE[video_path] = tmp_path
                    local_path = tmp_path
                    logger.info(f"GCS動画ダウンロード(Stage2): {video_path} -> {tmp_path}")
                except Exception as e:
                    raise RuntimeError(f"Stage2: GCS動画ダウンロード失敗 {video_path}: {e}")

        cap = cv2.VideoCapture(local_path)
        if not cap.isOpened():
            raise ValueError(f"動画ファイルを開けません: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        extracted: List[Dict[str, Any]] = []
        ranking_metadata: List[Dict[str, Any]] = []

        for step in stage1_result['work_steps']:
            step_number = step.get('step_number', 0)
            start_seconds = float(step.get('start_seconds', 0.0))
            end_seconds = float(step.get('end_seconds', start_seconds + 5.0))
            ts_list = _candidate_timestamps(start_seconds, end_seconds)

            raw_candidates: List[Dict[str, Any]] = []
            prev_frame_small = None
            for ts in ts_list:
                frame_index = int(ts * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = self.fix_frame_orientation(frame, video_path)
                sharp = _laplacian_sharpness(frame)
                bright = _brightness(frame)
                # 簡易モーション: 前候補とのMSE
                motion_pen = 0.0
                try:
                    small = cv2.resize(frame, (64, 64))
                    if prev_frame_small is not None:
                        diff = cv2.absdiff(prev_frame_small, small)
                        motion_pen = float(np.mean(diff))
                    prev_frame_small = small
                except Exception:
                    pass
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                _, buf = cv2.imencode('.jpg', cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
                b64 = base64.b64encode(buf).decode('utf-8')
                raw_candidates.append({
                    'timestamp_seconds': ts,
                    'timestamp_formatted': f"{int(ts//60):02d}:{int(ts%60):02d}",
                    'frame_number': frame_index,
                    'image_base64': b64,
                    'width': w,
                    'height': h,
                    'sharpness': sharp,
                    'brightness': bright,
                    'motion_penalty': motion_pen,
                })

            if not raw_candidates:
                continue
            # 正規化 & スコア計算
            sharp_norm = _normalize([c['sharpness'] for c in raw_candidates])
            bright_vals = [c['brightness'] for c in raw_candidates]
            bright_norm = _normalize(bright_vals)
            # 目標明度 0.5 からの距離を減点
            scored_candidates = []
            for idx, c in enumerate(raw_candidates):
                score = (
                    0.6 * sharp_norm[idx]
                    + 0.3 * (1 - abs(bright_norm[idx] - 0.5) * 2)  # 中間明るさ優遇
                    + 0.1 * (1 - min(1.0, c['motion_penalty'] / 50.0))
                )
                sc = dict(c)
                sc['heuristic_score'] = score
                scored_candidates.append(sc)

            # Heuristic 上位 3 まで
            scored_candidates.sort(key=lambda x: x['heuristic_score'], reverse=True)
            top_candidates = scored_candidates[:3]

            # Gemini 再ランキング
            sel_index = _gemini_rank({
                'step_number': step_number,
                'step_title': step.get('step_title'),
                'step_description': step.get('step_description','')
            }, top_candidates)
            if sel_index < 0 or sel_index >= len(top_candidates):
                sel_index = 0
            chosen = top_candidates[sel_index]

            extracted.append({
                'step_number': step_number,
                'timestamp_seconds': chosen['timestamp_seconds'],
                'timestamp_formatted': chosen['timestamp_formatted'],
                'frame_number': chosen['frame_number'],
                'image_base64': chosen['image_base64'],
                'image_data_url': f"data:image/jpeg;base64,{chosen['image_base64']}",
                'step_title': step.get('step_title', f'ステップ {step_number}'),
                'step_description': step.get('step_description', ''),
                'width': chosen['width'],
                'height': chosen['height'],
                'selection_method': 'gemini_rerank',
                # (2) 以降で利用: 初期回転角（ユーザー編集用 / 0,90,180,270 のみ想定）
                'rotation': 0,
            })

            ranking_metadata.append({
                'step_number': step_number,
                'candidates': [
                    {
                        'timestamp': c['timestamp_formatted'],
                        'sharpness': c['sharpness'],
                        'brightness': c['brightness'],
                        'motion_penalty': c['motion_penalty'],
                        'heuristic_score': c['heuristic_score']
                    } for c in top_candidates
                ],
                'selected_index': sel_index
            })

        cap.release()
        result = {
            'stage': 2,
            'timestamp': datetime.now().isoformat(),
            'video_path': video_path,
            'extracted_frames': extracted,
            'total_frames': len(extracted),
            'ranking_metadata': ranking_metadata,
            'stage1_reference': {
                'work_title': stage1_result.get('work_title', ''),
                'work_steps_count': len(stage1_result.get('work_steps', [])),
            },
        }
        logger.info(f"2段階完了: {len(extracted)}フレーム確定 (再ランキング適用)")
        return result

    # ---------- Stage 2 (hybrid minimal extraction) ----------
    def stage_2_extract_representative_frames_hybrid(self, video_path: str, stage1_result: Dict[str, Any]) -> Dict[str, Any]:
        """各ステップ midpoint の1枚のみ抽出する軽量版 (Stage3 互換形式)"""
        logger.info("=== 2段階(hybrid): 最小代表フレーム抽出開始 ===")
        steps = stage1_result.get('work_steps') or []
        if not steps:
            raise ValueError('hybrid Stage2: work_steps が空')
        local_path = video_path
        if video_path.startswith('gs://'):
            cached = _GCS_VIDEO_LOCAL_CACHE.get(video_path)
            if cached and os.path.exists(cached):
                local_path = cached
                logger.debug(f"GCS動画キャッシュ再利用(hybrid Stage2): {video_path} -> {local_path}")
            else:
                try:
                    import tempfile
                    from google.cloud import storage  # type: ignore
                    bucket_name, blob_path = video_path[5:].split('/',1)
                    client = storage.Client(); bucket = client.bucket(bucket_name); blob = bucket.blob(blob_path)
                    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(blob_path)[1] or '.mp4'); os.close(fd)
                    blob.download_to_filename(tmp_path)
                    _GCS_VIDEO_LOCAL_CACHE[video_path] = tmp_path
                    local_path = tmp_path
                    logger.info(f"GCS動画ダウンロード(hybrid Stage2): {video_path} -> {tmp_path}")
                except Exception as e:
                    raise RuntimeError(f"hybrid Stage2: GCS動画ダウンロード失敗 {video_path}: {e}")
        cap = cv2.VideoCapture(local_path)
        if not cap.isOpened():
            raise RuntimeError('hybrid Stage2: 動画オープン失敗')
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        extracted: List[Dict[str, Any]] = []
        for step in steps:
            ss = float(step.get('start_seconds',0.0))
            es = float(step.get('end_seconds', ss+2.0))
            mid = ss + (es-ss)*0.5
            frame_index = int(mid*fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = self.fix_frame_orientation(frame, video_path)
            h, w = frame.shape[:2]
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY,80])
            b64 = base64.b64encode(buf).decode('utf-8')
            extracted.append({
                'step_number': step.get('step_number'),
                'timestamp_seconds': mid,
                'timestamp_formatted': f"{int(mid//60):02d}:{int(mid%60):02d}",
                'frame_number': frame_index,
                'image_base64': b64,
                'image_data_url': f"data:image/jpeg;base64,{b64}",
                'step_title': step.get('step_title'),
                'step_description': step.get('step_description',''),
                'width': w,
                'height': h,
                'selection_method': 'hybrid_midpoint',
                'rotation': 0,
            })
        cap.release()
    # cleanup はキャッシュ化戦略のため行わない
        result = {
            'stage':2,
            'mode':'hybrid_minimal',
            'video_path': video_path,
            'extracted_frames': extracted,
            'total_frames': len(extracted),
            'ranking_metadata': [],
            'stage1_reference': {
                'work_title': stage1_result.get('work_title',''),
                'work_steps_count': len(steps)
            }
        }
        logger.info(f"2段階(hybrid) 完了: {len(extracted)}枚")
        return result

    # ---------- Hybrid pipeline convenience ----------
    def run_hybrid_pipeline(self, video_path: str, custom_prompt: Dict[str, Any] | None = None) -> Dict[str, Any]:
        s1 = self.stage_1_analyze_work_steps_text_only(video_path, custom_prompt)
        s2 = self.stage_2_extract_representative_frames_hybrid(video_path, s1)
        return {'stage1': s1, 'stage2': s2}

    # ---------- Stage 3: HTML 生成（二分割レイアウト） ----------
    def stage_3_generate_html_manual(self, stage1_result: Dict[str, Any], stage2_result: Dict[str, Any], custom_prompt: Dict[str, Any] | None = None) -> str:
        logger.info("=== マニュアル（画像あり）生成: HTMLマニュアル生成開始 ===")
        work_title = stage1_result.get('work_title', '動画マニュアル')
        work_steps = stage1_result.get('work_steps', [])
        frames_by_step = {f['step_number']: f for f in stage2_result.get('extracted_frames', [])}
        output_detail = (custom_prompt or {}).get('output_detail', 'titles_only')

        html = []
        html.append("<!DOCTYPE html>\n<html lang=\"ja\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>")
        html.append(self._escape(work_title))
        html.append(" - 作業マニュアル</title>\n</head>\n<body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Hiragino Sans', Meiryo, sans-serif; line-height:1.6; margin:0; padding:16px; background:#ffffff; color:#222;\">\n  <div style=\"max-width:1200px; margin:0 auto;\">\n    <div style=\"padding:12px 0 20px;\">\n      <h1 style=\"margin:0 0 8px; font-size:22px; color:#0d47a1;\">")
        html.append(self._escape(work_title))
        html.append("</h1>\n      <div style=\"font-size:13px; color:#555;\">種類: ")
        html.append(self._escape(stage1_result.get('work_type', '一般作業')))
        html.append(" ／ 難易度: ")
        html.append(self._escape(stage1_result.get('difficulty_level', '中級')))
        html.append(" ／ 予想時間: ")
        html.append(self._escape(str(stage1_result.get('estimated_duration', '30'))))
        html.append("分 ／ ステップ数: ")
        html.append(str(len(work_steps)))
        # 先に 工具・材料 セクションを配置
        html.append("</div>\n    </div>\n")
        if stage1_result.get('required_tools') or stage1_result.get('materials'):
            html.append("    <div style=\"margin:0 0 16px; display:flex; gap:12px; flex-wrap:wrap;\">\n")
            if stage1_result.get('required_tools'):
                html.append("      <div style=\"flex:1 1 360px; min-width:280px; border:1px solid #e5e7eb; border-radius:8px; padding:12px;\">\n        <div style=\"font-weight:600; color:#222; margin-bottom:6px;\">🔧 必要な工具</div>\n        <ul style=\"margin:0; padding-left:18px;\">\n")
                for tool in stage1_result.get('required_tools', []):
                    html.append("          <li>")
                    html.append(self._escape(tool))
                    html.append("</li>\n")
                html.append("        </ul>\n      </div>\n")
            if stage1_result.get('materials'):
                html.append("      <div style=\"flex:1 1 360px; min-width:280px; border:1px solid #e5e7eb; border-radius:8px; padding:12px;\">\n        <div style=\"font-weight:600; color:#222; margin-bottom:6px;\">📦 使用材料</div>\n        <ul style=\"margin:0; padding-left:18px;\">\n")
                for material in stage1_result.get('materials', []):
                    html.append("          <li>")
                    html.append(self._escape(material))
                    html.append("</li>\n")
                html.append("        </ul>\n      </div>\n")
            html.append("    </div>\n")
        # 作業手順+画像の二分割レイアウト
        html.append("    <div style=\"display:flex; gap:16px; align-items:flex-start; flex-wrap:wrap;\">\n      <div style=\"flex:1 1 200px; min-width:200px; border:1px solid #e5e7eb; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);\">\n        <h2 style=\"margin:0 0 12px; font-size:18px; color:#222; border-left:4px solid #1565c0; padding-left:10px;\">作業手順</h2>\n        <ol style=\"margin:0; padding-left:20px;\">\n")

        for step in work_steps:
            n = step.get('step_number', 1)
            title = step.get('step_title', f'ステップ {n}')
            desc = step.get('step_description', '')
            key_actions = step.get('key_actions', [])
            important = step.get('important_points', [])
            safety = step.get('safety_notes', '')

            html.append("          <li style=\"margin:0 0 10px;\">\n            <div style=\"font-weight:600; color:#222;\">ステップ ")
            html.append(str(n))
            html.append(": ")
            html.append(self._escape(title))
            html.append("</div>\n")

            if output_detail == 'titles_with_descriptions' and desc:
                html.append("            <div style=\"margin:4px 0 0; color:#555;\">")
                html.append(self._escape(desc))
                html.append("</div>\n")

            if output_detail == 'titles_with_descriptions' and key_actions:
                html.append("            <ul style=\"margin:6px 0 0 16px; padding:0; list-style: disc; color:#333;\">\n")
                for act in key_actions:
                    html.append("              <li style=\"margin:2px 0;\">")
                    html.append(self._escape(act))
                    html.append("</li>\n")
                html.append("            </ul>\n")

            if output_detail == 'titles_with_descriptions' and important:
                html.append("            <ul style=\"margin:6px 0 0 16px; padding:0; list-style: circle; color:#333;\">\n")
                for p in important:
                    html.append("              <li style=\"margin:2px 0;\">")
                    html.append(self._escape(p))
                    html.append("</li>\n")
                html.append("            </ul>\n")

            if output_detail == 'titles_with_descriptions' and safety:
                html.append("            <div style=\"margin-top:6px; padding:8px; background:#fff8e1; border:1px solid #ffe0b2; border-radius:6px;\">⚠️ ")
                html.append(self._escape(safety))
                html.append("</div>\n")

            html.append("          </li>\n")

        html.append("        </ol>\n      </div>\n")

        # 右カラム
        html.append("      <div style=\"flex:1 1 200px; min-width:200px; display:flex; flex-direction:row; gap:10px; flex-wrap:wrap;\">\n")
        for step in work_steps:
            n = step.get('step_number', 1)
            title = step.get('step_title', f'ステップ {n}')
            f = frames_by_step.get(n)
            if f:
                caption = f"ステップ {n}: {title}"
                ts = f.get('timestamp_formatted', '')
                # 画像は既に物理的に回転されているため、CSS回転は不要
                html.append(f"        <figure data-step=\"{n}\" style=\"margin:0; padding:10px; border:1px solid #e5e7eb; border-radius:8px; background:#fafafa; box-shadow:0 1px 3px rgba(0,0,0,0.04);\">\n          <img data-step=\"{n}\" src=\"")
                html.append(f['image_data_url'])
                html.append("\" alt=\"")
                html.append(self._escape(caption))
                html.append(f"\" style=\"width:100%; height:auto; display:block; border-radius:6px;\">\n          <figcaption style=\"font-size:13px; color:#333; margin-top:6px;\">")
                html.append(self._escape(caption))
                html.append("<span style=\"color:#666; margin-left:8px;\">")
                html.append(self._escape(ts))
                html.append("</span></figcaption>\n        </figure>\n")
            else:
                html.append(f"        <div data-step=\"{n}\" style=\"padding:16px; border:1px dashed #ccc; border-radius:8px; color:#777; text-align:center;\">ステップ ")
                html.append(str(n))
                html.append(" の画像は利用できません</div>\n")
        html.append("</div>\n</div>\n\n</div>\n</body>\n</html>\n")

        result = ''.join(html)
        logger.info("マニュアル（画像あり）生成完了: HTMLマニュアル生成")
        return result

    # ---------- Utils ----------
    @staticmethod
    def _escape(s: Any) -> str:
        x = str(s)
        return (
            x.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    # ---------- Convenience: マニュアル（画像あり）生成一括実行（同期用エンドポイント向け） ----------
    def generate_manual_with_images(self, video_path: str, custom_prompt: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """マニュアル（画像あり）生成を順次実行し、集約結果を返す。主に同期エンドポイント用。"""
        logger.info("=== マニュアル（画像あり）生成処理開始（同期） ===")
        try:
            stage1 = self.stage_1_analyze_work_steps(video_path, custom_prompt)
            stage2 = self.stage_2_extract_representative_frames(video_path, stage1)
            html = self.stage_3_generate_html_manual(stage1, stage2, custom_prompt)
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "video_path": video_path,
                "stage1_result": stage1,
                "stage2_result": stage2,
                "html_manual": html,
                "summary": {
                    "work_title": stage1.get('work_title', ''),
                    "total_steps": len(stage1.get('work_steps', [])),
                    "extracted_frames": len(stage2.get('extracted_frames', [])),
                    "html_length": len(html),
                },
            }
        except Exception as e:
            logger.error(f"マニュアル（画像あり）生成処理エラー（同期）: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "video_path": video_path,
            }

