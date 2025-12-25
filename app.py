import os
import random
import pandas as pd
from flask import Flask, request, render_template, send_file, jsonify
import io
import datetime

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_file', methods=['POST'])
def analyze_file():
    file = request.files.get('file')
    if not file: return jsonify({"error": "未找到文件"}), 400
    try:
        # 1. 获取所有 Sheet 名称
        xl = pd.ExcelFile(file)
        sheets = xl.sheet_names
        
        # 2. 默认读取第一个 Sheet 的结构
        df = xl.parse(sheets[0], nrows=10)
        columns = df.columns.tolist()
        
        return jsonify({
            "sheets": sheets,
            "columns": columns
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_sheet_info', methods=['POST'])
def get_sheet_info():
    """切换 Sheet 时重新获取列和单位"""
    file = request.files.get('file')
    sheet_name = request.form.get('sheet_name')
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        columns = df.columns.tolist()
        units = []
        unit_col = next((c for c in columns if '单位' in str(c)), None)
        if unit_col:
            units = df[unit_col].dropna().unique().tolist()
        return jsonify({
            "columns": columns,
            "units": [str(u) for u in units]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    file = request.files.get('file')
    sheet_name = request.form.get('sheet_name')
    target_qty_col = request.form.get('target_qty_col') # 用户选定的数量基准列
    total_days = int(request.form.get('days', 12))
    selected_cols = request.form.getlist('cols')[:10]
    int_units = request.form.getlist('int_units')
    
    try:
        df = pd.read_excel(file, sheet_name=sheet_name)
        
        # 自动定位其他辅助列
        name_col = next((c for c in df.columns if '名称' in str(c)), selected_cols[0])
        unit_col = next((c for c in df.columns if '单位' in str(c)), None)
        price_col = next((c for c in df.columns if '单价' in str(c)), None)

        # 清洗指定数量列
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
                # 使用用户指定的基准列更新拆分后的值
                if target_qty_col in new_row: new_row[target_qty_col] = splits[i]
                
                # 如果用户选了含税金额且单价列存在，自动重算
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
