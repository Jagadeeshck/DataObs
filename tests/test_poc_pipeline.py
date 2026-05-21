from pathlib import Path
from src.poc.scenarios.road_safety.generator import generate_scaled
from src.poc.scenarios.road_safety.pipeline import run_road_safety_scenario
from src.poc.spark_metrics import metric_doc


def test_generator_small(tmp_path: Path):
    out = generate_scaled(Path('fixtures/poc/road_safety'), tmp_path, scale='small')
    assert out['accidents'].exists()
    assert out['vehicles'].exists()


def test_good_run_quality_summary(tmp_path: Path):
    generate_scaled(Path('fixtures/poc/road_safety'), tmp_path, scale='small')
    res = run_road_safety_scenario(tmp_path, 'RUN1', run_mode='good')
    assert 'dataobs-rs-accident-facts' in res['outputs']
    assert all(q['status'] in {'pass','warn','fail'} for q in res['quality'])


def test_bad_run_injection(tmp_path: Path):
    generate_scaled(Path('fixtures/poc/road_safety'), tmp_path, scale='small')
    res = run_road_safety_scenario(tmp_path, 'RUN2', run_mode='bad')
    assert any(q['status'] == 'fail' for q in res['quality'])


def test_spark_metric_shape():
    doc = metric_doc('R','stage',100,90)
    for k in ['run_id','stage_name','stage_duration_seconds','input_rows','output_rows','status','error_count']:
        assert k in doc
