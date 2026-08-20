# Monitor bot Edge

On-prem kindergarten safety vision for [Monitor bot](https://github.com/ysluo-nexial/monitor-bot-edge).
Uses [Ultralytics YOLO-World](https://docs.ultralytics.com/models/yolo-world/) for open-vocabulary detection.

**License:** [AGPL-3.0-or-later](LICENSE)

This repository is the public corresponding source for the on-prem compute. The cloud admin, SI portal, and Monitor bot mobile app are separate closed products and are not in this repo.

## Commercial use

You may run and modify this code under AGPL-3.0. **A product key from the license server is required to start recognition.**

1. A contracted system integrator receives an API key from the vendor.
2. The SI applies for a product key (one key → one venue, one machine).
3. On the venue machine:

```bash
export LICENSE_SERVER_URL=https://your-license-server.example
export PRODUCT_KEY=your-product-key
python scripts/activate.py
```

Without a valid local license, the detector will not start. Video and detections stay on site.

## This release (YOLO only)

- Runtime: YOLO-World (`yolov8s-world.pt` or the weight you configure)
- Qwen-VL is optional and **not** required for launch
- Weights are **not** stored in git. Ultralytics can download them at install time.

## CI / CD

**Do not add GitHub Actions to this repository.**  
Public GitHub is source only. Build, test, and deploy run on the vendor GitLab (`git.nexial.com.tw`). There is no `.github/workflows` here and none should be added.

## What is not in this repo

- Kindergarten / toddler videos or CCTV
- Model weight files (`.pt`, `.gguf`)
- Cloud billing, accounts, or key issuance
- Partner or government reports
- Test Station integration

## Status

Skeleton for the public edge. Detection code and activate-against-license-server land next.
