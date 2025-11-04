#!/usr/bin/env python3
"""
統合マイグレーションスクリプト
app.py から呼び出し可能な安全なマイグレーション実行関数
"""

import sqlite3
import os
import logging
from pathlib import Path

def run_migrations(db_path, logger=None):
    """
    データベースマイグレーションを安全に実行
    
    Args:
        db_path (str): データベースファイルのパス
        logger: ロガーオブジェクト（任意）
    
    Returns:
        bool: マイグレーション成功可否
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if not os.path.exists(db_path):
        logger.info(f"データベースファイルが存在しません: {db_path}")
        return False
    
    try:
        # マイグレーション前にバックアップを作成（安全性向上）
        backup_path = f"{db_path}.backup_before_migration"
        if not os.path.exists(backup_path):  # 既存バックアップがない場合のみ
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"📋 マイグレーション前バックアップ作成: {backup_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のテーブル構造を確認
        cursor.execute("PRAGMA table_info(manuals)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"既存のカラム: {columns}")
        
        migrations_applied = 0
        
        # Migration 1: description カラムの追加
        if 'description' not in columns:
            logger.info("Migration 1: description カラムを追加中...")
            cursor.execute("ALTER TABLE manuals ADD COLUMN description TEXT")
            migrations_applied += 1
            logger.info("ADD: description カラムが追加されました")
        else:
            logger.info("OK: description カラムは既に存在します")
        
        # Migration 2: 画像あり マニュアル関連フィールドの追加
        stage_fields = [
            ('stage1_content', 'TEXT'),
            ('stage2_content', 'TEXT'), 
            ('stage3_content', 'TEXT'),
            ('generation_status', "TEXT DEFAULT 'completed'"),
            ('generation_progress', "INTEGER DEFAULT 100"),
            ('error_message', 'TEXT'),
            ('generation_config', 'TEXT')
        ]
        
        # 最新のカラム状況を再取得
        cursor.execute("PRAGMA table_info(manuals)")
        current_columns = [column[1] for column in cursor.fetchall()]
        
        for field_name, field_type in stage_fields:
            if field_name not in current_columns:
                logger.info(f"Migration 2: {field_name} カラムを追加中...")
                cursor.execute(f"ALTER TABLE manuals ADD COLUMN {field_name} {field_type}")
                migrations_applied += 1
                logger.info(f"ADD: {field_name} カラムが追加されました")
            else:
                logger.info(f"OK: {field_name} カラムは既に存在します")
        
        # 変更をコミット
        if migrations_applied > 0:
            conn.commit()
            logger.info(f"DONE: {migrations_applied}個のマイグレーションが適用されました")
        else:
            logger.info("INFO: 適用すべきマイグレーションはありません（最新状態）")
        
        # 最終的なテーブル構造を確認
        cursor.execute("PRAGMA table_info(manuals)")
        final_columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"マイグレーション後のカラム: {final_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"マイグレーション実行エラー: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    """スタンドアロン実行用（テスト目的）"""
    import sys
    
    # ログ設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # データベースパスの決定
    if os.path.exists('/app'):
        # コンテナ環境
        db_path = '/app/instance/manual_generator.db'
    else:
        # ローカル環境
        db_path = os.path.join('instance', 'manual_generator.db')
    
    logger.info(f"=== 統合マイグレーション開始 ===")
    logger.info(f"データベースパス: {db_path}")
    
    success = run_migrations(db_path, logger)
    
    if success:
        logger.info("✅ マイグレーション完了")
        sys.exit(0)
    else:
        logger.error("❌ マイグレーション失敗")
        sys.exit(1)
