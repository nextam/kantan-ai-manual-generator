import os
import json
from pathlib import Path

from app import app, db, Company

"""companies.storage_config の credentials_path (GOOGLE_APPLICATION_CREDENTIALS) を絶対パスへ正規化するスクリプト。

実行: python -m scripts.fix_storage_config
"""

def resolve_credentials_path(value: str) -> str:
    if not value:
        return value
    raw = value.strip().strip('"').strip("'")
    if os.path.isabs(raw):
        return raw
    # 探索候補: manual_generator/, ルート/
    manual_dir = Path(__file__).resolve().parent.parent
    repo_root = manual_dir.parent
    for cand in [manual_dir / raw, repo_root / raw]:
        if cand.is_file():
            return str(cand.resolve())
    # 見つからない場合は元値
    return value

def main():
    updated = 0
    with app.app_context():
        companies = Company.query.all()
        for c in companies:
            cfg = {}
            if c.storage_config:
                try:
                    cfg = json.loads(c.storage_config)
                except Exception:
                    pass
            cred = cfg.get('credentials_path') or cfg.get('GOOGLE_APPLICATION_CREDENTIALS')
            if cred:
                resolved = resolve_credentials_path(cred)
                if resolved != cred:
                    # 統一キーとして credentials_path を利用
                    cfg['credentials_path'] = resolved
                    c.storage_config = json.dumps(cfg, ensure_ascii=False)
                    updated += 1
        if updated:
            db.session.commit()
    print(f"Updated companies: {updated}")

if __name__ == '__main__':
    main()
