# KRISHNA Mobile APK Release

The canonical installable Android artifact produced by GitHub Actions is:

`KRISHNA-Mobile.apk`

Package ID: `com.krishna.mobile`

## Build and verification gate

The APK is uploaded only after the workflow completes all of these checks:

- Android Gradle build succeeds.
- Canonical KRISHNA Mobile source contract passes.
- Avatar/Hawkeye/chat/mic UI contract passes.
- Mrityunjaya mobile auto-healer contract passes.
- KABACH APK privacy release gate passes.
- No unexpected tracker signatures are found.
- No non-loopback clear-text host strings are found.
- Android emulator clean install, launch, UI-ready probe and restart pass.
- The produced `KRISHNA-Mobile.apk` is the exact file audited and emulator-tested.

The GitHub artifact also contains:

- `KRISHNA-Mobile.apk.sha256`
- `KRISHNA-Mobile-build.json`

This is a debug-signed private test APK so it is installable without a private production signing key. It must not be represented as a Play Store production-signed release.

## Recommended Windows location

Keep the downloaded mobile package outside the KRISHNA source checkout:

`E:\KRISHNA-Mobile\KRISHNA-Mobile.apk`

Example after downloading the GitHub Actions artifact:

```powershell
New-Item -ItemType Directory -Force "E:\KRISHNA-Mobile" | Out-Null
Copy-Item ".\KRISHNA-Mobile.apk" "E:\KRISHNA-Mobile\KRISHNA-Mobile.apk" -Force
Get-FileHash "E:\KRISHNA-Mobile\KRISHNA-Mobile.apk" -Algorithm SHA256
adb install -r "E:\KRISHNA-Mobile\KRISHNA-Mobile.apk"
```

Compare the SHA-256 output with `KRISHNA-Mobile.apk.sha256` before installation.
