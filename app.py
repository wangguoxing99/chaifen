import os
import random
import pandas as pd
from flask import Flask, request, render_template, send_file, jsonify, session, redirect, url_for
import io
import datetime
from functools import wraps

app = Flask(__name__)
# 设置 Session 密钥，生产环境建议通过环境变量设置
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "secret_key_for_session")

# 从环境变量获取用户名密码，默认值为 admin/admin123
AUTH_USER = os.environ.get("APP_USER", "admin")
AUTH_PWD = os.environ.get("APP_PASSWORD", "admin123")

# 登录限制装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def split_smart(total_qty, days, is_int):
    if days <= 1: return [total_qty]
    amounts = []
    if is_int:
        total_int = int(total_qty)
        if total_int < days: return [1] * total_int
        base = total_int // days
        remainder = total_int % days
        amounts = [base] * days
        indices = list(range(days))
        random.shuffle(indices)
        for i in range(remainder): amounts[indices[i]] += 1
    else:
        weights = [random.uniform(0.8, 1.2) for _ in range(days)]
        sum_weights = sum(weights)
        current_sum = 0
        for w in weights[:-1]:
            val = round((w / sum_weights) * total_qty, 1)
            if val == 0 and total_qty > 1: val = 0.1
            amounts.append(val)
            current_sum += val
        amounts.append(round(total_qty - current_sum, 1))
    return amounts

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == AUTH_USER and pwd == AUTH_PWD:
            session["logged_in"] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', user=AUTH_USER)

@app.route('/analyze_file', methods=['POST'])
@login_required
def analyze_file():
    file = request.files.get('file')
    if not file: return jsonify({"error": "未找到文件"}), 400
    try:
        xl = pd.ExcelFile(file)
        sheets = xl.sheet_names
        df = xl.parse(sheets[0], nrows=10)
        return jsonify({"sheets": sheets, "columns": df.columns.tolist()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_sheet_info', methods=['POST'])
@login_required
def get_sheet_info():
    file = request.files.get('file')
    sheet_name = request.form.get('sheet_name')
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        columns = df.columns.tolist()
        units = []
        unit_col = next((c for c in columns if '单位' in str(c)), None)
        if unit_col:
            units = df[unit_col].dropna().unique().tolist()
        return jsonify({"columns": columns, "units": [str(u) for u in units]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
@login_required
def process():
    # ... (保持之前 process 内部逻辑不变) ...
    file = request.files.get('file')
    sheet_name = request.form.get('sheet_name')
    target_qty_col = request.form.get('target_qty_col')
    total_days = int(request.form.get('days', 12))
    selected_cols = request.form.getlist('cols')[:10]
    int_units = request.form.getlist('int_units')
    
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        name_col = next((c for c in df.columns if '名称' in str(c)), selected_cols[0])
        unit_col = next((c for c in df.columns if '单位' in str(c)), None)
        price_col = next((c for c in df.columns if '单价' in str(c)), None)
        df = df.dropna(subset=[name_col, target_qty_col])
        df[target_qty_col] = pd.to_numeric(df[target_qty_col], errors='coerce')
        df = df[df[target_qty_col] > 0]
        daily_rows = [[] for _ in range(total_days)]
        for _, row in df.iterrows():
            unit = str(row.get(unit_col, '')) if unit_col else ""
            qty = row[target_qty_col]
            if qty <= 3: active_days = 1
            elif qty <= 10: active_days = random.randint(2, min(4, total_days))
            else: active_days = random.randint(3, min(total_days, 10))
            is_int = unit in int_units
            splits = split_smart(qty, active_days, is_int)
            days_indices = sorted(random.sample(range(total_days), len(splits)))
            for i, day_idx in enumerate(days_indices):
                new_row = {col: row[col] for col in selected_cols if col in row}
                if target_qty_col in new_row: new_row[target_qty_col] = splits[i]
                if price_col in row and '含税金额' in selected_cols:
                    new_row['含税金额'] = round(float(row[price_col]) * splits[i], 2)
                daily_rows[day_idx].append(new_row)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i in range(total_days):
                pd.DataFrame(daily_rows[i]).to_excel(writer, sheet_name=f'第{i+1}天', index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"拆分_{sheet_name}.xlsx")
    except Exception as e:
        return f"发生错误: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
