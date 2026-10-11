"""Gemini SDK contract and failure regressions; no live AI requests."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google import genai
from google.genai import errors, types

import analyzer


@pytest.fixture(autouse=True)
def gemini_environment(monkeypatch):
    monkeypatch.setenv('SCAMBRAKE_AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.delenv('GEMINI_MODEL', raising=False)


def install_client(monkeypatch, **kwargs):
    client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(**kwargs)), close=Mock())
    monkeypatch.setattr(analyzer, '_gemini_client', lambda: client)
    return client


@pytest.mark.parametrize('model,expected', [('', 'gemini-2.5-flash'), (' custom-model ', 'custom-model')])
def test_sdk_request_and_contract(monkeypatch, model, expected):
    monkeypatch.setenv('GEMINI_MODEL', model)
    payload = analyzer._empty_result('Possible indicators.')
    response = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(parts=[types.Part(text=json.dumps(payload))]))])
    client = install_client(monkeypatch, return_value=response)
    assert analyzer.analyze_input('Please verify $20') == payload
    request = client.models.generate_content.call_args.kwargs
    assert request['model'] == expected
    assert 'Please verify $20' in request['contents']
    config = types.GenerateContentConfig(**request['config'])
    assert config.system_instruction == analyzer.INSTRUCTIONS
    assert config.response_mime_type == 'application/json'
    assert config.thinking_config.thinking_budget == 0
    assert config.max_output_tokens == 1024
    client.close.assert_called_once()


def test_factory_uses_official_sdk_and_bounded_timeout(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(genai, 'Client', factory)
    analyzer._gemini_client()
    args = factory.call_args.kwargs
    assert args['api_key'] == 'test-key'
    assert args['vertexai'] is False
    options = types.HttpOptions(**args['http_options'])
    assert options.timeout == 60000
    assert options.retry_options.attempts == 1


@pytest.mark.parametrize('code,attempts', [(400, 1), (401, 1), (403, 1), (404, 1), (429, 3), (500, 3), (503, 3)])
def test_real_sdk_errors_are_sanitized(monkeypatch, capsys, code, attempts):
    client = install_client(monkeypatch, side_effect=errors.APIError(code, {'message': 'PRIVATE MESSAGE AND KEY'}))
    sleep = Mock()
    monkeypatch.setattr(analyzer.time, 'sleep', sleep)
    result = analyzer.analyze_input('PRIVATE INPUT')
    assert result['risk_level'] == 'uncertain'
    assert len(result) == 7
    assert str(code) in result['explanation']
    assert client.models.generate_content.call_count == attempts
    assert sleep.call_count == attempts - 1
    client.close.assert_called_once()
    assert 'PRIVATE' not in str(result) + capsys.readouterr().err


def test_retry_recovers(monkeypatch):
    payload = analyzer._empty_result('Recovered')
    client = install_client(monkeypatch, side_effect=[errors.APIError(503, {}), SimpleNamespace(text=json.dumps(payload))])
    monkeypatch.setattr(analyzer.time, 'sleep', Mock())
    assert analyzer.analyze_input('hello') == payload
    assert client.models.generate_content.call_count == 2


def test_blocked_response_is_uncertain(monkeypatch):
    response = types.GenerateContentResponse(prompt_feedback=types.GenerateContentResponsePromptFeedback(block_reason='SAFETY'))
    install_client(monkeypatch, return_value=response)
    result = analyzer.analyze_input('hello')
    assert result['risk_level'] == 'uncertain'
    assert 'empty response' in result['explanation']


def test_missing_sdk_is_actionable(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == 'google':
            raise ImportError('PRIVATE')
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', missing)
    result = analyzer.analyze_input('hello')
    assert 'pip install google-genai' in result['explanation']
    assert 'PRIVATE' not in str(result)
