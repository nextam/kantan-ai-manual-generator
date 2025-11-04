# 基本的な認証ルート（認証システムがない場合のフォールバック）
@app.route('/auth/status', methods=['GET'])
def auth_status():
    """認証状態取得API"""
    if HAS_AUTH_SYSTEM:
        try:
            return auth_manager.get_auth_status()
        except:
            pass
    
    # フォールバック
    return jsonify({
        'authenticated': False,
        'user': None,
        'company': None
    })

@app.route('/login', methods=['GET'])
def login_page():
    """ログインページ"""
    if HAS_AUTH_SYSTEM:
        return render_template('login.html')
    else:
        # 認証システムがない場合はマニュアル一覧にリダイレクト
        return redirect(url_for('manual_list'))
