"""
データベース初期化・管理スクリプト
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# パスの設定
sys.path.append(str(Path(__file__).parent))

from flask import Flask
from src.models.models import db, Company, User, UploadedFile, Manual
from src.middleware.auth import CompanyManager

def create_app():
    """Flaskアプリケーション作成"""
    app = Flask(__name__)
    
    # 設定
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    # Use DATABASE_URL from environment (PostgreSQL for development/production)
    # Falls back to SQLite only if DATABASE_URL is not set
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/manual_generator.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # データベース初期化
    db.init_app(app)
    
    return app

def init_database():
    """データベース初期化"""
    app = create_app()
    
    with app.app_context():
        print("データベースを初期化しています...")
        
        # テーブル作成
        db.create_all()
        print("✓ データベーステーブルが作成されました")
        
        # サンプル企業作成
        if not Company.query.first():
            print("サンプル企業を作成しています...")
            
            # デモ企業1
            result1 = CompanyManager.create_company(
                name="サンプル製造業株式会社",
                company_code="sample001",
                password="password123",
                admin_username="admin",
                admin_email="admin@sample001.com"
            )
            
            if result1['success']:
                print("✓ デモ企業1が作成されました:")
                print(f"  - 企業名: サンプル製造業株式会社")
                print(f"  - 企業コード: sample001")
                print(f"  - パスワード: password123")
                print(f"  - 管理者: admin")
            
            # デモ企業2
            result2 = CompanyManager.create_company(
                name="テスト工業有限会社",
                company_code="test002",
                password="test123456",
                admin_username="admin",
                admin_email="admin@test002.com"
            )
            
            if result2['success']:
                print("✓ デモ企業2が作成されました:")
                print(f"  - 企業名: テスト工業有限会社")
                print(f"  - 企業コード: test002")
                print(f"  - パスワード: test123456")
                print(f"  - 管理者: admin")
        
        print("データベース初期化が完了しました!")

def reset_database():
    """データベースリセット"""
    app = create_app()
    
    with app.app_context():
        print("データベースをリセットしています...")
        
        # 全テーブル削除
        db.drop_all()
        print("✓ 既存テーブルが削除されました")
        
        # 再作成
        db.create_all()
        print("✓ テーブルが再作成されました")
        
        print("データベースリセットが完了しました!")

def show_companies():
    """企業一覧表示"""
    app = create_app()
    
    with app.app_context():
        companies = Company.query.all()
        
        if not companies:
            print("登録されている企業はありません")
            return
        
        print("登録企業一覧:")
        print("-" * 60)
        
        for company in companies:
            users_count = User.query.filter_by(company_id=company.id).count()
            files_count = UploadedFile.query.filter_by(company_id=company.id).count()
            manuals_count = Manual.query.filter_by(company_id=company.id).count()
            
            print(f"企業名: {company.name}")
            print(f"企業コード: {company.company_code}")
            print(f"作成日: {company.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"ユーザー数: {users_count}")
            print(f"ファイル数: {files_count}")
            print(f"マニュアル数: {manuals_count}")
            print(f"ストレージ: {company.storage_type}")
            print(f"状態: {'アクティブ' if company.is_active else '無効'}")
            print("-" * 60)

def create_company_interactive():
    """対話式企業作成"""
    app = create_app()
    
    with app.app_context():
        print("新規企業作成")
        print("-" * 30)
        
        company_name = input("企業名: ")
        company_code = input("企業コード: ")
        password = input("パスワード: ")
        admin_username = input("管理者ユーザー名 (デフォルト: admin): ") or "admin"
        admin_email = input("管理者メールアドレス (任意): ") or None
        
        result = CompanyManager.create_company(
            name=company_name,
            company_code=company_code,
            password=password,
            admin_username=admin_username,
            admin_email=admin_email
        )
        
        if result['success']:
            print("\n✓ 企業が正常に作成されました!")
            print(f"企業ID: {result['company'].id}")
        else:
            print(f"\n✗ エラー: {result['error']}")

def backup_database():
    """データベースバックアップ"""
    app = create_app()
    
    db_path = Path("manual_generator.db")
    if not db_path.exists():
        print("データベースファイルが見つかりません")
        return
    
    # バックアップファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = Path(f"manual_generator_backup_{timestamp}.db")
    
    # ファイルコピー
    import shutil
    shutil.copy2(db_path, backup_path)
    
    print(f"✓ データベースをバックアップしました: {backup_path}")

def restore_database(backup_file):
    """データベース復元"""
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        print(f"バックアップファイルが見つかりません: {backup_file}")
        return
    
    db_path = Path("manual_generator.db")
    
    # 既存データベースのバックアップ
    if db_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup = Path(f"manual_generator_before_restore_{timestamp}.db")
        import shutil
        shutil.copy2(db_path, current_backup)
        print(f"✓ 現在のデータベースをバックアップしました: {current_backup}")
    
    # 復元
    import shutil
    shutil.copy2(backup_path, db_path)
    print(f"✓ データベースを復元しました: {backup_file}")

def clean_old_files():
    """古いファイルの清掃"""
    app = create_app()
    
    with app.app_context():
        # アップロードディレクトリのチェック
        uploads_dir = Path("uploads")
        if not uploads_dir.exists():
            print("アップロードディレクトリが見つかりません")
            return
        
        # データベース上のファイル一覧取得
        db_files = set()
        for uploaded_file in UploadedFile.query.all():
            db_files.add(uploaded_file.file_path)
        
        # 物理ファイル一覧取得
        physical_files = set()
        for file_path in uploads_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(uploads_dir)
                physical_files.add(str(rel_path))
        
        # 孤立ファイル検出
        orphaned_files = physical_files - db_files
        
        if orphaned_files:
            print(f"孤立ファイルが {len(orphaned_files)} 件見つかりました:")
            for file in orphaned_files:
                print(f"  - {file}")
            
            if input("これらのファイルを削除しますか？ (y/N): ").lower() == 'y':
                for file in orphaned_files:
                    file_path = uploads_dir / file
                    file_path.unlink()
                    print(f"✓ 削除: {file}")
        else:
            print("孤立ファイルはありません")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual Generator データベース管理")
    parser.add_argument("command", choices=[
        "init", "reset", "list", "create", "backup", "restore", "clean"
    ], help="実行コマンド")
    parser.add_argument("--backup-file", help="復元するバックアップファイル")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_database()
    elif args.command == "reset":
        if input("データベースをリセットしますか？ (y/N): ").lower() == 'y':
            reset_database()
        else:
            print("キャンセルされました")
    elif args.command == "list":
        show_companies()
    elif args.command == "create":
        create_company_interactive()
    elif args.command == "backup":
        backup_database()
    elif args.command == "restore":
        if args.backup_file:
            restore_database(args.backup_file)
        else:
            print("--backup-file オプションが必要です")
    elif args.command == "clean":
        clean_old_files()
