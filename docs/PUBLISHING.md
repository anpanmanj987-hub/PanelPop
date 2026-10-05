# Publishing this independent alpha

The deliverable is the `panelpop/` tree as a standalone MIT source repository. No remote GitHub repository, package upload, public host or signed executable is created by this implementation. Choose and verify a remote/package name before publishing; the local project name does not reserve a registry name.

## Prepare a release

1. Copy this tree into its own repository root. Preserve `src/`, `tests/`, `docs/`, `.github/`, both READMEs and LICENSE. It has no dependency on sibling projects.
2. Use Python 3.10 or newer and a clean virtual environment. Install the project and build frontend:

   ```sh
   python -m pip install -e . build
   python -m unittest discover -s tests -v
   python -m panelpop --help
   python -m build
   ```

3. Install the generated wheel into a separate directory/virtualenv, and run the demo from outside the checkout:

   ```sh
   python -m pip install /absolute/path/to/dist/panelpop-0.1.0a2-py3-none-any.whl
   python -m panelpop --demo
   ```

   Open the printed admin/viewer URLs. Verify preview, QR, settings, phone-style panel tap and Stop. Confirm HTML/CSS/JS are included. Repeat installation with the sdist in another clean environment.
4. Review [VALIDATION.md](VALIDATION.md) and include the unfinished Windows/phone items in release notes. Obtain actual hardware evidence before promoting this beyond an alpha.
5. Review CI output after pushing the independent repository. Its working directory is the repository root, not a parent workspace. Check no `.venv`, tokens, request logs, private desktop screenshots or generated secrets are committed.
6. Tag `v0.1.0a2` and attach the wheel/sdist and concise alpha release notes to the chosen GitHub release when authorized. Registry publishing is a separate deliberate step; do not assume the name is available.

## Release note essentials

- Windows 10/11 target; Python 3.10+; phone browser client.
- Explicit synthetic demo on other OSes; live native desktop operation unverified until hardware checks are recorded.
- View-only default, PC-only settings/Stop/rearm, two-second frame validity.
- LAN HTTP is unencrypted and intended for trusted private networks only.
- Conservative occlusion checks, non-atomic Win32 input race and UIPI limits.
- No signed executable, automatic updater, reverse proxy or public-host deployment.

Do not publish the example runtime URLs printed during a demo: their fragments are live credentials for that host. Restarting revokes them.
