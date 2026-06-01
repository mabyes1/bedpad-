# BedPad

Use your phone browser as a tiny touchpad for your Windows PC.

No mobile app. No account. One Python file. Built for couch and bed control.

## Features

- Single-finger drag moves the PC cursor.
- Short tap sends left click.
- Long press sends right click.
- Double tap opens the phone text panel.
- Two-finger swipe scrolls.
- Quick keys for Backspace, Esc, Space, and Enter.
- Text input sends Unicode text to the currently focused Windows app.
- Random URL token by default.

## Demo Positioning

There are bigger tools in this space, including KDE Connect, Unified Remote, Remote Mouse, and Unrud's Remote Touchpad. BedPad is intentionally smaller: it is a single-file, browser-based Windows remote touchpad that is easy to inspect, modify, and run.

## Requirements

- Windows
- Python 3.10 or newer
- Phone and PC on the same trusted local network

## Quick Start

```powershell
python .\bedpad.py
```

Open the printed URL on your phone.

Example:

```text
BedPad is running.
http://192.168.0.20:8765/?token=...
Keep this window open. Press Ctrl+C to stop.
```

## Gesture Map

| Phone gesture | PC action |
| --- | --- |
| Drag one finger | Move cursor |
| Short tap | Left click |
| Long press | Right click |
| Double tap | Open text panel |
| Two-finger swipe | Scroll |
| Text panel Send | Type text into focused app |

## Options

```powershell
python .\bedpad.py --port 8876
python .\bedpad.py --host 127.0.0.1
python .\bedpad.py --token your-local-token
```

## Security Notes

BedPad injects mouse and keyboard input into your Windows session. Treat the URL like a local remote-control key.

- Use only on trusted LANs.
- Keep the token private.
- Stop the server when you are done.
- Do not expose the port to the internet.

## Roadmap

- QR code in the console or launcher.
- Windows tray app.
- Packaged `.exe` release.
- Sensitivity sliders for pointer and scroll.
- Media keys and presentation mode.
- Optional HTTPS for local networks.

## License

MIT
