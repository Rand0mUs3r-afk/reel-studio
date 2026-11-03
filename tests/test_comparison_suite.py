import json
from pathlib import Path
from comparison_suite import attempt,write_report

def test_failed_case_does_not_stop_other_cases():
    results=[]
    def fail():raise ValueError('secret URL should not be copied')
    attempt(results,'bad','bad',fail,'review')
    attempt(results,'good','good',lambda:None,'review')
    assert [r['status'] for r in results]==['failed','completed']
    assert results[0]['error_type']=='ValueError'
    assert 'secret' not in json.dumps(results)

def test_report_escapes_text_and_marks_missing_modes(tmp_path):
    results=[{'name':'<script>','folder':'01-intact','status':'skipped','warning':'No approved paid backend'}]
    document=write_report(tmp_path,results,True)
    assert document['paid_api_calls'] is False
    assert document['publishing']=='disabled'
    page=(tmp_path/'comparison.html').read_text()
    assert '&lt;script&gt;' in page and '<script>' not in page
    assert json.loads((tmp_path/'comparison.json').read_text())['preview_only'] is True
