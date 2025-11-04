"""
作業手順マニュアルPDF生成モジュール
ReportLabを使用してA4サイズのマニュアルPDFを生成
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import logging

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import black, red, blue, HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

logger = logging.getLogger(__name__)

class ManualPDFGenerator:
    """作業手順マニュアルPDF生成クラス"""
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 20 * mm
        self.content_width = self.page_width - 2 * self.margin
        
        # 日本語フォント設定（システムフォント使用）
        self._setup_fonts()
        
        # スタイル設定
        self.styles = self._create_styles()

    def _setup_fonts(self):
        """日本語フォントの設定"""
        try:
            # Windows標準の日本語フォント
            font_paths = [
                "C:/Windows/Fonts/msgothic.ttc",  # MS Gothic
                "C:/Windows/Fonts/msmincho.ttc",  # MS Mincho
                "C:/Windows/Fonts/NotoSansCJK-Regular.ttc"  # Noto Sans CJK (Google Fonts)
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Japanese', font_path))
                        self.japanese_font = 'Japanese'
                        logger.info(f"日本語フォント登録成功: {font_path}")
                        return
                    except Exception:
                        continue
                        
            # フォールバック: Helvetica
            self.japanese_font = 'Helvetica'
            logger.warning("日本語フォントが見つかりません。Helveticaを使用します。")
            
        except Exception as e:
            logger.error(f"フォント設定エラー: {e}")
            self.japanese_font = 'Helvetica'

    def _create_styles(self):
        """スタイル定義"""
        styles = getSampleStyleSheet()
        
        # カスタムスタイル
        styles.add(ParagraphStyle(
            name='JapaneseTitle',
            parent=styles['Title'],
            fontName=self.japanese_font,
            fontSize=18,
            spaceAfter=15,
            alignment=TA_CENTER
        ))
        
        styles.add(ParagraphStyle(
            name='JapaneseHeading',
            parent=styles['Heading2'],
            fontName=self.japanese_font,
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor('#1f4e79')
        ))
        
        styles.add(ParagraphStyle(
            name='JapaneseBody',
            parent=styles['Normal'],
            fontName=self.japanese_font,
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
        
        styles.add(ParagraphStyle(
            name='StepNumber',
            parent=styles['Normal'],
            fontName=self.japanese_font,
            fontSize=12,
            textColor=HexColor('#c5504b'),
            spaceAfter=3
        ))
        
        return styles

    def generate_pdf(self, manual_data: Dict[str, Any], output_path: str) -> bool:
        """
        マニュアルPDFを生成
        
        Args:
            manual_data: マニュアルデータ
            output_path: 出力PDFパス
            
        Returns:
            成功時True
        """
        if not HAS_REPORTLAB:
            logger.error("ReportLabがインストールされていません")
            return False
            
        try:
            # PDFドキュメント作成
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin
            )
            
            # コンテンツ生成
            content = self._build_content(manual_data)
            
            # PDF生成
            doc.build(content)
            logger.info(f"PDF生成完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF生成エラー: {e}")
            return False

    def _build_content(self, manual_data: Dict[str, Any]) -> List:
        """PDFコンテンツを構築"""
        content = []
        analysis = manual_data.get("analysis_result", {})
        
        # タイトルページ
        content.extend(self._create_title_page(analysis))
        
        # 作業手順セクション
        content.extend(self._create_steps_section(analysis))
        
        return content

    def _create_title_page(self, analysis: Dict[str, Any]) -> List:
        """タイトルページ作成"""
        content = []
        
        # メインタイトル
        title = f"{analysis.get('work_type', '作業手順')}マニュアル"
        content.append(Paragraph(title, self.styles['JapaneseTitle']))
        content.append(Spacer(1, 20))
        
        # 概要情報テーブル
        summary_data = [
            ['作業概要', analysis.get('summary', 'N/A')],
            ['難易度', analysis.get('difficulty_level', 'N/A')],
            ['推定作業者数', f"{analysis.get('estimated_workers', 1)}名"],
            ['総作業時間', f"{analysis.get('total_duration', 0):.1f}秒"],
            ['生成日時', datetime.now().strftime('%Y年%m月%d日 %H:%M')]
        ]
        
        summary_table = Table(summary_data, colWidths=[40*mm, 120*mm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.japanese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#f2f2f2')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        content.append(summary_table)
        content.append(Spacer(1, 20))
        
        # 必要工具
        tools = analysis.get('required_tools', [])
        if tools:
            content.append(Paragraph('必要な工具・機材', self.styles['JapaneseHeading']))
            tools_text = '、'.join(tools)
            content.append(Paragraph(tools_text, self.styles['JapaneseBody']))
            content.append(Spacer(1, 15))
        
        content.append(PageBreak())
        return content

    def _create_steps_section(self, analysis: Dict[str, Any]) -> List:
        """作業手順セクション作成"""
        content = []
        steps = analysis.get('steps', [])
        
        content.append(Paragraph('作業手順', self.styles['JapaneseTitle']))
        content.append(Spacer(1, 20))
        
        for step in steps:
            content.extend(self._create_step_content(step))
            content.append(Spacer(1, 15))
        
        return content

    def _create_step_content(self, step: Dict[str, Any]) -> List:
        """個別ステップコンテンツ作成"""
        content = []
        
        # ステップ番号とタイトル
        step_title = f"手順 {step.get('step_number', 1)}: {step.get('title', 'N/A')}"
        content.append(Paragraph(step_title, self.styles['JapaneseHeading']))
        
        # 2カラムレイアウト用テーブル
        table_data = []
        
        # 左カラム: テキスト情報
        left_content = []
        
        # 作業内容
        description = step.get('description', '')
        if description:
            left_content.append(Paragraph('<b>作業内容:</b>', self.styles['JapaneseBody']))
            left_content.append(Paragraph(description, self.styles['JapaneseBody']))
            left_content.append(Spacer(1, 8))
        
        # 重要ポイント
        key_points = step.get('key_points', [])
        if key_points:
            left_content.append(Paragraph('<b>重要ポイント:</b>', self.styles['JapaneseBody']))
            for point in key_points:
                left_content.append(Paragraph(f"• {point}", self.styles['JapaneseBody']))
            left_content.append(Spacer(1, 8))
        
        # 安全注意
        safety_notes = step.get('safety_notes', '')
        if safety_notes:
            left_content.append(Paragraph('<b>安全上の注意:</b>', self.styles['JapaneseBody']))
            left_content.append(Paragraph(safety_notes, self.styles['JapaneseBody']))
        
        # 時間情報
        time_info = f"作業時間: {step.get('timestamp_start', 0):.1f}s ～ {step.get('timestamp_end', 0):.1f}s"
        left_content.append(Spacer(1, 8))
        left_content.append(Paragraph(time_info, self.styles['JapaneseBody']))
        
        # 右カラム: 画像
        right_content = []
        image_path = step.get('image_path')
        if image_path and os.path.exists(image_path):
            try:
                # 画像サイズ調整
                img = Image(image_path, width=70*mm, height=52*mm)
                right_content.append(img)
                right_content.append(Spacer(1, 5))
                right_content.append(Paragraph('↑ 作業画像', self.styles['JapaneseBody']))
            except Exception as e:
                logger.warning(f"画像読み込みエラー: {e}")
                right_content.append(Paragraph('[画像読み込みエラー]', self.styles['JapaneseBody']))
        else:
            right_content.append(Paragraph('[画像なし]', self.styles['JapaneseBody']))
        
        # テーブル作成
        table_data.append([left_content, right_content])
        
        step_table = Table(table_data, colWidths=[100*mm, 80*mm])
        step_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.japanese_font),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e0e0e0')),
        ]))
        
        content.append(step_table)
        return content

    def generate_simple_manual_pdf(self, manual_data: Dict[str, Any], output_path: str) -> bool:
        """
        シンプルなマニュアルPDF生成（フォールバック用）
        
        Args:
            manual_data: マニュアルデータ
            output_path: 出力PDFパス
            
        Returns:
            成功時True
        """
        try:
            from fpdf import FPDF
            
            class ManualPDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 16)
                    self.cell(0, 10, 'Work Manual', 0, 1, 'C')
                    self.ln(10)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            
            pdf = ManualPDF()
            pdf.add_page()
            
            analysis = manual_data.get("analysis_result", {})
            steps = analysis.get('steps', [])
            
            # タイトル
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f"Work Type: {analysis.get('work_type', 'General Work')}", 0, 1)
            pdf.ln(5)
            
            # 手順
            for step in steps:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 8, f"Step {step.get('step_number', 1)}: {step.get('title', 'N/A')}", 0, 1)
                
                pdf.set_font('Arial', '', 10)
                description = step.get('description', '')[:200] + '...' if len(step.get('description', '')) > 200 else step.get('description', '')
                pdf.multi_cell(0, 6, description)
                pdf.ln(3)
            
            pdf.output(output_path)
            logger.info(f"シンプルPDF生成完了: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"シンプルPDF生成エラー: {e}")
            return False
