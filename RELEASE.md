# Release v0.1.0

## GitHub web flow

1. Create a new GitHub repository named `bedpad`.
2. Push this local repository:

```powershell
git remote add origin https://github.com/YOUR_NAME/bedpad.git
git push -u origin main
```

3. Create and push the release tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

4. Open GitHub Releases and create a new release from `v0.1.0`.
5. Upload `bedpad-0.1.0.zip` as the release asset.

## Release title

```text
BedPad v0.1.0
```

## Release notes

```markdown
First public release of BedPad.

BedPad turns your phone browser into a tiny touchpad for your Windows PC.

- No mobile app
- No account
- Windows + Python
- Double-click QR launcher
- Tap, long press, double tap, two-finger scroll
- Text panel and quick keys
- Token-protected local URL

Use only on trusted local networks.
```
