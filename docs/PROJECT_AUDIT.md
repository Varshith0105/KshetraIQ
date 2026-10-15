# KshetraIQ project audit

Audit date: 2026-10-14. The repository was not a Git worktree when audited. No existing web application, backend package, dependency lockfile, database migration, or deployment configuration was present.

## Inventory

| Area | Verified contents | Assessment |
| --- | --- | --- |
| `AgriVerse-AI` | `agriverse_ai.ipynb`, README | Colab prototype for LangGraph-style routing, Groq, Chroma/RAG, Open-Meteo calls, and a synthetic yield demonstration. It is not deployable application code. |
| `Agriverse_Models` | 8 notebooks, 16 `.pkl` artifacts | Classical-model training/integration experiments: crop recommendation/yield, weather risk, market price, climate scenario, sustainability, RL irrigation references, and a combined pickle. No raw datasets are included. |
| `capstone-final` | 5 notebooks, `plant_disease.h5`, 5 PNGs | Plant disease ResNet50/BLIP/LIME and a Google Earth Engine NDVI experiment. The label map is not stored beside the H5 file. |

Original assets were not edited, renamed, moved, deserialized, retrained, or executed.

## Verified notebook findings

* Crop recommendation declares `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`.
* Yield integration declares `Crop`, `Season`, `State`, `Crop_Year`, `Area`, `Annual_Rainfall`, `Fertilizer`, `Pesticide`; a feature-name file for this model is referenced by a notebook but is absent from this repository.
* Weather-risk integration declares 27 fields, including month/season/state, observed temperatures, pressure, wind, location/elevation and rolling weather values. The integrated notebook supplies invented values (for example fixed elevation, latitude, longitude and derived history); that behaviour is not carried into KshetraIQ.
* Market, climate, and sustainability artifacts have companion feature/info/config pickles, but their complete input/output contracts were not established in this audit. RL irrigation references `final_rl_irrigation_ppo_model.zip`, which is absent.
* `plant_disease.h5` is associated with a 160×160 RGB ResNet50 architecture and 23 output neurons. The class ordering and preprocessing/export compatibility are not preserved in a safe deployable manifest.
* Satellite code uses Google Earth Engine and Sentinel-2; it requires a configured, authorized Earth Engine project and is not a local model.

## Credential and safety findings

* Hard-coded Kaggle credential assignments occur in both `main_file_capstone` notebook variants and both `florence_implementation` variants. Values are intentionally not reproduced here. They must be revoked/rotated; the notebooks remain untouched to preserve original research assets.
* The AgriVerse notebook retrieves a Groq key from Colab user data. It does not provide a local secret-management pattern.
* Notebooks contain installation, download, Colab/Drive, and external-service commands. They were not run.
* Pickle/joblib artifacts are executable-deserialization formats. Their existence is verified; no artifact was loaded until provenance, dependency versions, and sandboxing are established.

## Missing information / blockers

Training datasets, data dictionaries, evaluation summaries, category vocabularies, model/library versions, yield unit, artifact checksums, and deployable disease class map are missing. Consequently, no prediction or model metric is claimed by the scaffold.
