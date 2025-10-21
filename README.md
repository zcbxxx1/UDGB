
### GENERAL INFORMATION:

- Unity Dependencies Generator Bot used for Generating the ZIP Archives in:  
[Unity-Runtime-Libraries](https://github.com/LavaGang/Unity-Runtime-Libraries)  
[Unity-Libraries](https://github.com/LavaGang/Unity-Libraries)

- USAGE: "udgb.exe <Unity_Version>"

---

### PYTHON HELPER SCRIPT

If you only need the processed Windows Mono support archive for a specific
Unity version (for example `6000.0.58f2`), a standalone Python helper is
available at `scripts/download_unity_windows_mono.py`. It replicates UDGB's
behaviour: downloading the macOS installer that bundles the Windows Mono
support files, extracting the managed assemblies, and packaging them into a
flattened ZIP archive.

```bash
python scripts/download_unity_windows_mono.py 6000.0.58f2 -o 6000.0.58.zip
```

The script requires Python 3.8+ and a working `7z` executable (from 7-Zip or
p7zip). Use the `--seven-zip` option or the `SEVEN_ZIP` environment variable if
`7z` is not on your `PATH`.

---

### LICENSING & CREDITS:

UDGB is licensed under the Apache License, Version 2.0. See [LICENSE](https://github.com/LavaGang/UDGB/blob/master/LICENSE.md) for the full License.

Third-party tool used bundled in binary form:
- [7-Zip](https://www.7-zip.org/) is licensed under the GNU LGPL License. See [LICENSE](https://www.7-zip.org/license.txt) for the full License.

External Archive downloaded and extracted from at runtime:
- [Unity](https://unity3d.com/) is a trademark or a registered trademark of Unity Technologies or its affiliates in the U.S. and elsewhere.

UDGB is not sponsored by, affiliated with or endorsed by Unity Technologies or its affiliates.  
"Unity" is a trademark or a registered trademark of Unity Technologies or its affiliates in the U.S. and elsewhere.
