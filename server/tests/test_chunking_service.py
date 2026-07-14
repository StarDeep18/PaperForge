import logging
import pytest
from app.domain.services.chunking_service import ChunkingService, ChunkingConfig
from app.domain.exceptions import (
    EmptyDocumentError,
    MalformedParserOutputError,
    UnsupportedEncodingError,
)

def test_normal_document():
    # Configure small sizes to trigger chunking easily on small text
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    text = "Paragraph one is here.\n\nParagraph two has a lot of details and is much longer."
    result = service.chunk_document("doc-1", text)
    
    assert result.success
    assert result.duration_ms >= 0
    chunks = result.payload
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.document_id == "doc-1"
        assert chunk.content != ""
        assert chunk.parent_content != ""
        assert chunk.parent_chunk_id is not None
        assert chunk.total_chunks == len(chunks)

def test_very_small_document():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    # Valid but small documents should NOT raise an error; they should return a single chunk
    result = service.chunk_document("doc-small", "Short")
    assert result.success
    assert len(result.payload) == 1
    assert result.payload[0].content == "Short"

def test_empty_document():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    # Empty string should raise EmptyDocumentError
    with pytest.raises(EmptyDocumentError):
        service.chunk_document("doc-empty", "")
        
    with pytest.raises(EmptyDocumentError):
        service.chunk_document("doc-spaces", "    \n   ")

def test_long_document():
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    # Large document text
    text = " ".join([f"This is sentence number {i}." for i in range(100)])
    result = service.chunk_document("doc-long", text)
    
    assert result.success
    chunks = result.payload
    assert len(chunks) >= 5
    # Verify index ordering
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx
        assert chunk.total_chunks == len(chunks)

def test_overlap_correctness():
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
    result = service.chunk_document("doc-overlap", text)
    
    assert result.success
    chunks = result.payload
    # Verify overlaps exist and are contiguous slices of original text
    for i in range(1, len(chunks)):
        curr_chunk = chunks[i]
        prev_chunk = chunks[i - 1]
        
        # Verify characters are contiguous
        assert curr_chunk.character_start < prev_chunk.character_end
        assert curr_chunk.content == text[curr_chunk.character_start:curr_chunk.character_end]

def test_metadata_generation():
    config = ChunkingConfig(
        child_chunk_size=15,
        child_chunk_overlap=3,
        parent_chunk_size=30,
        parent_chunk_overlap=6
    )
    service = ChunkingService(config)
    
    text = "Abstract\n1. Introduction to RAG pipeline. This explains how chunks are indexed.\n2. Methods section goes next."
    page_breaks = {
        0: 1,
        45: 2
    }
    
    result = service.chunk_document("doc-meta", text, page_breaks=page_breaks)
    
    assert result.success
    chunks = result.payload
    assert len(chunks) > 0
    # Check that metadata fields are populated correctly on entities and retrieval mapping
    for chunk in chunks:
        assert chunk.document_id == "doc-meta"
        assert chunk.created_at is not None
        assert chunk.character_start >= 0
        assert chunk.character_end > chunk.character_start
        assert chunk.character_end <= len(text)
        
        # Check retrieval metadata dictionary content
        meta = chunk.retrieval_metadata
        assert meta["document_id"] == "doc-meta"
        assert meta["chunk_index"] == chunk.chunk_index
        assert meta["total_chunks"] == len(chunks)
        assert meta["character_start"] == chunk.character_start
        assert meta["character_end"] == chunk.character_end
        assert meta["page_relative_start"] == chunk.page_relative_start
        assert meta["page_relative_end"] == chunk.page_relative_end
        assert "created_at" in meta
        
        if chunk.page_number is not None:
            assert meta["page_number"] == chunk.page_number
            if chunk.character_start >= 45:
                assert chunk.page_number == 2
                assert chunk.page_relative_start == chunk.character_start - 45
            else:
                assert chunk.page_number == 1
                assert chunk.page_relative_start == chunk.character_start

def test_malformed_parser_output():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    text = "Valid text of a reasonable length for chunking."
    
    # Offset out of bounds
    with pytest.raises(MalformedParserOutputError):
        service.chunk_document("doc-err", text, page_breaks={100: 1})
        
    # Invalid page number (<= 0)
    with pytest.raises(MalformedParserOutputError):
        service.chunk_document("doc-err", text, page_breaks={10: 0})

def test_unsupported_encoding():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    # String containing raw invalid surrogates that fail to encode to utf-8
    bad_text = "Hello \ud800 World"
    with pytest.raises(UnsupportedEncodingError):
        service.chunk_document("doc-err", bad_text)

def test_single_page_document():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    text = "This is a single page document content."
    result = service.chunk_document("doc-single", text, page_breaks={0: 1})
    
    assert result.success
    chunks = result.payload
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].page_relative_start == 0
    assert chunks[0].page_relative_end == len(text)

def test_multi_page_document():
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    text = "Page one context here.\nPage two content follows next.\nPage three content is at the tail."
    page_breaks = {
        0: 1,
        23: 2,
        54: 3
    }
    
    result = service.chunk_document("doc-multi-page", text, page_breaks=page_breaks)
    
    assert result.success
    chunks = result.payload
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.page_number in [1, 2, 3]
        assert chunk.page_relative_start >= 0
        assert chunk.page_relative_end > chunk.page_relative_start

def test_document_containing_only_headings():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    text = "Abstract\nIntroduction\nMethodology\nConclusion"
    result = service.chunk_document("doc-headings", text)
    
    assert result.success
    chunks = result.payload
    assert len(chunks) == 1
    assert "Abstract" in chunks[0].content
    assert "Conclusion" in chunks[0].content

def test_document_with_extremely_long_paragraphs():
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    # 100 character paragraphs with no boundary splits
    text = "a" * 100
    result = service.chunk_document("doc-long-p", text)
    
    assert result.success
    chunks = result.payload
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.content) > 0

def test_deterministic_chunk_id_verification():
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    text = "This is a test of deterministic chunking identifiers."
    
    result1 = service.chunk_document("doc-det", text)
    result2 = service.chunk_document("doc-det", text)
    
    assert len(result1.payload) == len(result2.payload)
    for c1, c2 in zip(result1.payload, result2.payload):
        assert c1.id == c2.id
        assert c1.parent_chunk_id == c2.parent_chunk_id

def test_chunk_statistics_validation():
    config = ChunkingConfig(
        child_chunk_size=10,
        child_chunk_overlap=2,
        parent_chunk_size=20,
        parent_chunk_overlap=4
    )
    service = ChunkingService(config)
    
    text = "This is a document content for statistics testing."
    result = service.chunk_document("doc-stats", text)
    
    assert result.success
    assert result.duration_ms >= 0
    
    stats = result.statistics
    assert stats["total_chunks"] == len(result.payload)
    assert stats["total_characters"] == len(text)
    assert stats["average_chunk_size"] > 0
    assert stats["overlap_size"] == 2 * 4
    assert stats["processing_duration_ms"] == result.duration_ms

def test_logging_behavior(caplog):
    config = ChunkingConfig()
    service = ChunkingService(config)
    
    with caplog.at_level(logging.INFO, logger="paperforge"):
        service.chunk_document("doc-log", "This is a logging behavior test document.")
        
    assert any("Chunking completed" in record.message for record in caplog.records)
