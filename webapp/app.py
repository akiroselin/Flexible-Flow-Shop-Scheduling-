import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(APP_ROOT, os.pardir))
OUTPUT_FILES = [
    # GA结果文件
    "schedule_results_GA.csv",
    "schedule_kpis_GA.csv",
    "schedule_orders_GA.csv",
    "schedule_gantt_GA.html",
    # NSGA-II结果文件
    "schedule_results_NSGA2.csv",
    "schedule_kpis_NSGA2.csv",
    "schedule_orders_NSGA2.csv",
    "schedule_gantt_NSGA2.html",
]

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'
app.config['UPLOAD_FOLDER'] = REPO_ROOT


@app.route('/')
def index():
    # 切换到基于React+Babel的新版UI
    return render_template('ffs.html')


@app.route('/model')
def model():
    return render_template('model.html')


@app.route('/input', methods=['GET', 'POST'])
def input_page():
    if request.method == 'POST':
        mapping = {
            'process_times': '工序加工时间.csv',
            'orders': '订单数据.csv',
            'equipment': '设备可用时间.csv',
        }
        saved = []
        for field, filename in mapping.items():
            file = request.files.get(field)
            if file and file.filename:
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                saved.append(filename)
        if saved:
            flash(f"已上传文件: {', '.join(saved)}", "success")
        else:
            flash("未选择文件或上传失败", "warning")
        return redirect(url_for('input_page'))
    return render_template('input.html')


@app.route('/run', methods=['POST'])
def run_schedule():
    try:
        # 触发后端排程脚本
        result = subprocess.run(
            ["uv", "run", "python", "run_ga.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        flash("排程运行完成。", "success")
        return redirect(url_for('result'))
    except subprocess.CalledProcessError as e:
        err = e.stderr or e.stdout
        flash(f"排程运行失败: {err[:500]}", "danger")
        return redirect(url_for('index'))


@app.route('/result')
def result():
    existing = [f for f in OUTPUT_FILES if os.path.exists(os.path.join(REPO_ROOT, f))]
    return render_template('result.html', files=existing)


@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(REPO_ROOT, filename, as_attachment=True)


@app.route('/gantt')
def gantt():
    # 内嵌甘特图（如果存在）
    gantt_path = os.path.join(REPO_ROOT, 'schedule_gantt_GA.html')
    if os.path.exists(gantt_path):
        return send_from_directory(REPO_ROOT, 'schedule_gantt_GA.html')
    flash("尚未生成甘特图，请先运行排程。", "warning")
    return redirect(url_for('index'))

@app.route('/gantt_nsga2')
def gantt_nsga2():
    # 内嵌 NSGA-II 甘特图（如果存在）
    gantt_path = os.path.join(REPO_ROOT, 'schedule_gantt_NSGA2.html')
    if os.path.exists(gantt_path):
        return send_from_directory(REPO_ROOT, 'schedule_gantt_NSGA2.html')
    flash("尚未生成 NSGA-II 甘特图，请先运行排程（NSGA-II）。", "warning")
    return redirect(url_for('index'))

def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None

def _parse_kpis_csv(path):
    import csv
    kpis = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('指标')
                val = row.get('数值')
                try:
                    num = float(val)
                except Exception:
                    num = None
                if name == '总加权拖期':
                    kpis['total_weighted_tardiness'] = num
                elif name == '订单准时交付率':
                    kpis['on_time_delivery_rate'] = num
                elif name == '平均拖期':
                    kpis['avg_tardiness'] = num
                elif name == 'Makespan':
                    kpis['makespan_days'] = num
                elif name == '设备平均利用率':
                    kpis['avg_utilization'] = num
                elif name and '负载均衡度' in name:
                    kpis['load_balance_std'] = num
    except Exception:
        pass
    return kpis

def _parse_orders_csv(path):
    import csv
    orders = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    orders.append({
                        'order_id': row.get('订单ID'),
                        'completion_days': float(row.get('完工时间(天)')) if row.get('完工时间(天)') else None,
                        'due_date': float(row.get('交货期(天)')) if row.get('交货期(天)') else None,
                        'tardiness': float(row.get('拖期(天)')) if row.get('拖期(天)') else None,
                        'on_time': (row.get('是否准时') or '').strip() in ('是', 'Yes', 'TRUE', 'True'),
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return orders

@app.route('/api/results', methods=['GET'])
def api_results():
    # 汇总当前已存在的结果文件列表及下载链接（两种算法）
    existing = []
    for f in OUTPUT_FILES:
        full = os.path.join(REPO_ROOT, f)
        if os.path.exists(full):
            existing.append({
                'name': f,
                'download_url': url_for('download', filename=f)
            })

    # GA结果
    ga = {}
    ga_kpis = os.path.join(REPO_ROOT, 'schedule_kpis_GA.csv')
    ga_orders = os.path.join(REPO_ROOT, 'schedule_orders_GA.csv')
    ga_gantt = os.path.join(REPO_ROOT, 'schedule_gantt_GA.html')
    ga_results = os.path.join(REPO_ROOT, 'schedule_results_GA.csv')
    if os.path.exists(ga_kpis):
        ga['kpis'] = _parse_kpis_csv(ga_kpis)
    if os.path.exists(ga_orders):
        ga['orders'] = _parse_orders_csv(ga_orders)
    if os.path.exists(ga_gantt):
        ga['gantt_url'] = url_for('download', filename='schedule_gantt_GA.html')
    if os.path.exists(ga_results):
        ga['schedule_csv_url'] = url_for('download', filename='schedule_results_GA.csv')

    # NSGA-II结果
    ns = {}
    ns_kpis = os.path.join(REPO_ROOT, 'schedule_kpis_NSGA2.csv')
    ns_orders = os.path.join(REPO_ROOT, 'schedule_orders_NSGA2.csv')
    ns_gantt = os.path.join(REPO_ROOT, 'schedule_gantt_NSGA2.html')
    ns_results = os.path.join(REPO_ROOT, 'schedule_results_NSGA2.csv')
    if os.path.exists(ns_kpis):
        ns['kpis'] = _parse_kpis_csv(ns_kpis)
    if os.path.exists(ns_orders):
        ns['orders'] = _parse_orders_csv(ns_orders)
    if os.path.exists(ns_gantt):
        ns['gantt_url'] = url_for('download', filename='schedule_gantt_NSGA2.html')
    if os.path.exists(ns_results):
        ns['schedule_csv_url'] = url_for('download', filename='schedule_results_NSGA2.csv')

    return jsonify({
        'files': existing,
        'ga': ga,
        'nsga2': ns,
    })

@app.route('/api/schedule', methods=['POST'])
def api_schedule():
    # 保存上传文件
    mapping = {
        'process_times': '工序加工时间.csv',
        'orders': '订单数据.csv',
        'machines': '设备可用时间.csv',
    }
    for field, filename in mapping.items():
        file = request.files.get(field)
        if file and file.filename:
            file.save(os.path.join(REPO_ROOT, filename))

    # 运行GA
    try:
        subprocess.run([
            'uv', 'run', 'python', 'run_ga.py'
        ], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr or e.stdout
        return jsonify({'error': err[:500]}), 500

    # 读取结果
    kpis = _parse_kpis_csv(os.path.join(REPO_ROOT, 'schedule_kpis_GA.csv'))
    orders = _parse_orders_csv(os.path.join(REPO_ROOT, 'schedule_orders_GA.csv'))
    gantt_html = _read_text(os.path.join(REPO_ROOT, 'schedule_gantt_GA.html'))
    schedule_csv = _read_text(os.path.join(REPO_ROOT, 'schedule_results_GA.csv'))

    return jsonify({
        'kpis': kpis,
        'orders': orders,
        'gantt_html': gantt_html,
        'schedule_csv': schedule_csv,
        'algorithm': 'GA',
    })

@app.route('/api/schedule_nsga2', methods=['POST'])
def api_schedule_nsga2():
    # 保存上传文件（与GA相同映射）
    mapping = {
        'process_times': '工序加工时间.csv',
        'orders': '订单数据.csv',
        'machines': '设备可用时间.csv',
    }
    for field, filename in mapping.items():
        file = request.files.get(field)
        if file and file.filename:
            file.save(os.path.join(REPO_ROOT, filename))

    # 运行NSGA-II
    try:
        subprocess.run([
            'uv', 'run', 'python', 'run_nsga2.py'
        ], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr or e.stdout
        return jsonify({'error': err[:500]}), 500

    # 读取NSGA-II结果
    kpis = _parse_kpis_csv(os.path.join(REPO_ROOT, 'schedule_kpis_NSGA2.csv'))
    orders = _parse_orders_csv(os.path.join(REPO_ROOT, 'schedule_orders_NSGA2.csv'))
    gantt_html = _read_text(os.path.join(REPO_ROOT, 'schedule_gantt_NSGA2.html'))
    schedule_csv = _read_text(os.path.join(REPO_ROOT, 'schedule_results_NSGA2.csv'))

    return jsonify({
        'kpis': kpis,
        'orders': orders,
        'gantt_html': gantt_html,
        'schedule_csv': schedule_csv,
        'algorithm': 'NSGA2',
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8003))
    app.run(host='0.0.0.0', port=port, debug=True)