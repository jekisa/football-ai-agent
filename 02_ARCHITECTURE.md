# Architecture

Modules

1. News Collector
2. Duplicate Filter
3. Trending Analyzer
4. Script Generator
5. SEO Generator
6. Voice Generator
7. Subtitle Generator
8. Thumbnail Prompt Generator
9. Video Builder
10. Quality Checker
11. YouTube Publisher
12. Analytics Reporter

Each module must be independently testable.

Communication between modules should use JSON.

No module should directly depend on another module's internal implementation.

Future integrations:

- n8n
- PostgreSQL
- Ollama
- FFmpeg
- Whisper
- Piper TTS
- YouTube API
