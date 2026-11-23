import json
import os
import shutil
import subprocess
import sys

from mage_ai.settings.repo import get_repo_path

from lab_project.utils.etl_log import utcnow, write_log

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

DBT_TIMEOUT_SECONDS = 1800


def _dbt_command(*args: str) -> list:
    dbt_dir = os.path.join(get_repo_path(), 'dbt', 'hotel_dw')
    binary = shutil.which('dbt')
    base = [binary] if binary else [sys.executable, '-m', 'dbt.cli.main']
    return base + list(args) + ['--profiles-dir', dbt_dir, '--project-dir', dbt_dir]


def _run_dbt(*args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(_dbt_command(*args), capture_output=True, text=True, timeout=DBT_TIMEOUT_SECONDS)
    tail = '\n'.join((proc.stdout or '').strip().splitlines()[-25:])
    print(f'[dbt {args[0]}] exit={proc.returncode}\n{tail}')
    if proc.stderr.strip():
        print(f'[dbt {args[0]}] stderr: {proc.stderr.strip()[-800:]}')
    return proc


def _read_results() -> list:
    results_file = os.path.join(get_repo_path(), 'dbt', 'hotel_dw', 'target', 'run_results.json')
    with open(results_file, encoding='utf-8') as f:
        return json.load(f).get('results', [])


def _count(results: list, prefix: str, ok_statuses: tuple) -> tuple:
    items = [r for r in results if str(r.get('unique_id', '')).startswith(prefix)]
    ok = [r for r in items if r.get('status') in ok_statuses]
    bad = [r.get('unique_id', '?').split('.')[-2] if prefix == 'test.' else r.get('unique_id', '?')
           for r in items if r.get('status') not in ok_statuses]
    return len(items), len(ok), bad


@custom
def run_dbt_build(summary: dict, **kwargs) -> dict:
    """
    Block 4 (Custom): chạy dbt run rồi dbt test để cập nhật dds ngay sau khi nạp stage thành công.

    Ghi KẾT QUẢ vào control.etl_batch_log với pipeline_name = 'hotel_dbt_build', load_mode = 'DBT':
      rows_extracted = tổng số dbt test | rows_valid = số test PASS | rows_rejected = số test FAIL/ERROR
      status: SUCCESS (mọi test pass) | WARNING (dds đã build nhưng có test fail) | FAILED (dbt run lỗi => dừng pipeline)
    Nếu block trước không nạp dòng nào (AUTO không có batch mới) thì bỏ qua dbt.
    """
    rows_loaded = int((summary or {}).get('rows_loaded', 0))
    batch_file = str((summary or {}).get('batch_file', 'unknown'))
    if rows_loaded == 0:
        print('[run_dbt_build] Stage không có dữ liệu mới, bỏ qua dbt.')
        return {'dbt_status': 'SKIPPED', 'batch_file': batch_file}

    started = utcnow()

    # 1. dbt run: dựng staging view + 5 dim + fact_bookings
    run_proc = _run_dbt('run')
    try:
        models_total, models_ok, models_bad = _count(_read_results(), 'model.', ('success',))
    except FileNotFoundError:
        models_total, models_ok, models_bad = 0, 0, ['(không đọc được run_results.json)']
    if run_proc.returncode != 0 or models_bad:
        message = f'dbt run lỗi: {models_ok}/{models_total} model OK; lỗi: {models_bad}'
        if models_total == 0:  # dbt không chạy được (sai cấu hình / kết nối) => đính kèm đoạn cuối log để dễ tìm nguyên nhân
            message += ' | ' + ((run_proc.stderr or run_proc.stdout or '').strip()[-300:])
        write_log(batch_file, 'DBT', 0, 0, 0, 'FAILED', message, started, pipeline_name='hotel_dbt_build')
        raise RuntimeError(message)

    # 2. dbt test: 43 test chất lượng dữ liệu trên dds
    test_proc = _run_dbt('test')
    try:
        tests_total, tests_ok, tests_bad = _count(_read_results(), 'test.', ('pass',))
    except FileNotFoundError:
        tests_total, tests_ok, tests_bad = 0, 0, ['(không đọc được run_results.json)']
    if tests_total == 0 and test_proc.returncode != 0:
        message = 'dbt test không chạy được (không có kết quả test).'
        write_log(batch_file, 'DBT', 0, 0, 0, 'FAILED', message, started, pipeline_name='hotel_dbt_build')
        raise RuntimeError(message)

    failed = tests_total - tests_ok
    status = 'SUCCESS' if failed == 0 else 'WARNING'
    message = f'dbt run: {models_ok}/{models_total} model OK | dbt test: {tests_ok}/{tests_total} PASS'
    if failed:
        message += f' | FAIL: {", ".join(tests_bad)[:600]}'
    write_log(batch_file, 'DBT', tests_total, tests_ok, failed, status, message, started,
              pipeline_name='hotel_dbt_build')
    print(f'[run_dbt_build] {message} => {status}')
    return {'dbt_status': status, 'batch_file': batch_file, 'tests_total': tests_total, 'tests_failed': failed}


@test
def test_output(output, *args) -> None:
    assert output is not None, 'Output không được None'
    assert output.get('dbt_status') in ('SUCCESS', 'WARNING', 'SKIPPED'), 'Trạng thái dbt không hợp lệ'
