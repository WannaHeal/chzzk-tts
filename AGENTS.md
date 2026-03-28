# AGENTS.md

## Project Overview

Chzzk-TTS is a desktop application that reads Chzzk (Naver's streaming platform) chat messages aloud using Text-to-Speech (TTS) services.

### Key Features
- Real-time Chzzk chat integration
- Multiple TTS providers (Edge TTS, Google Cloud TTS)
- Per-user voice customization
- Message filtering (banned words/users, length limits)
- Queue-based audio playback with interrupt/sequential modes
- SQLite database for settings persistence

## Tech Stack

- **Python**: 3.12+
- **GUI**: PySide6 (Qt6 bindings)
- **Async**: asyncio + qasync (Qt event loop integration)
- **Chat API**: chzzkpy (Chzzk API client)
- **TTS Providers**: 
  - edge-tts (Microsoft Edge TTS)
  - google-cloud-texttospeech
- **Audio**: sounddevice + numpy + pydub
- **Package Manager**: uv
- **Build**: setuptools

## Project Structure

```
chzzk-tts/
├── src/chzzk_tts/           # Main source code
│   ├── __init__.py
│   ├── app.py               # Application composition and wiring
│   ├── config.py            # Configuration management
│   ├── db.py                # SQLite database operations
│   ├── audio/               # Audio playback
│   │   ├── player.py        # Audio player with queue management
│   │   └── __init__.py
│   ├── chat/                # Chzzk chat integration
│   │   ├── client.py        # Chat manager and WebSocket client
│   │   ├── filters.py       # Message filtering logic
│   │   └── __init__.py
│   ├── tts/                 # TTS providers and engine
│   │   ├── base.py          # Base classes and voice settings
│   │   ├── engine.py        # TTS engine with queue management
│   │   ├── edge_tts_provider.py
│   │   ├── google_tts.py
│   │   └── __init__.py
│   └── ui/                  # GUI components
│       ├── main_window.py   # Main application window
│       ├── connection_panel.py
│       ├── tts_panel.py
│       ├── user_panel.py
│       ├── filter_panel.py
│       ├── oauth_dialog.py
│       └── __init__.py
├── main.py                  # Application entry point
├── pyproject.toml           # Project configuration
├── uv.lock                  # Locked dependencies
├── config.json              # User configuration (gitignored)
└── chzzk_tts.db             # SQLite database (gitignored)
```

## Development Setup

### Prerequisites
- Python 3.12 or higher
- uv package manager

### Installation

```bash
# Install dependencies
uv sync

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/Mac
```

### Running the Application

```bash
# Run directly
python main.py

# Or using uv
uv run python main.py
```

## Code Conventions

### Style
- Follow PEP 8
- Use type hints throughout
- Use `from __future__ import annotations` for forward references

### Async Patterns
- Use `qasync` for Qt-async integration
- Use `@asyncSlot` decorator for async Qt slots
- For slots without arguments, use `lambda: asyncio.ensure_future(coro())` pattern

### Component Design
- **Separation of concerns**: UI panels are separate from business logic
- **Signal-based communication**: Use Qt signals for decoupled communication
- **Provider pattern**: TTS providers implement a common interface
- **Database abstraction**: All DB operations go through `Database` class

### Naming Conventions
- Classes: PascalCase
- Functions/variables: snake_case
- Constants: UPPER_SNAKE_CASE
- Private methods: _leading_underscore

## Configuration

### Files
- `config.json`: User settings (API credentials, TTS preferences)
- `chzzk_tts.db`: SQLite database (user voice settings, banned lists)

### Environment Variables
None currently used. All configuration is via `config.json`.

## Common Commands

```bash
# Run the application
uv run python main.py

# Sync dependencies
uv sync

# Build package
uv build
```

## Testing

Currently no test suite exists. When adding tests:
- Use pytest
- Mock external services (Chzzk API, TTS providers)
- Test UI components with QtTest

## Important Notes

### qasync Bug Workaround
When connecting async slots without arguments to signals, use:
```python
async def _do_something():
    await some_async_operation()

signal.connect(lambda: asyncio.ensure_future(_do_something()))
```

Instead of `@asyncSlot()` decorator (which has a bug with zero-argument signals).

### Credentials
- Google Cloud TTS requires a credentials JSON file
- Chzzk OAuth requires Client ID and Secret from Naver Developer Center
- Never commit credential files to git

### Audio Playback Modes
- **SEQUENTIAL**: Play messages one after another
- **INTERRUPT**: New messages interrupt current playback

## Adding Features

### New TTS Provider
1. Create provider class inheriting from `TTSProvider` in `src/chzzk_tts/tts/`
2. Implement required methods: `name`, `synthesize`, `get_available_voices`
3. Register in `app.py` in `create_app()` function

### New UI Panel
1. Create panel class in `src/chzzk_tts/ui/`
2. Add to `MainWindow` layout
3. Wire signals in `app.py`

## Debugging

Enable debug logging by modifying the logging level in `app.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## License

See LICENSE file for details.
