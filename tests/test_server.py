# nhanes-assistant-plugin/tests/test_server.py
"""
Unit tests for NHANES Plugin v2 MCP server.
Run from nhanes-assistant-plugin/: pytest tests/test_server.py -v
"""
import os
import sys
import subprocess
import zipfile
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhanes_server'))
import server


def _mock_r(returncode=0, stdout='ok', stderr=''):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


class TestSearchNhanesVariables:
    def test_returns_stdout_on_success(self):
        with patch('subprocess.run', return_value=_mock_r(stdout='DR1_030Z Eating Occasion')):
            assert 'DR1_030Z' in server.search_nhanes_variables('eating occasion')

    def test_returns_error_on_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='pkg error')):
            result = server.search_nhanes_variables('x')
        assert 'failed' in result.lower() or 'pkg error' in result

    def test_returns_timeout_message(self):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['Rscript'], 600)):
            assert 'timed out' in server.search_nhanes_variables('x').lower()


class TestExecuteRScript:
    def test_saves_script_and_returns_path(self):
        with patch('subprocess.run', return_value=_mock_r(stdout='hello')):
            result = server.execute_r_script('cat("hello")')
        assert 'Script saved to:' in result
        assert 'hello' in result

    def test_returns_stderr_on_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='object not found')):
            result = server.execute_r_script('bad()')
        assert 'object not found' in result

    def test_timeout_includes_saved_path(self):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['Rscript'], 600)):
            result = server.execute_r_script('Sys.sleep(9999)')
        assert 'Script saved to:' in result
        assert 'timed out' in result.lower()


class TestWriteCsvOutputs:
    def test_writes_file_to_csv_dir(self):
        result = server.write_csv_outputs('a,b\n1,2\n', 'unit_test.csv')
        assert 'CSV written to:' in result
        written_path = result.replace('CSV written to: ', '').strip()
        assert os.path.exists(written_path)
        with open(written_path) as f:
            assert 'a,b' in f.read()
        os.remove(written_path)

    def test_appends_csv_extension_if_missing(self):
        result = server.write_csv_outputs('x\n', 'noext_unit_test')
        written_path = result.replace('CSV written to: ', '').strip()
        assert written_path.endswith('.csv')
        if os.path.exists(written_path):
            os.remove(written_path)


class TestLookupNhanesCodebook:
    def test_returns_stdout_on_success(self):
        with patch('subprocess.run', return_value=_mock_r(stdout='SEQN Respondent...')):
            assert 'SEQN' in server.lookup_nhanes_codebook('DEMO', 'J')

    def test_returns_error_on_timeout(self):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['Rscript'], 120)):
            assert 'timed out' in server.lookup_nhanes_codebook('DEMO', 'J').lower()

    def test_rejects_injection_characters(self):
        result = server.lookup_nhanes_codebook('DEMO"; system("rm -rf /")', 'J')
        assert 'Invalid' in result


class TestResources:
    def test_nhanes_expertise_mentions_covid_exclusion(self):
        assert 'COVID' in server.get_nhanes_expertise()

    def test_nhanes_expertise_mentions_weight_variables(self):
        content = server.get_nhanes_expertise()
        assert 'WTDRD1' in content and 'WTMEC2YR' in content

    def test_reporting_conventions_decimal_rule(self):
        assert '2 decimal' in server.get_reporting_conventions()

    def test_html_style_has_arial(self):
        assert 'Arial' in server.get_html_style()

    def test_nhanes_styles_resource_has_theme_function(self):
        content = server.get_nhanes_styles()
        assert 'theme_nhanes' in content and 'nhanes_flextable_style' in content


class TestRenderHtmlFigure:
    def test_returns_figure_fragment_on_success(self, tmp_path):
        def fake_run(cmd, **kwargs):
            # Find SVG path from the generated R script and create a fake SVG
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    with open(arg) as f:
                        src = f.read()
                    import re
                    m = re.search(r'svglite\("([^"]+)"', src)
                    if m:
                        with open(m.group(1), 'w') as sf:
                            sf.write('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
            return MagicMock(returncode=0, stdout='SVG written', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            result = server.render_html_figure('p <- ggplot2::ggplot()', 'My Title', 'My Caption')
        assert '<figure' in result
        assert 'My Title' in result
        assert 'My Caption' in result
        assert '<svg' in result

    def test_returns_error_string_on_r_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='ggplot error')):
            result = server.render_html_figure('p <- bad()', 'T', 'C')
        assert 'failed' in result.lower()

    def _capture_script(self, blank_axes):
        captured = {}
        def fake_run(cmd, **kwargs):
            import re
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    with open(arg) as f:
                        captured['src'] = f.read()
                    m = re.search(r'svglite\("([^"]+)"', captured['src'])
                    if m:
                        with open(m.group(1), 'w') as sf:
                            sf.write('<svg/>')
            return MagicMock(returncode=0, stdout='', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            server.render_html_figure('p <- ggplot2::ggplot()', 'T', 'C', blank_axes=blank_axes)
        return captured['src']

    def test_blank_axes_appends_void_theme_after_theme_nhanes(self):
        src = self._capture_script(blank_axes=True)
        assert 'axis.line = ggplot2::element_blank()' in src
        # must come AFTER theme_nhanes() or the theme would override it
        assert src.index('theme_nhanes()') < src.index('axis.line = ggplot2::element_blank()')

    def test_no_blank_axes_by_default(self):
        src = self._capture_script(blank_axes=False)
        assert 'axis.line = ggplot2::element_blank()' not in src


class TestRenderHtmlTable:
    def test_returns_table_fragment_on_success(self):
        fake_html = '<table><tr><th>A</th></tr></table>'
        with patch('subprocess.run', return_value=_mock_r(stdout=fake_html)):
            result = server.render_html_table('tbl <- gt::gt(data.frame(a=1))', 'Table 1', 'Notes')
        assert 'Table 1' in result
        assert 'Notes' in result
        assert '<table' in result

    def test_returns_error_on_r_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='gt error')):
            result = server.render_html_table('tbl <- bad()', 'T', 'N')
        assert 'failed' in result.lower()


class TestWriteHtmlOutput:
    def test_creates_standalone_html_file(self):
        result = server.write_html_output('<p>Hello</p>', 'unit_test_output.html')
        assert result.endswith('.html')
        assert os.path.exists(result)
        with open(result) as f:
            content = f.read()
        assert '<!DOCTYPE html>' in content
        assert 'Arial' in content
        assert '<p>Hello</p>' in content
        os.remove(result)


class TestRenderManuscriptFigure:
    def test_returns_png_path_on_success(self, tmp_path):
        def fake_run(cmd, **kwargs):
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    with open(arg) as f:
                        src = f.read()
                    import re
                    m = re.search(r'agg_png\("([^"]+)"', src)
                    if m:
                        # Create a 1x1 white PNG (minimal valid PNG)
                        import struct, zlib
                        def mk_png():
                            sig = b'\x89PNG\r\n\x1a\n'
                            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
                            ihdr_chunk = b'IHDR' + ihdr
                            ihdr_crc = zlib.crc32(ihdr_chunk) & 0xffffffff
                            idat_data = zlib.compress(b'\x00\xff\xff\xff')
                            idat_chunk = b'IDAT' + idat_data
                            idat_crc = zlib.crc32(idat_chunk) & 0xffffffff
                            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
                            return (sig
                                + struct.pack('>I', len(ihdr)) + ihdr_chunk + struct.pack('>I', ihdr_crc)
                                + struct.pack('>I', len(idat_data)) + idat_chunk + struct.pack('>I', idat_crc)
                                + struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc))
                        with open(m.group(1), 'wb') as pf:
                            pf.write(mk_png())
            return MagicMock(returncode=0, stdout='PNG written', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            result = server.render_manuscript_figure('p <- ggplot2::ggplot()', 'Fig', 'Cap', 2)
        assert result.endswith('.png')
        assert 'fig2_' in os.path.basename(result)

    def test_returns_error_on_r_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='ragg error')):
            result = server.render_manuscript_figure('p <- bad()', 'T', 'C', 1)
        assert 'failed' in result.lower()


class TestRenderManuscriptTable:
    def test_returns_rds_path_on_success(self, tmp_path):
        def fake_run(cmd, **kwargs):
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    with open(arg) as f:
                        src = f.read()
                    import re
                    m = re.search(r'saveRDS\(ft, "([^"]+)"', src)
                    if m:
                        with open(m.group(1), 'w') as rf:
                            rf.write('fake_rds')
            return MagicMock(returncode=0, stdout='Table RDS saved', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            result = server.render_manuscript_table('ft <- flextable::flextable(data.frame(a=1))', 'T', 'N', 1)
        assert result.endswith('.rds')
        assert 'tbl1_' in os.path.basename(result)

    def test_returns_error_on_r_failure(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='flextable error')):
            result = server.render_manuscript_table('ft <- bad()', 'T', 'N', 1)
        assert 'failed' in result.lower()


class TestWriteDocxOutput:
    def test_returns_docx_path_on_success(self):
        def fake_run(cmd, **kwargs):
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    with open(arg) as f:
                        src = f.read()
                    import re
                    m = re.search(r'"output_path"\s*:\s*"([^"]+)"', src)
                    if not m:
                        # Try reading the json file referenced in the script
                        jm = re.search(r'fromJSON\("([^"]+)"', src)
                        if jm and os.path.exists(jm.group(1)):
                            import json as _json
                            with open(jm.group(1)) as jf:
                                data = _json.load(jf)
                            op = data.get('output_path', '')
                            if op:
                                with open(op, 'w') as df:
                                    df.write('fake docx')
            return MagicMock(returncode=0, stdout='DOCX saved', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            result = server.write_docx_output(
                title='Test', abstract='Abs', methods='Meth', results='Res',
                limitations='Lim', ethics_statement='Ethics', data_availability='Data',
                figure_paths=[], table_rds_paths=[]
            )
        assert result.endswith('.docx')
        assert 'manuscript_' in os.path.basename(result)

    def test_authors_defaults_to_empty_string(self):
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='err')):
            result = server.write_docx_output(
                'T', 'A', 'M', 'R', 'L', 'E', 'D', [], []
            )
        # Even on failure, it should not raise; authors kwarg is optional
        assert isinstance(result, str)

    def test_legends_passed_to_handoff(self):
        captured = {}
        def fake_run(cmd, **kwargs):
            import re, json as _json
            for arg in cmd:
                if arg.endswith('.R') and os.path.exists(arg):
                    src = open(arg).read()
                    m = re.search(r'fromJSON\("([^"]+)"', src)
                    if m and os.path.exists(m.group(1)):
                        data = _json.load(open(m.group(1)))
                        captured.update(data)
                        op = data.get('output_path', '')
                        if op:
                            open(op, 'w').write('x')
            return MagicMock(returncode=0, stdout='ok', stderr='')
        with patch('subprocess.run', side_effect=fake_run):
            server.write_docx_output(
                'T', 'A', 'M', 'R', 'L', 'E', 'D', [], [],
                figure_legends=['Fig 1 legend'], table_legends=['Tab 1 legend'])
        assert captured.get('figure_legends') == ['Fig 1 legend']
        assert captured.get('table_legends') == ['Tab 1 legend']

    def test_legends_default_empty(self):
        # Backward compatibility: omitting legends must still work (defaults to []).
        with patch('subprocess.run', return_value=_mock_r(returncode=1, stderr='err')):
            result = server.write_docx_output('T', 'A', 'M', 'R', 'L', 'E', 'D', [], [])
        assert isinstance(result, str)


class TestMissingRscript:
    """FIX 1: OSError (e.g. FileNotFoundError) when Rscript is absent."""

    def test_execute_r_script_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.execute_r_script('cat("hello")')
        assert 'could not run Rscript' in result
        assert 'PATH' in result or 'setup.sh' in result

    def test_search_nhanes_variables_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.search_nhanes_variables('sugar')
        assert 'could not run Rscript' in result

    def test_lookup_nhanes_codebook_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.lookup_nhanes_codebook('DEMO', 'J')
        assert 'could not run Rscript' in result

    def test_render_html_figure_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.render_html_figure('p <- ggplot2::ggplot()', 'T', 'C')
        assert 'could not run Rscript' in result

    def test_render_html_table_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.render_html_table('tbl <- gt::gt(data.frame(a=1))', 'T', 'N')
        assert 'could not run Rscript' in result

    def test_render_manuscript_figure_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.render_manuscript_figure('p <- ggplot2::ggplot()', 'T', 'C', 1)
        assert 'could not run Rscript' in result

    def test_render_manuscript_table_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.render_manuscript_table('ft <- flextable::flextable(data.frame(a=1))', 'T', 'N', 1)
        assert 'could not run Rscript' in result

    def test_write_docx_output_missing_rscript(self):
        with patch('subprocess.run', side_effect=FileNotFoundError("No such file: Rscript")):
            result = server.write_docx_output('T', 'A', 'M', 'R', 'L', 'E', 'D', [], [])
        assert 'could not run Rscript' in result


class TestCreateReproducibilityBundle:
    def test_returns_message_when_no_outputs(self, tmp_path):
        # Point dirs at empty tmp dirs
        import server as srv
        orig_docx = srv.DOCX_DIR
        orig_scripts = srv.ANALYSIS_SCRIPTS_DIR
        orig_csv = srv.CSV_DIR
        orig_html = srv.HTML_DIR
        orig_bundles = srv.BUNDLES_DIR
        try:
            srv.DOCX_DIR = str(tmp_path / 'docx'); os.makedirs(srv.DOCX_DIR)
            srv.ANALYSIS_SCRIPTS_DIR = str(tmp_path / 'scripts'); os.makedirs(srv.ANALYSIS_SCRIPTS_DIR)
            srv.CSV_DIR = str(tmp_path / 'csv'); os.makedirs(srv.CSV_DIR)
            srv.HTML_DIR = str(tmp_path / 'html'); os.makedirs(srv.HTML_DIR)
            srv.BUNDLES_DIR = str(tmp_path / 'bundles'); os.makedirs(srv.BUNDLES_DIR)
            result = srv.create_reproducibility_bundle()
        finally:
            srv.DOCX_DIR = orig_docx
            srv.ANALYSIS_SCRIPTS_DIR = orig_scripts
            srv.CSV_DIR = orig_csv
            srv.HTML_DIR = orig_html
            srv.BUNDLES_DIR = orig_bundles
        assert 'No output files' in result

    def test_session_timestamp_filters_files(self, tmp_path):
        """FIX 6: session_timestamp restricts scripts/csv/html to matching filenames."""
        import server as srv
        orig_docx = srv.DOCX_DIR
        orig_scripts = srv.ANALYSIS_SCRIPTS_DIR
        orig_csv = srv.CSV_DIR
        orig_html = srv.HTML_DIR
        orig_bundles = srv.BUNDLES_DIR
        try:
            srv.DOCX_DIR = str(tmp_path / 'docx'); os.makedirs(srv.DOCX_DIR)
            srv.ANALYSIS_SCRIPTS_DIR = str(tmp_path / 'scripts'); os.makedirs(srv.ANALYSIS_SCRIPTS_DIR)
            srv.CSV_DIR = str(tmp_path / 'csv'); os.makedirs(srv.CSV_DIR)
            srv.HTML_DIR = str(tmp_path / 'html'); os.makedirs(srv.HTML_DIR)
            srv.BUNDLES_DIR = str(tmp_path / 'bundles'); os.makedirs(srv.BUNDLES_DIR)

            session_ts = "20240101_120000"
            stale_ts   = "20230101_090000"

            # Create session files and stale files
            for ext, d in [('.R', srv.ANALYSIS_SCRIPTS_DIR), ('.csv', srv.CSV_DIR), ('.html', srv.HTML_DIR)]:
                open(os.path.join(d, f"analysis_{session_ts}{ext}"), 'w').close()
                open(os.path.join(d, f"analysis_{stale_ts}{ext}"), 'w').close()

            result = srv.create_reproducibility_bundle(session_timestamp=session_ts)
        finally:
            srv.DOCX_DIR = orig_docx
            srv.ANALYSIS_SCRIPTS_DIR = orig_scripts
            srv.CSV_DIR = orig_csv
            srv.HTML_DIR = orig_html
            srv.BUNDLES_DIR = orig_bundles

        assert result.endswith('.zip')
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
        # session files included; stale files excluded
        assert any(session_ts in n for n in names)
        assert not any(stale_ts in n for n in names)

    def test_no_session_timestamp_includes_all(self, tmp_path):
        """FIX 6: empty session_timestamp keeps backward-compatible all-files behavior."""
        import server as srv
        orig_docx = srv.DOCX_DIR
        orig_scripts = srv.ANALYSIS_SCRIPTS_DIR
        orig_csv = srv.CSV_DIR
        orig_html = srv.HTML_DIR
        orig_bundles = srv.BUNDLES_DIR
        try:
            srv.DOCX_DIR = str(tmp_path / 'docx'); os.makedirs(srv.DOCX_DIR)
            srv.ANALYSIS_SCRIPTS_DIR = str(tmp_path / 'scripts'); os.makedirs(srv.ANALYSIS_SCRIPTS_DIR)
            srv.CSV_DIR = str(tmp_path / 'csv'); os.makedirs(srv.CSV_DIR)
            srv.HTML_DIR = str(tmp_path / 'html'); os.makedirs(srv.HTML_DIR)
            srv.BUNDLES_DIR = str(tmp_path / 'bundles'); os.makedirs(srv.BUNDLES_DIR)

            ts_a = "20240101_120000"
            ts_b = "20230101_090000"
            for ext, d in [('.R', srv.ANALYSIS_SCRIPTS_DIR), ('.csv', srv.CSV_DIR)]:
                open(os.path.join(d, f"analysis_{ts_a}{ext}"), 'w').close()
                open(os.path.join(d, f"analysis_{ts_b}{ext}"), 'w').close()

            result = srv.create_reproducibility_bundle()  # no session_timestamp
        finally:
            srv.DOCX_DIR = orig_docx
            srv.ANALYSIS_SCRIPTS_DIR = orig_scripts
            srv.CSV_DIR = orig_csv
            srv.HTML_DIR = orig_html
            srv.BUNDLES_DIR = orig_bundles

        assert result.endswith('.zip')
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
        assert any(ts_a in n for n in names)
        assert any(ts_b in n for n in names)
