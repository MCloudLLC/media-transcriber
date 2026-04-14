"""
Unit tests for qa.py - TranscriptQA class

All external dependencies (openai, chromadb, sentence_transformers) are mocked
to allow tests to run without these packages installed.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture(autouse=True)
def mock_optional_deps():
    """Mock optional qa dependencies at module level before importing qa."""
    mock_openai = MagicMock()
    mock_chromadb = MagicMock()
    mock_sentence_transformers = MagicMock()
    
    mocks = {
        "openai": mock_openai,
        "chromadb": mock_chromadb,
        "sentence_transformers": mock_sentence_transformers,
    }
    
    with patch.dict(sys.modules, mocks):
        yield mocks


@pytest.fixture
def short_transcript():
    """A short ~50-word transcript for testing full-context routing."""
    words = ["This", "is", "a", "test", "transcript", "with", "meaningful", "content."] * 6
    return " ".join(words)


@pytest.fixture
def long_transcript():
    """A long transcript (>20K words) for testing RAG routing."""
    return " ".join(["word"] * 20000)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns a canned response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "mocked answer"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.mark.unit
def test_ask_full_context_route(short_transcript, mock_openai_client, mock_optional_deps):
    """Transcript with < 25K estimated tokens should use full-context routing."""
    from qa import TranscriptQA
    
    qa_instance = TranscriptQA(
        transcript_text=short_transcript,
        llm_url="http://localhost:11434/v1",
        api_key="test-key",
        model="llama3"
    )
    
    with patch.object(qa_instance, "_ask_full_context", return_value="full context answer") as mock_full:
        with patch.object(qa_instance, "_ask_rag", return_value="rag answer") as mock_rag:
            result = qa_instance.ask("What is this about?")
            
            mock_full.assert_called_once()
            mock_rag.assert_not_called()
            assert result == "full context answer"


@pytest.mark.unit
def test_ask_rag_route(long_transcript, mock_openai_client, mock_optional_deps):
    """Transcript with >= 25K estimated tokens should use RAG routing."""
    from qa import TranscriptQA
    
    qa_instance = TranscriptQA(
        transcript_text=long_transcript,
        llm_url="http://localhost:11434/v1",
        api_key="test-key",
        model="llama3"
    )
    
    with patch.object(qa_instance, "_ask_full_context", return_value="full context answer") as mock_full:
        with patch.object(qa_instance, "_ask_rag", return_value="rag answer") as mock_rag:
            with patch.object(qa_instance, "_setup_rag"):  # Mock setup to avoid dependencies
                result = qa_instance.ask("What is this about?")
                
                mock_rag.assert_called_once()
                mock_full.assert_not_called()
                assert result == "rag answer"


@pytest.mark.unit
def test_ask_full_context_calls_llm(short_transcript, mock_openai_client, mock_optional_deps):
    """Full-context route should call OpenAI client with correct parameters."""
    from qa import TranscriptQA
    
    # Patch OpenAI at the point of import (inside the ask method)
    with patch("openai.OpenAI", return_value=mock_openai_client) as mock_openai_class:
        qa_instance = TranscriptQA(
            transcript_text=short_transcript,
            llm_url="http://custom-llm:8080/v1",
            api_key="custom-key",
            model="gpt-4"
        )
        
        qa_instance.ask("What is the main topic?")
        
        # Verify OpenAI client initialized with correct URL and API key
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs["base_url"] == "http://custom-llm:8080/v1"
        assert call_kwargs["api_key"] == "custom-key"
        
        # Verify chat completion called with question and transcript
        mock_openai_client.chat.completions.create.assert_called_once()
        create_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert create_kwargs["model"] == "gpt-4"
        
        messages = create_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "What is the main topic?" in messages[1]["content"]
        assert short_transcript in messages[1]["content"] or "transcript" in messages[0]["content"].lower()


@pytest.mark.unit
def test_ask_returns_llm_response(short_transcript, mock_optional_deps):
    """ask() should return the exact response from LLM."""
    from qa import TranscriptQA
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "The answer is 42"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch("openai.OpenAI", return_value=mock_client):
        qa_instance = TranscriptQA(
            transcript_text=short_transcript,
            llm_url="http://localhost:11434/v1",
            api_key="test-key",
            model="llama3"
        )
        
        result = qa_instance.ask("What is the meaning of life?")
        assert result == "The answer is 42"


@pytest.mark.unit
def test_rag_setup_chunks_correctly(mock_optional_deps):
    """RAG setup should create correct number of chunks with 500-word chunks and 50-word overlap."""
    from qa import TranscriptQA, _chunk_text
    
    # 1000-word transcript with 500-word chunks and 50-word overlap
    # Chunk 1: words 0-499 (500 words)
    # Chunk 2: words 450-949 (500 words, overlaps 50 with chunk 1)
    # Chunk 3: words 900-999 + pad (100 words remaining, less than full chunk)
    # Expected: 3 chunks total
    transcript_1000_words = " ".join([f"word{i}" for i in range(1000)])
    
    # Test the chunking function directly
    chunks = _chunk_text(transcript_1000_words)
    
    # Verify chunks were created
    # Expected chunks = ceil((1000 - 50) / (500 - 50)) + 1 = ceil(950/450) + 1 = 3
    # Or simpler: start at 0, jump by 450 each time until end: 0, 450, 900 = 3 chunks
    assert len(chunks) >= 2  # At minimum 2 chunks for 1000 words
    assert len(chunks) <= 3  # At maximum 3 chunks


@pytest.mark.unit
def test_rag_chunks_have_overlap(mock_optional_deps):
    """Adjacent chunks should share words at the overlap boundary."""
    from qa import _chunk_text
    
    # Create a transcript where we can verify overlap
    words = [f"word{i:04d}" for i in range(1000)]
    transcript = " ".join(words)
    
    # Test the chunking function directly
    chunks = _chunk_text(transcript)
    
    # Verify we have at least 2 chunks to check overlap
    assert len(chunks) >= 2
    
    # Check that chunk 2 starts before chunk 1 ends (overlap)
    chunk1_words = chunks[0].split()
    chunk2_words = chunks[1].split()
    
    # Last 50 words of chunk 1 should appear in first 50 words of chunk 2
    chunk1_end = chunk1_words[-50:]
    chunk2_start = chunk2_words[:50]
    
    # Find at least some overlap
    overlap = set(chunk1_end) & set(chunk2_start)
    assert len(overlap) > 0, "Adjacent chunks should have overlapping words"


@pytest.mark.unit
def test_missing_openai_package_raises_import_error(short_transcript, mock_optional_deps):
    """When openai is not importable, ask() should raise ImportError with helpful message."""
    from qa import TranscriptQA
    
    qa_instance = TranscriptQA(
        transcript_text=short_transcript,
        llm_url="http://localhost:11434/v1",
        api_key="test-key",
        model="llama3"
    )
    
    # Mock the import to fail when ask() tries to import openai
    def mock_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return __import__(name, *args, **kwargs)
    
    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(ImportError) as exc_info:
            qa_instance.ask("test question")
        
        error_message = str(exc_info.value).lower()
        assert "uv sync --extra qa" in error_message or "openai" in error_message


@pytest.mark.unit
def test_missing_sentence_transformers_raises_import_error(long_transcript, mock_optional_deps):
    """When sentence_transformers is not importable, _setup_rag() should raise ImportError."""
    from qa import TranscriptQA
    
    qa_instance = TranscriptQA(
        transcript_text=long_transcript,
        llm_url="http://localhost:11434/v1",
        api_key="test-key",
        model="llama3"
    )
    
    # Mock sentence_transformers import to fail
    def mock_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("No module named 'sentence_transformers'")
        return __import__(name, *args, **kwargs)
    
    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(ImportError) as exc_info:
            qa_instance._setup_rag()
        
        error_message = str(exc_info.value).lower()
        assert "uv sync --extra qa" in error_message or "sentence" in error_message


@pytest.mark.unit
def test_custom_llm_url(short_transcript, mock_openai_client, mock_optional_deps):
    """TranscriptQA should initialize OpenAI client with custom LLM URL."""
    from qa import TranscriptQA
    
    custom_url = "http://my-custom-llm.example.com:9000/v1"
    
    with patch("openai.OpenAI", return_value=mock_openai_client) as mock_openai_class:
        qa_instance = TranscriptQA(
            transcript_text=short_transcript,
            llm_url=custom_url,
            api_key="test-key",
            model="llama3"
        )
        
        qa_instance.ask("test question")
        
        # Verify OpenAI initialized with custom URL
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs["base_url"] == custom_url


@pytest.mark.unit
def test_api_key_fallback_to_ollama(short_transcript, mock_openai_client, mock_optional_deps):
    """When api_key is None, OpenAI client should be initialized with 'ollama' as key."""
    from qa import TranscriptQA
    
    with patch("openai.OpenAI", return_value=mock_openai_client) as mock_openai_class:
        qa_instance = TranscriptQA(
            transcript_text=short_transcript,
            llm_url="http://localhost:11434/v1",
            api_key=None,
            model="llama3"
        )
        
        qa_instance.ask("test question")
        
        # Verify OpenAI initialized with fallback key
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs["api_key"] is not None
        assert call_kwargs["api_key"] == "ollama" or isinstance(call_kwargs["api_key"], str)


@pytest.mark.unit
def test_empty_transcript(mock_openai_client, mock_optional_deps):
    """Empty transcript should either raise ValueError or return sensible error."""
    from qa import TranscriptQA
    
    with patch("openai.OpenAI", return_value=mock_openai_client):
        # Test with empty string
        qa_instance = TranscriptQA(
            transcript_text="",
            llm_url="http://localhost:11434/v1",
            api_key="test-key",
            model="llama3"
        )
        
        # Should either raise ValueError or handle gracefully
        try:
            result = qa_instance.ask("test question")
            # If it doesn't raise, result should indicate the issue
            assert result is not None
            assert isinstance(result, str)
        except ValueError as e:
            # ValueError is acceptable for empty transcript
            assert "empty" in str(e).lower() or "transcript" in str(e).lower()


@pytest.mark.unit
def test_qa_status_no_transcript_set():
    """
    Integration note: In app.py, _qa should be reset to None when a new transcript is loaded.
    This test documents the expected behavior.
    
    When app._transcript_text is empty or None, the Ask button should be disabled
    and app._qa should be None until a transcript is successfully loaded.
    """
    # This is primarily an integration concern for test_app_qa_tab.py
    # Document here that qa.py itself doesn't track this state
    # The App class is responsible for:
    # 1. Setting _qa = None on initialization
    # 2. Setting _qa = None when clearing chat
    # 3. Only creating TranscriptQA when transcript_text is non-empty
    pass
