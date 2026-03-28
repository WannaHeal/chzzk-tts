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

### Test Framework
- **pytest**: Primary test framework
- **pytest-asyncio**: For testing async code
- **pytest-qt**: For Qt UI testing
- **unittest.mock**: For mocking

### Test Structure
```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_db.py               # Database operation tests
├── test_config.py           # Configuration tests
├── test_filters.py          # Message filtering tests
├── audio/
│   └── test_player.py       # Audio player tests
├── chat/
│   └── test_client.py       # Chat client tests
├── tts/
│   ├── test_engine.py       # TTS engine tests
│   ├── test_edge_tts.py     # Edge TTS provider tests
│   └── test_google_tts.py   # Google TTS provider tests
└── ui/
    └── test_main_window.py  # UI component tests
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/chzzk_tts --cov-report=html

# Run specific test file
pytest tests/test_filters.py

# Run with verbose output
pytest -v

# Run Qt tests (requires display)
pytest tests/ui/
```

### Test Categories

#### Unit Tests
- Test individual functions and classes in isolation
- Mock all external dependencies (API calls, database, audio)
- Fast execution, no side effects

#### Integration Tests
- Test component interactions
- Use test database (in-memory SQLite)
- Mock external services only (Chzzk API, TTS providers)

#### UI Tests
- Use `pytest-qt` with QtBot
- Test signal/slot connections
- Verify UI state changes
- Mock all business logic

### Mocking Strategies

#### External Services
```python
# Mock Chzzk API
@pytest.fixture
def mock_chzzk_client():
    with patch('chzzk_tts.chat.client.ChzzkClient') as mock:
        yield mock

# Mock TTS provider
@pytest.fixture
def mock_tts_provider():
    provider = Mock(spec=TTSProvider)
    provider.synthesize = AsyncMock(return_value=b'fake_audio_data')
    return provider

# Mock database
@pytest.fixture
def test_db():
    db = Database(':memory:')  # In-memory SQLite
    db.init_tables()
    yield db
    db.close()
```

#### Async Testing
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected

# For Qt async, use qasync test pattern
@pytest.mark.asyncio
async def test_qt_async(qtbot):
    widget = SomeWidget()
    qtbot.addWidget(widget)
    
    # Trigger async operation
    widget.button.click()
    
    # Wait for signal
    qtbot.waitSignal(widget.operation_complete, timeout=1000)
```

### Qt Testing Best Practices

#### Testing Signals
```python
def test_button_emits_signal(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    with qtbot.waitSignal(widget.button_clicked) as blocker:
        qtbot.mouseClick(widget.button, Qt.LeftButton)
    
    assert blocker.signal_triggered
```

#### Testing Async Slots
```python
@pytest.mark.asyncio
async def test_async_slot(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    # Call async slot
    await widget.async_operation()
    
    # Verify state change
    assert widget.label.text() == 'Completed'
```

### Test Configuration

#### conftest.py
```python
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope='session')
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def event_loop(qapp):
    """Provide event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### Code Coverage Goals
- Core logic (filters, config, db): >90%
- TTS providers: >80%
- UI components: >60%
- Overall: >75%

### Continuous Integration
When setting up CI:
- Run on Python 3.12+
- Test on Windows, macOS, Linux
- Install PySide6 dependencies (may need `apt-get install libgl1` on Linux)
- Use `pytest-xvfb` for headless Qt tests on Linux
- Upload coverage reports to codecov

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
