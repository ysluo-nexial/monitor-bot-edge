# Monitor bot Edge

On-prem kindergarten safety vision for Monitor bot.
YOLO-World open-vocabulary detection, then IoU tracking and geometry/time rules (fall, climb, alone, crowd). No Qwen / GGUF.

**Brand:** Monitor bot Edge  
**Copyright:** Nexial Technology LTD. / 朔域科技有限公司 2026  
**License:** [AGPL-3.0-or-later](LICENSE)

Public corresponding source for the on-prem compute. Cloud admin, SI portal, and the Monitor bot app are separate closed products.

## Commercial use

AGPL-3.0-or-later. **A product key is required to start recognition.** One key → one venue, one machine.

```bash
export LICENSE_SERVER_URL=https://your-license-server.example
export PRODUCT_KEY=your-product-key
python scripts/activate.py
```

Without `license/license.json` containing `license_token`, detect will not load YOLO. Video stays on site.

## CI / CD

**Do not add GitHub Actions.** This GitHub repo is source only. Build, test, and deploy run on GitLab (`git.nexial.com.tw`).

## Quick start (local mock)

```bash
python -m pip install -e ".[dev]"

# 1) mock license server
python scripts/mock_license_server.py --host 127.0.0.1 --port 8765

# 2) activate this machine
export LICENSE_SERVER_URL=http://127.0.0.1:8765
export PRODUCT_KEY=dev-key
export MACHINE_ID=venue-dev-1
python scripts/activate.py

# 3) detect (downloads yolov8s-world.pt on first run)
python -m monitor_bot_edge detect \
  --video /path/to/on_site.mp4 \
  --keywords "幼兒,跌倒,攀爬" \
  --output-dir outputs
```

Outputs: `<stem>.annotated.mp4` and `<stem>.events.jsonl` (`time`, `label`, `confidence`, `box`).

## Tests (no GPU, no weights)

```bash
PYTHONPATH=. python -m pytest -q
```

## Not in this repo

Kindergarten videos, `.pt` / `.gguf` weights, billing, partner reports, Test Station.
