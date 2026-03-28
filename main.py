import sys
import asyncio

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from chzzk_tts.app import create_app


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    window = create_app()
    window.show()

    with loop:
        loop.run_until_complete(app_close_event.wait())


if __name__ == "__main__":
    main()
