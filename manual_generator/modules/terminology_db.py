"""
製造業専門用語データベース管理モジュール
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TerminologyDatabase:
    """製造業専門用語データベース管理クラス"""
    
    def __init__(self, db_path: str = "data/terminology.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースの初期化
        self._initialize_database()
        
        logger.info(f"用語データベースを初期化しました: {self.db_path}")
    
    def _initialize_database(self):
        """データベーステーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用語テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE NOT NULL,
                    definition TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    difficulty_level INTEGER DEFAULT 1,
                    usage_frequency INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 関連文書テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS term_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term_id INTEGER,
                    document_name TEXT NOT NULL,
                    document_type TEXT,
                    page_number INTEGER,
                    context TEXT,
                    FOREIGN KEY (term_id) REFERENCES terms (id)
                )
            ''')
            
            # 同義語テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS term_synonyms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term_id INTEGER,
                    synonym TEXT NOT NULL,
                    FOREIGN KEY (term_id) REFERENCES terms (id)
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term)')
            
            conn.commit()
            
            # 初期データの投入
            self._insert_initial_data(cursor)
    
    def _insert_initial_data(self, cursor):
        """初期データの投入"""
        initial_terms = [
            # 機械加工関連
            ("圧入", "部品を圧力により嵌合させる組立方法", "機械加工", "組立", 2),
            ("切削", "工具により材料を削り取る加工方法", "機械加工", "除去加工", 1),
            ("研削", "砥石により材料表面を研磨する精密加工", "機械加工", "仕上げ加工", 3),
            ("旋盤", "工作物を回転させて切削加工を行う工作機械", "機械加工", "工作機械", 2),
            ("フライス盤", "回転する切削工具で平面や溝を加工する機械", "機械加工", "工作機械", 2),
            
            # 溶接関連
            ("アーク溶接", "電気アークの熱を利用した溶接方法", "溶接", "電気溶接", 2),
            ("TIG溶接", "タングステン電極を使用した不活性ガス溶接", "溶接", "電気溶接", 3),
            ("溶接棒", "アーク溶接で使用する消耗電極", "溶接", "材料", 1),
            ("溶接ビード", "溶接により形成された溶着金属の隆起部", "溶接", "品質", 2),
            
            # 測定・検査関連
            ("マイクロメータ", "精密な外径測定器具", "測定", "寸法測定", 2),
            ("ノギス", "長さや径を測定する器具", "測定", "寸法測定", 1),
            ("ゲージ", "規定寸法を確認するための基準器具", "測定", "検査", 1),
            ("公差", "許容される寸法の変動範囲", "測定", "品質管理", 2),
            ("真直度", "直線からのずれの程度を示す幾何公差", "測定", "幾何公差", 3),
            
            # 安全関連
            ("KYT", "危険予知訓練の略称", "安全管理", "予防活動", 1),
            ("LOTO", "ロックアウト・タグアウトの安全手順", "安全管理", "電気安全", 2),
            ("PPE", "個人用保護具（Personal Protective Equipment）", "安全管理", "保護具", 1),
            ("ヒヤリハット", "事故に至らなかった危険な事例", "安全管理", "予防活動", 1),
            
            # 品質管理関連
            ("QC", "品質管理（Quality Control）", "品質管理", "管理手法", 1),
            ("QA", "品質保証（Quality Assurance）", "品質管理", "管理手法", 2),
            ("トレーサビリティ", "製品の履歴を追跡できる状態", "品質管理", "管理手法", 2),
            ("不適合", "規定要求事項を満たしていない状態", "品質管理", "不良管理", 2),
            ("是正処置", "不適合の原因を除去する処置", "品質管理", "改善活動", 2),
            
            # 生産管理関連
            ("JIT", "ジャストインタイム生産方式", "生産管理", "生産方式", 2),
            ("5S", "整理・整頓・清掃・清潔・躾の活動", "生産管理", "改善活動", 1),
            ("カンバン", "生産指示や在庫管理に使用する札", "生産管理", "管理ツール", 2),
            ("タクトタイム", "1個の製品を生産するのに許される時間", "生産管理", "時間管理", 2),
            
            # 材料関連
            ("SS400", "一般構造用圧延鋼材の規格", "材料", "鋼材", 2),
            ("SUS304", "オーステナイト系ステンレス鋼の規格", "材料", "ステンレス", 2),
            ("アルミ合金", "アルミニウムを主成分とする合金", "材料", "軽金属", 1),
            ("硬度", "材料の硬さを表す物性値", "材料", "機械的性質", 2),
        ]
        
        for term, definition, category, subcategory, difficulty in initial_terms:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO terms 
                    (term, definition, category, subcategory, difficulty_level)
                    VALUES (?, ?, ?, ?, ?)
                ''', (term, definition, category, subcategory, difficulty))
            except sqlite3.IntegrityError:
                # 既に存在する場合はスキップ
                pass
    
    def add_term(
        self, 
        term: str, 
        definition: str, 
        category: str, 
        subcategory: Optional[str] = None,
        difficulty_level: int = 1,
        synonyms: Optional[List[str]] = None,
        related_documents: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        新しい用語を追加
        
        Args:
            term: 用語
            definition: 定義
            category: カテゴリ
            subcategory: サブカテゴリ
            difficulty_level: 難易度（1-5）
            synonyms: 同義語リスト
            related_documents: 関連文書情報
            
        Returns:
            追加された用語のID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用語を追加
            cursor.execute('''
                INSERT OR REPLACE INTO terms 
                (term, definition, category, subcategory, difficulty_level)
                VALUES (?, ?, ?, ?, ?)
            ''', (term, definition, category, subcategory, difficulty_level))
            
            term_id = cursor.lastrowid
            
            # 同義語を追加
            if synonyms:
                for synonym in synonyms:
                    cursor.execute('''
                        INSERT OR IGNORE INTO term_synonyms (term_id, synonym)
                        VALUES (?, ?)
                    ''', (term_id, synonym))
            
            # 関連文書を追加
            if related_documents:
                for doc in related_documents:
                    cursor.execute('''
                        INSERT INTO term_documents 
                        (term_id, document_name, document_type, page_number, context)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        term_id,
                        doc.get('name'),
                        doc.get('type'),
                        doc.get('page'),
                        doc.get('context')
                    ))
            
            conn.commit()
            logger.info(f"用語を追加しました: {term}")
            return term_id
    
    def search_terms(
        self, 
        query: str, 
        category: Optional[str] = None,
        difficulty_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        用語検索
        
        Args:
            query: 検索クエリ
            category: カテゴリフィルター
            difficulty_level: 難易度フィルター
            
        Returns:
            検索結果のリスト
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ベースクエリ
            sql = '''
                SELECT t.*, 
                       GROUP_CONCAT(DISTINCT s.synonym) as synonyms,
                       GROUP_CONCAT(DISTINCT d.document_name) as documents
                FROM terms t
                LEFT JOIN term_synonyms s ON t.id = s.term_id
                LEFT JOIN term_documents d ON t.id = d.term_id
                WHERE (t.term LIKE ? OR t.definition LIKE ? OR s.synonym LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%', f'%{query}%']
            
            # フィルター条件追加
            if category:
                sql += ' AND t.category = ?'
                params.append(category)
            
            if difficulty_level:
                sql += ' AND t.difficulty_level = ?'
                params.append(difficulty_level)
            
            sql += ' GROUP BY t.id ORDER BY t.usage_frequency DESC, t.term'
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 結果を辞書形式に変換
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in rows:
                term_dict = dict(zip(columns, row))
                # 同義語と文書をリストに変換
                term_dict['synonyms'] = term_dict['synonyms'].split(',') if term_dict['synonyms'] else []
                term_dict['documents'] = term_dict['documents'].split(',') if term_dict['documents'] else []
                results.append(term_dict)
            
            return results
    
    def get_term_by_id(self, term_id: int) -> Optional[Dict[str, Any]]:
        """
        IDで用語を取得
        
        Args:
            term_id: 用語ID
            
        Returns:
            用語情報の辞書
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.*, 
                       GROUP_CONCAT(DISTINCT s.synonym) as synonyms,
                       GROUP_CONCAT(DISTINCT d.document_name) as documents
                FROM terms t
                LEFT JOIN term_synonyms s ON t.id = s.term_id
                LEFT JOIN term_documents d ON t.id = d.term_id
                WHERE t.id = ?
                GROUP BY t.id
            ''', (term_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [description[0] for description in cursor.description]
            term_dict = dict(zip(columns, row))
            term_dict['synonyms'] = term_dict['synonyms'].split(',') if term_dict['synonyms'] else []
            term_dict['documents'] = term_dict['documents'].split(',') if term_dict['documents'] else []
            
            return term_dict
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """
        すべてのカテゴリを取得
        
        Returns:
            カテゴリ情報のリスト
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT category, subcategory, COUNT(*) as term_count
                FROM terms
                GROUP BY category, subcategory
                ORDER BY category, subcategory
            ''')
            
            rows = cursor.fetchall()
            categories = {}
            
            for category, subcategory, count in rows:
                if category not in categories:
                    categories[category] = {'subcategories': {}, 'total_count': 0}
                
                categories[category]['subcategories'][subcategory] = count
                categories[category]['total_count'] += count
            
            return categories
    
    def update_usage_frequency(self, term: str):
        """
        用語の使用頻度を更新
        
        Args:
            term: 用語
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE terms 
                SET usage_frequency = usage_frequency + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE term = ?
            ''', (term,))
            
            conn.commit()
    
    def extract_terms_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        テキストから既知の用語を抽出
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            見つかった用語のリスト
        """
        found_terms = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 全用語を取得
            cursor.execute('SELECT term, definition, category, difficulty_level FROM terms')
            all_terms = cursor.fetchall()
            
            # 同義語も取得
            cursor.execute('''
                SELECT s.synonym, t.term, t.definition, t.category, t.difficulty_level
                FROM term_synonyms s
                JOIN terms t ON s.term_id = t.id
            ''')
            synonyms = cursor.fetchall()
        
        # テキスト内での用語検索
        text_lower = text.lower()
        
        # 正式用語の検索
        for term, definition, category, difficulty in all_terms:
            if term.lower() in text_lower:
                found_terms.append({
                    'term': term,
                    'definition': definition,
                    'category': category,
                    'difficulty_level': difficulty,
                    'found_as': term
                })
                # 使用頻度を更新
                self.update_usage_frequency(term)
        
        # 同義語の検索
        for synonym, original_term, definition, category, difficulty in synonyms:
            if synonym.lower() in text_lower:
                found_terms.append({
                    'term': original_term,
                    'definition': definition,
                    'category': category,
                    'difficulty_level': difficulty,
                    'found_as': synonym
                })
                # 使用頻度を更新
                self.update_usage_frequency(original_term)
        
        # 重複除去
        unique_terms = []
        seen_terms = set()
        
        for term_info in found_terms:
            if term_info['term'] not in seen_terms:
                unique_terms.append(term_info)
                seen_terms.add(term_info['term'])
        
        return unique_terms
    
    def export_terms_to_json(self, output_path: str):
        """
        用語データをJSONファイルにエクスポート
        
        Args:
            output_path: 出力ファイルパス
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.*, 
                       GROUP_CONCAT(DISTINCT s.synonym) as synonyms,
                       GROUP_CONCAT(DISTINCT d.document_name) as documents
                FROM terms t
                LEFT JOIN term_synonyms s ON t.id = s.term_id
                LEFT JOIN term_documents d ON t.id = d.term_id
                GROUP BY t.id
                ORDER BY t.category, t.term
            ''')
            
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            terms_data = []
            for row in rows:
                term_dict = dict(zip(columns, row))
                term_dict['synonyms'] = term_dict['synonyms'].split(',') if term_dict['synonyms'] else []
                term_dict['documents'] = term_dict['documents'].split(',') if term_dict['documents'] else []
                terms_data.append(term_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(terms_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"用語データをエクスポートしました: {output_path}")
    
    def import_terms_from_json(self, input_path: str):
        """
        JSONファイルから用語データをインポート
        
        Args:
            input_path: 入力ファイルパス
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            terms_data = json.load(f)
        
        for term_data in terms_data:
            self.add_term(
                term=term_data['term'],
                definition=term_data['definition'],
                category=term_data['category'],
                subcategory=term_data.get('subcategory'),
                difficulty_level=term_data.get('difficulty_level', 1),
                synonyms=term_data.get('synonyms', [])
            )
        
        logger.info(f"用語データをインポートしました: {input_path} ({len(terms_data)}件)")

# テスト実行用のメイン関数
if __name__ == "__main__":
    # 用語データベースのテスト
    db = TerminologyDatabase()
    
    # 検索テスト
    results = db.search_terms("溶接")
    print(f"「溶接」の検索結果: {len(results)}件")
    for result in results[:3]:
        print(f"  - {result['term']}: {result['definition']}")
    
    # カテゴリ一覧
    categories = db.get_categories()
    print(f"\nカテゴリ一覧: {len(categories)}カテゴリ")
    for cat, info in categories.items():
        print(f"  - {cat}: {info['total_count']}用語")
    
    # テキストから用語抽出
    sample_text = "アーク溶接による圧入作業では、適切なPPEの着用とKYTの実施が重要です。"
    found_terms = db.extract_terms_from_text(sample_text)
    print(f"\nテキストから抽出された用語: {len(found_terms)}件")
    for term in found_terms:
        print(f"  - {term['term']} (発見形式: {term['found_as']})")
